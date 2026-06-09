"""Helpers for reconciling projected Yeelight Pro entities with HA's registry."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN
from .entity_candidates import (
    EntityCandidateCoordinator,
    EntityKey,
    collect_entity_candidate_keys,
)
from .entity_lifecycle_cleanup import (
    EntityRegistryCleanupAudit,
    EntityRegistryCleanupPreview,
    async_disable_stale_registry_entities,
    async_preview_stale_registry_cleanup,
    entity_registry_cleanup_diagnostics,
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

    def as_diagnostics(self) -> dict[str, int]:
        """Return a diagnostics-safe aggregate payload."""
        return {
            "active": self.active,
            "registry_entries": self.registry_entries,
            "stale": self.stale,
            "pending_stale": self.pending_stale,
            "disabled": self.disabled,
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
    return getattr(registry_entry, "disabled_by", None) == er.RegistryEntryDisabler.USER


async def async_reconcile_entity_registry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: EntityLifecycleCoordinator,
) -> set[str]:
    """Track stale registry entries without mutating Home Assistant registries."""
    active_entity_keys = collect_active_entity_keys(coordinator)
    registry_entries, stale_entries = _collect_registry_entries(
        hass,
        entry,
        active_entity_keys,
    )
    stale_keys = set(stale_entries)
    pending_stale_keys = _pending_stale_entity_keys(coordinator)
    pending_stale_keys.intersection_update(stale_keys)
    pending_stale_keys.update(stale_keys)

    setattr(
        coordinator,
        _LAST_RECONCILE_SUMMARY,
        EntityRegistryReconcileSummary(
            active=len(active_entity_keys),
            registry_entries=len(registry_entries),
            stale=len(stale_keys),
            pending_stale=len(pending_stale_keys),
            disabled=0,
        ),
    )
    _LOGGER.info(
        "Reconciled Yeelight Pro entity registry for entry %s: active=%s "
        "pending_stale=%s disabled=%s",
        entry.entry_id,
        len(active_entity_keys),
        len(pending_stale_keys),
        0,
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
