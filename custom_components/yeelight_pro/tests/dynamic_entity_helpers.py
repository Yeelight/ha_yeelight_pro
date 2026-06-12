"""Shared helpers for dynamic entity tests."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from homeassistant.helpers.entity import Entity

from custom_components.yeelight_pro import dynamic_entities
from custom_components.yeelight_pro.const import DOMAIN


class DummyEntity(Entity):
    """Minimal entity with a stable unique id."""

    def __init__(
        self,
        unique_id: str,
        *,
        device_id: int | None = None,
        source_device_id: int | None = None,
    ) -> None:
        self._attr_unique_id = unique_id
        if device_id is not None:
            self._device_id = device_id
        if source_device_id is not None:
            self._source_device_id = source_device_id


def legacy_light(device_id: int, *, name: str) -> dict:
    """Build a minimal legacy light payload accepted by the light projector."""
    return {
        "device_id": device_id,
        "name": name,
        "type": "light",
        "online": True,
        "params": {"p": True, "l": 80},
    }


def legacy_fresh_air(device_id: int, *, name: str) -> dict:
    """Build a minimal fresh-air payload accepted by the fan projector."""
    return {
        "device_id": device_id,
        "name": name,
        "type": "temp_control",
        "category": "temp_control",
        "online": True,
        "params": {"vmcp": True, "vmcf": 50},
    }


def entry_with_unload_hook() -> MagicMock:
    """Build a config-entry mock that records unload callbacks."""
    entry = MagicMock()
    entry.entry_id = "entry_1"
    entry.async_on_unload = MagicMock()
    return entry


def coordinator_with_device_filter(filter_config: dict) -> MagicMock:
    """Build a coordinator double with runtime device import filter options."""
    coordinator = MagicMock()
    coordinator.hass = None
    coordinator.data = {
        1: {"id": 1, "device_id": 1, "category": "light"},
        2: {"id": 2, "device_id": 2, "category": "curtain"},
    }
    coordinator.options = {"device_import_filter": filter_config}
    coordinator.get_device.side_effect = (
        lambda device_id: coordinator.data.get(device_id)
    )
    coordinator.async_add_listener = MagicMock(return_value=lambda: None)
    return coordinator


def registry_entry(
    *,
    unique_id: str,
    entity_id: str,
    domain: str,
    disabled_by: str | None = None,
    config_entry_id: str = "entry_1",
) -> SimpleNamespace:
    """Build a focused HA registry entry double."""
    return SimpleNamespace(
        platform=DOMAIN,
        unique_id=unique_id,
        entity_id=entity_id,
        domain=domain,
        disabled_by=disabled_by,
        config_entry_id=config_entry_id,
    )


def patch_entity_registry(
    monkeypatch,
    entries: list[SimpleNamespace],
    *,
    global_entries: list[SimpleNamespace] | None = None,
) -> None:
    """Patch HA entity registry access for dynamic entity helper tests."""
    registry = MagicMock()
    registry.entities = {
        entry.entity_id: entry for entry in [*entries, *(global_entries or [])]
    }
    monkeypatch.setattr(dynamic_entities.er, "async_get", lambda hass: registry)
    monkeypatch.setattr(
        dynamic_entities.er,
        "async_entries_for_config_entry",
        lambda registry, entry_id: list(entries),
    )


def hass_with_state(state) -> SimpleNamespace:
    """Build a minimal hass double with state lookup."""
    return SimpleNamespace(states=SimpleNamespace(get=MagicMock(return_value=state)))
