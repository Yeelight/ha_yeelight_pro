"""Diagnostics filter preview tests for Yeelight Pro."""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.const import CONF_DEVICE_IMPORT_FILTER
from custom_components.yeelight_pro.diagnostics import (
    async_get_config_entry_diagnostics,
)

from .diagnostics_helpers import (
    build_diagnostics_entry,
    build_filter_preview_coordinator,
    install_runtime_entry,
)


@pytest.fixture
def diagnostics_entry() -> MagicMock:
    """Build a diagnostics config entry."""
    return build_diagnostics_entry()


@pytest.mark.asyncio
async def test_diagnostics_entity_filter_preview_counts_device_candidates(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
) -> None:
    """实体过滤预览应反映设备候选变化，同时保留辅助拓扑候选."""
    coordinator = build_filter_preview_coordinator()
    diagnostics_entry.options[CONF_DEVICE_IMPORT_FILTER] = {
        "enabled": True,
        "exclude": {"devices": ["vacuum-secret"]},
    }
    install_runtime_entry(hass, diagnostics_entry, coordinator)

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)

    assert data["runtime"]["entity_candidates"] == {
        "total": 8,
        "platforms": {
            "button": 1,
            "number": 2,
            "select": 3,
            "switch": 2,
        },
        "device_platforms": {
            "switch": 2,
        },
        "sources": {
            "device": 2,
            "group": 2,
            "house": 3,
            "scene": 1,
        },
        "source_classes": {"device": 2, "topology": 6},
        "duplicate_key_count": 0,
        "availability": {"available": 8, "unavailable": 0},
    }
    assert data["runtime"]["entity_import_filter_preview"] == {
        "total": 8,
        "platforms": {
            "button": 1,
            "number": 2,
            "select": 3,
            "switch": 2,
        },
        "device_platforms": {
            "switch": 2,
        },
        "sources": {
            "device": 2,
            "group": 2,
            "house": 3,
            "scene": 1,
        },
        "source_classes": {"device": 2, "topology": 6},
        "duplicate_key_count": 0,
        "availability": {"available": 8, "unavailable": 0},
    }
    dumped = json.dumps(data, ensure_ascii=False)
    assert "relay-secret" not in dumped
    assert "vacuum-secret" not in dumped
    assert "group-secret" not in dumped
    assert "scene-secret" not in dumped
    assert "429392" not in dumped
