"""Registry metadata synchronization helpers for Yeelight Pro entities."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .entity_category import ha_entity_category
from .entity_candidates import EntityCandidate, EntityKey
from .entity_lifecycle_entity_id import (
    all_registry_entity_ids,
    safe_entity_id_migration,
)

_LOGGER = logging.getLogger(__name__)


def restore_active_integration_entries(
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
        registry_domain = registry_entry_domain(registry_entry)
        if registry_domain is None:
            continue
        registry_key = (registry_domain, registry_entry.unique_id)
        if (
            registry_key not in active_entity_keys
            or not registry_entry_disabled_by_integration(registry_entry)
        ):
            continue
        entity_registry.async_update_entity(
            registry_entry.entity_id,
            disabled_by=None,
        )
        restored += 1
    return restored


def sync_active_registry_metadata(
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
        registry_domain = registry_entry_domain(registry_entry)
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


def registry_entry_domain(registry_entry: er.RegistryEntry) -> str | None:
    """Return the HA entity domain for a registry entry."""
    domain = getattr(registry_entry, "domain", None)
    if isinstance(domain, str) and domain:
        return domain
    entity_id = getattr(registry_entry, "entity_id", "")
    if isinstance(entity_id, str) and "." in entity_id:
        return entity_id.split(".", 1)[0]
    return None


def registry_entry_disabled_by_integration(registry_entry: er.RegistryEntry) -> bool:
    """Return whether the registry entry was automatically disabled by this integration."""
    return getattr(registry_entry, "disabled_by", None) in {
        er.RegistryEntryDisabler.INTEGRATION,
        "integration",
    }


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
                registry_entry_domain(registry_entry),
            )
            return {}
        entity_registry.async_update_entity(registry_entry.entity_id, **metadata_kwargs)
        _LOGGER.debug(
            "Applied partial Yeelight Pro registry metadata update after "
            "entity_id migration failed: domain=%s fields=%s "
            "skipped_field=new_entity_id reason=entity_id_conflict",
            registry_entry_domain(registry_entry),
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


__all__ = [
    "registry_entry_disabled_by_integration",
    "registry_entry_domain",
    "restore_active_integration_entries",
    "sync_active_registry_metadata",
]
