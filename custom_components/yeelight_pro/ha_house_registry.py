"""House-level device-registry helpers for Yeelight Pro."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import device_registry as dr

from .house_metadata import house_device_info, is_house_placeholder_name


def sync_house_device(
    device_registry: dr.DeviceRegistry,
    entry: ConfigEntry,
    coordinator: Any,
    *,
    normalize_registry_pairs: Any,
    sync_metadata: Any,
) -> None:
    """Keep house-level helper devices off legacy placeholder names."""
    device_info = house_device_info(coordinator)
    identifiers = normalize_registry_pairs(device_info.get("identifiers"))
    if not identifiers:
        return

    device_entries = _house_device_entries(device_registry, entry, identifiers)
    if not device_entries:
        device_entries = [_create_house_device(device_registry, entry, device_info, identifiers)]
    for device_entry in device_entries:
        _sync_house_device_entry(
            device_registry,
            device_entry,
            device_info=device_info,
            identifiers=_safe_house_identifiers(device_entry, device_entries, identifiers),
            sync_metadata=sync_metadata,
        )


def _create_house_device(
    device_registry: dr.DeviceRegistry,
    entry: ConfigEntry,
    device_info: Mapping[str, Any],
    identifiers: set[tuple[str, str]],
) -> dr.DeviceEntry:
    """Create the current house helper device when no legacy entry exists."""
    return device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers=identifiers,
        manufacturer=device_info.get("manufacturer"),
        model=device_info.get("model"),
        name=device_info.get("name"),
    )


def _house_device_entries(
    device_registry: dr.DeviceRegistry,
    entry: ConfigEntry,
    identifiers: set[tuple[str, str]],
) -> list[dr.DeviceEntry]:
    """Return current and legacy house helper devices for one config entry."""
    return [
        item
        for item in device_registry.devices.values()
        if entry.entry_id in item.config_entries and bool(item.identifiers & identifiers)
    ]


def _safe_house_identifiers(
    device_entry: dr.DeviceEntry,
    device_entries: Iterable[dr.DeviceEntry],
    identifiers: set[tuple[str, str]],
) -> set[tuple[str, str]]:
    """Avoid adding identifiers already present on duplicate legacy entries."""
    occupied = {
        identifier
        for other_entry in device_entries
        if other_entry.id != device_entry.id
        for identifier in other_entry.identifiers
    }
    return device_entry.identifiers | (identifiers - occupied)


def _sync_house_device_entry(
    device_registry: dr.DeviceRegistry,
    device_entry: dr.DeviceEntry,
    *,
    device_info: Mapping[str, Any],
    identifiers: set[tuple[str, str]],
    sync_metadata: Any,
) -> dr.DeviceEntry:
    """Update one house helper device while preserving non-placeholder user names."""
    updated = sync_metadata(
        device_registry,
        device_entry,
        device_info=device_info,
        identifiers=identifiers,
        connections=set(),
    )
    if is_house_placeholder_name(updated.name_by_user):
        return device_registry.async_update_device(updated.id, name_by_user=None) or updated
    return updated


__all__ = ["sync_house_device"]
