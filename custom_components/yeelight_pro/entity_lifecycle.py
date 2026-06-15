"""Helpers for reconciling projected Yeelight Pro entities with HA's registry."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN
from .entity_category import ha_entity_category
from .entity_candidates import (
    EntityCandidate,
    EntityCandidateCoordinator,
    EntityKey,
    collect_entity_candidates,
    collect_entity_candidate_keys,
)
from .entity_lifecycle_cleanup import (
    EntityRegistryCleanupAudit,
    EntityRegistryCleanupPreview,
    async_disable_stale_registry_entities,
    async_preview_stale_registry_cleanup,
    entity_registry_cleanup_diagnostics,
)
from .entity_lifecycle_entity_id import (
    all_registry_entity_ids,
    safe_entity_id_migration,
)

_LOGGER = logging.getLogger(__name__)

_PENDING_STALE_ENTITY_KEYS = "_yeelight_pro_pending_stale_entity_keys"
_LAST_RECONCILE_SUMMARY = "_yeelight_pro_last_entity_registry_reconcile_summary"


EntityLifecycleCoordinator = EntityCandidateCoordinator

__all__ = [
    "EntityLifecycleCoordinator",
    "EntityRegistryCleanupAudit",
    "EntityRegistryCleanupPreview",
    "EntityRegistryReconcileSummary",
    "async_disable_stale_registry_entities",
    "async_preview_stale_registry_cleanup",
    "async_reconcile_entity_registry",
    "collect_active_entity_keys",
    "collect_active_entity_unique_ids",
    "entity_registry_cleanup_diagnostics",
    "entity_registry_reconcile_diagnostics",
]


@dataclass(frozen=True, slots=True)
class EntityRegistryReconcileSummary:
    """Aggregate entity registry reconciliation result for diagnostics."""

    active: int
    registry_entries: int
    stale: int
    pending_stale: int
    disabled: int
    restored: int = 0
    metadata_updated: int = 0

    def as_diagnostics(self) -> dict[str, int]:
        """Return a diagnostics-safe aggregate payload."""
        return {
            "active": self.active,
            "registry_entries": self.registry_entries,
            "stale": self.stale,
            "pending_stale": self.pending_stale,
            "disabled": self.disabled,
            "restored": self.restored,
            "metadata_updated": self.metadata_updated,
        }


def collect_active_entity_keys(
    coordinator: EntityLifecycleCoordinator,
) -> set[EntityKey]:
    """Collect active projected entity keys for the current topology."""
    return collect_entity_candidate_keys(coordinator)


def collect_active_entity_unique_ids(
    coordinator: EntityLifecycleCoordinator,
) -> set[str]:
    """Collect active unique IDs for compatibility with existing tests."""
    return {unique_id for _, unique_id in collect_active_entity_keys(coordinator)}


def entity_registry_reconcile_diagnostics(
    coordinator: Any,
) -> dict[str, int] | None:
    """Return the last aggregate reconcile result without entity identifiers."""
    summary = getattr(coordinator, _LAST_RECONCILE_SUMMARY, None)
    return summary.as_diagnostics() if isinstance(
        summary,
        EntityRegistryReconcileSummary,
    ) else None


def _registry_entry_domain(registry_entry: er.RegistryEntry) -> str | None:
    """Return the HA entity domain for a registry entry."""
    domain = getattr(registry_entry, "domain", None)
    if isinstance(domain, str) and domain:
        return domain
    entity_id = getattr(registry_entry, "entity_id", "")
    if isinstance(entity_id, str) and "." in entity_id:
        return entity_id.split(".", 1)[0]
    return None


def _registry_entry_disabled_by_user(registry_entry: er.RegistryEntry) -> bool:
    """Return whether the registry entry was explicitly disabled by the user."""
    return getattr(registry_entry, "disabled_by", None) in {
        er.RegistryEntryDisabler.USER,
        "user",
    }


def _registry_entry_disabled_by_integration(registry_entry: er.RegistryEntry) -> bool:
    """Return whether the registry entry was automatically disabled by this integration."""
    return getattr(registry_entry, "disabled_by", None) in {
        er.RegistryEntryDisabler.INTEGRATION,
        "integration",
    }


async def async_reconcile_entity_registry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: EntityLifecycleCoordinator,
) -> set[str]:
    """Record stale integration registry entries without mutating user registries."""
    active_entity_candidates = collect_entity_candidates(coordinator)
    active_entity_keys = set(active_entity_candidates)
    registry_entries, stale_entries = _collect_registry_entries(
        hass,
        entry,
        active_entity_keys,
    )
    stale_keys = set(stale_entries)
    pending_stale_keys = _pending_stale_entity_keys(coordinator)
    pending_stale_keys.intersection_update(stale_keys)
    pending_stale_keys.update(stale_keys)
    restored = _restore_active_integration_entries(
        hass,
        registry_entries,
        active_entity_keys,
    )
    metadata_updated = _sync_active_registry_metadata(
        hass,
        registry_entries,
        active_entity_candidates,
    )

    setattr(
        coordinator,
        _LAST_RECONCILE_SUMMARY,
        EntityRegistryReconcileSummary(
            active=len(active_entity_keys),
            registry_entries=len(registry_entries),
            stale=len(stale_keys),
            pending_stale=len(pending_stale_keys),
            disabled=0,
            restored=restored,
            metadata_updated=metadata_updated,
        ),
    )
    _LOGGER.info(
        "Reconciled Yeelight Pro entity registry for entry %s: active=%s "
        "pending_stale=%s stale=%s restored=%s metadata_updated=%s",
        entry.entry_id,
        len(active_entity_keys),
        len(pending_stale_keys),
        len(stale_keys),
        restored,
        metadata_updated,
    )
    _LOGGER.debug(
        "Yeelight Pro entity registry reconcile detail for entry %s: "
        "registry_entries=%s disabled=%s active_domains=%s stale_domains=%s "
        "pending_stale_domains=%s registry_domains=%s",
        entry.entry_id,
        len(registry_entries),
        0,
        _entity_key_domain_counts(active_entity_keys),
        _entity_key_domain_counts(stale_keys),
        _entity_key_domain_counts(pending_stale_keys),
        _registry_entry_domain_counts(registry_entries),
    )
    return {unique_id for _, unique_id in active_entity_keys}


def _collect_registry_entries(
    hass: HomeAssistant,
    entry: ConfigEntry,
    active_entity_keys: set[EntityKey],
) -> tuple[list[er.RegistryEntry], dict[EntityKey, er.RegistryEntry]]:
    """Collect owned registry entries and stale candidates."""
    entity_registry = er.async_get(hass)
    registry_entries: list[er.RegistryEntry] = []
    stale_entries: dict[EntityKey, er.RegistryEntry] = {}
    for registry_entry in er.async_entries_for_config_entry(entity_registry, entry.entry_id):
        registry_domain = _registry_entry_domain(registry_entry)
        if (
            registry_domain is None
            or registry_entry.platform != DOMAIN
            or not registry_entry.unique_id.startswith(f"{DOMAIN}_")
        ):
            continue
        registry_entries.append(registry_entry)
        registry_key = (registry_domain, registry_entry.unique_id)
        if registry_key not in active_entity_keys:
            if getattr(registry_entry, "disabled_by", None) is not None:
                continue
            if _registry_entry_disabled_by_user(registry_entry):
                continue
            stale_entries[registry_key] = registry_entry
    return (registry_entries, stale_entries)


def _pending_stale_entity_keys(coordinator: Any) -> set[EntityKey]:
    """Return coordinator-local stale candidates between reconcile passes."""
    value = getattr(coordinator, _PENDING_STALE_ENTITY_KEYS, None)
    if isinstance(value, set):
        return value
    pending: set[EntityKey] = set()
    setattr(coordinator, _PENDING_STALE_ENTITY_KEYS, pending)
    return pending


def _entity_key_domain_counts(keys: set[EntityKey]) -> dict[str, int]:
    """Return deterministic HA domain counts without entity identifiers."""
    return dict(sorted(Counter(domain for domain, _unique_id in keys).items()))


def _registry_entry_domain_counts(
    registry_entries: list[er.RegistryEntry],
) -> dict[str, int]:
    """Return deterministic registry domain counts without entity identifiers."""
    counts = Counter(
        domain
        for registry_entry in registry_entries
        if (domain := _registry_entry_domain(registry_entry)) is not None
    )
    return dict(sorted(counts.items()))


def _disable_stale_entries(
    hass: HomeAssistant,
    stale_entries: dict[EntityKey, er.RegistryEntry],
) -> int:
    """Mark stale entries disabled by integration while preserving registry data."""
    if not stale_entries:
        return 0
    entity_registry = er.async_get(hass)
    disabled = 0
    for registry_entry in stale_entries.values():
        if getattr(registry_entry, "disabled_by", None) is not None:
            continue
        entity_registry.async_update_entity(
            registry_entry.entity_id,
            disabled_by=er.RegistryEntryDisabler.INTEGRATION,
        )
        disabled += 1
    return disabled


def _restore_active_integration_entries(
    hass: HomeAssistant,
    registry_entries: list[er.RegistryEntry],
    active_entity_keys: set[EntityKey],
) -> int:
    """Re-enable integration-disabled entries whose candidates are active again."""
    if not registry_entries:
        return 0
    entity_registry = er.async_get(hass)
    restored = 0
    for registry_entry in registry_entries:
        registry_domain = _registry_entry_domain(registry_entry)
        if registry_domain is None:
            continue
        registry_key = (registry_domain, registry_entry.unique_id)
        if (
            registry_key not in active_entity_keys
            or not _registry_entry_disabled_by_integration(registry_entry)
        ):
            continue
        entity_registry.async_update_entity(
            registry_entry.entity_id,
            disabled_by=None,
        )
        restored += 1
    return restored


def _sync_active_registry_metadata(
    hass: HomeAssistant,
    registry_entries: list[er.RegistryEntry],
    active_entity_candidates: dict[EntityKey, EntityCandidate],
) -> int:
    """Refresh integration-owned registry metadata for active entities."""
    if not registry_entries:
        return 0
    entity_registry = er.async_get(hass)
    current_entity_ids = all_registry_entity_ids(entity_registry, registry_entries)
    updated = 0
    for registry_entry in registry_entries:
        registry_domain = _registry_entry_domain(registry_entry)
        if registry_domain is None:
            continue
        candidate = active_entity_candidates.get((registry_domain, registry_entry.unique_id))
        if candidate is None:
            continue
        kwargs = _active_metadata_update_kwargs(
            registry_entry,
            candidate,
            current_entity_ids=current_entity_ids,
        )
        if not kwargs:
            continue
        applied_kwargs = _update_active_registry_entry(
            entity_registry,
            registry_entry,
            kwargs,
        )
        if not applied_kwargs:
            continue
        if isinstance(new_entity_id := applied_kwargs.get("new_entity_id"), str):
            current_entity_ids.discard(registry_entry.entity_id)
            current_entity_ids.add(new_entity_id)
        updated += 1
    return updated


def _update_active_registry_entry(
    entity_registry: er.EntityRegistry,
    registry_entry: er.RegistryEntry,
    kwargs: dict[str, Any],
) -> dict[str, Any]:
    """Apply metadata updates, keeping display cleanup if entity_id migration fails."""
    try:
        entity_registry.async_update_entity(registry_entry.entity_id, **kwargs)
        return kwargs
    except ValueError:
        metadata_kwargs = dict(kwargs)
        metadata_kwargs.pop("new_entity_id", None)
        if not metadata_kwargs:
            _LOGGER.debug(
                "Skipped Yeelight Pro entity_id migration for active registry "
                "entry: domain=%s reason=entity_id_conflict",
                _registry_entry_domain(registry_entry),
            )
            return {}
        entity_registry.async_update_entity(registry_entry.entity_id, **metadata_kwargs)
        _LOGGER.debug(
            "Applied partial Yeelight Pro registry metadata update after "
            "entity_id migration failed: domain=%s fields=%s "
            "skipped_field=new_entity_id reason=entity_id_conflict",
            _registry_entry_domain(registry_entry),
            sorted(metadata_kwargs),
        )
        return metadata_kwargs


def _active_metadata_update_kwargs(
    registry_entry: er.RegistryEntry,
    candidate: EntityCandidate,
    *,
    current_entity_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Return safe registry metadata changes without touching user custom names."""
    kwargs: dict[str, Any] = {}
    if new_entity_id := safe_entity_id_migration(
        registry_entry,
        candidate,
        current_entity_ids=current_entity_ids,
    ):
        kwargs["new_entity_id"] = new_entity_id
    if getattr(registry_entry, "original_name", None) != candidate.name:
        kwargs["original_name"] = candidate.name
    if getattr(registry_entry, "original_icon", None) != candidate.icon:
        kwargs["original_icon"] = candidate.icon
    category = ha_entity_category(candidate.entity_category)
    current = getattr(registry_entry, "entity_category", None)
    if current not in {category, getattr(category, "value", None)}:
        kwargs["entity_category"] = category
    if getattr(registry_entry, "has_entity_name", None) is not True:
        kwargs["has_entity_name"] = True
    return kwargs
