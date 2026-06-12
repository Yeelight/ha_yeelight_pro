"""Shared diagnostics test helper facade for Yeelight Pro."""
from __future__ import annotations

from collections.abc import Sequence
from unittest.mock import MagicMock

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.const import (
    CONF_CLOUD_DOMAIN,
    CONF_CONNECTION_MODE,
    CONF_DEVICE_IMPORT_FILTER,
    CONF_DEBUG_MODE,
    CONF_HIDE_UNKNOWN_ENTITIES,
    CONF_HOUSE_ID,
    CONF_SCAN_INTERVAL,
    CONF_TOPOLOGY_CHANGE_REPAIRS,
    CONNECTION_MODE_CLOUD,
    DOMAIN,
)

from .diagnostics_runtime_helpers import (
    aggregate_runtime_secret_markers,
    build_aggregate_runtime_coordinator as _build_aggregate_runtime_coordinator,
)

__all__ = [
    "aggregate_runtime_secret_markers",
    "build_aggregate_runtime_coordinator",
    "build_diagnostics_entry",
    "build_empty_diagnostics_coordinator",
    "build_filter_preview_coordinator",
    "install_runtime_entry",
]


def build_diagnostics_entry() -> MagicMock:
    """Build a config entry carrying sensitive values."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "entry-sensitive"
    entry.data = {
        CONF_CONNECTION_MODE: CONNECTION_MODE_CLOUD,
        CONF_ACCESS_TOKEN: "token-secret",
        CONF_HOUSE_ID: 429392,
        CONF_CLOUD_DOMAIN: "https://private-api.example.test/apis/iot",
    }
    entry.options = {
        CONF_SCAN_INTERVAL: 15,
        CONF_DEBUG_MODE: True,
        CONF_HIDE_UNKNOWN_ENTITIES: False,
        CONF_TOPOLOGY_CHANGE_REPAIRS: False,
        CONF_DEVICE_IMPORT_FILTER: {
            "enabled": True,
            "exclude": {
                "devices": ["device-secret-2"],
                "rooms": ["room-secret"],
                "unsupported": ["token-secret", "house-secret"],
            },
        },
    }
    return entry


def install_runtime_entry(
    hass: HomeAssistant,
    entry: MagicMock,
    coordinator: MagicMock,
    *,
    platforms: Sequence[str] = (),
) -> None:
    """Install a loaded diagnostics runtime entry into hass data."""
    hass.data[DOMAIN] = {
        entry.entry_id: {
            "entry": entry,
            "coordinator": coordinator,
            "platforms": list(platforms),
        }
    }


def build_empty_diagnostics_coordinator(
    *,
    last_update_success: bool = True,
    last_exception: BaseException | None = None,
    topology_generation: int = 1,
    topology_diff_summary: object | None = None,
    product_schema_cache_size: int = 0,
    hide_unknown_entities: bool = False,
) -> MagicMock:
    """Build a diagnostics coordinator double with empty topology collections."""
    coordinator = MagicMock()
    coordinator.scan_interval = 15
    coordinator.debug_mode = True
    coordinator.hide_unknown_entities = hide_unknown_entities
    coordinator.last_update_success = last_update_success
    coordinator.last_exception = last_exception
    coordinator.topology_generation = topology_generation
    coordinator.topology_diff_summary = topology_diff_summary
    coordinator.product_schema_cache_size = product_schema_cache_size
    coordinator.property_hydration_diagnostics = {}
    coordinator.devices = {}
    coordinator.gateways = {}
    coordinator.areas = []
    coordinator.rooms = []
    coordinator.groups = []
    coordinator.scenes = []
    return coordinator


def build_aggregate_runtime_coordinator() -> MagicMock:
    """Build the aggregate runtime coordinator used by diagnostics tests."""
    return _build_aggregate_runtime_coordinator(build_empty_diagnostics_coordinator)


def build_filter_preview_coordinator() -> MagicMock:
    """Build a coordinator with device candidates for filter preview tests."""
    coordinator = build_empty_diagnostics_coordinator(hide_unknown_entities=True)
    coordinator.house_id = 429392
    coordinator.devices = {
        1: {
            "id": "relay-secret",
            "device_id": "relay-secret",
            "category": "relay_switch",
            "type": "switch",
            "online": True,
            "params": {"1-p": True, "2-sp": False},
        },
        2: {
            "id": "vacuum-secret",
            "device_id": "vacuum-secret",
            "category": "other",
            "type": "vacuum",
            "online": True,
            "params": {"status": "idle", "battery": 80},
        },
    }
    coordinator.groups = [{"id": "group-secret"}]
    coordinator.scenes = [{"id": "scene-secret"}]
    return coordinator
