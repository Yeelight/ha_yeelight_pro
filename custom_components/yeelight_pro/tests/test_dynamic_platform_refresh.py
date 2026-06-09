"""Platform-level dynamic entity refresh tests."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.yeelight_pro.const import DOMAIN
from custom_components.yeelight_pro.fan import async_setup_entry as async_setup_fan_entry
from custom_components.yeelight_pro.light import (
    async_setup_entry as async_setup_light_entry,
)

from .dynamic_entity_helpers import (
    entry_with_unload_hook,
    legacy_fan,
    legacy_light,
)


@pytest.mark.asyncio
async def test_light_platform_adds_new_entities_after_refresh(mock_hass) -> None:
    """light 平台应在 coordinator refresh 后补建新灯实体."""
    coordinator = MagicMock()
    coordinator.hass = None
    coordinator.data = {1: legacy_light(1, name="客厅灯")}
    coordinator.devices = coordinator.data
    coordinator.get_device.side_effect = (
        lambda device_id: coordinator.data.get(device_id)
    )
    listeners: list = []

    def _add_listener(listener):
        listeners.append(listener)
        return lambda: None

    coordinator.async_add_listener = MagicMock(side_effect=_add_listener)

    entry = entry_with_unload_hook()
    mock_hass.data = {DOMAIN: {entry.entry_id: {"coordinator": coordinator}}}
    add_entities = MagicMock()

    await async_setup_light_entry(mock_hass, entry, add_entities)

    assert add_entities.call_count == 1
    assert [entity.unique_id for entity in add_entities.call_args.args[0]] == [
        "yeelight_pro_1_light"
    ]
    assert len(listeners) == 1

    coordinator.data = {
        1: legacy_light(1, name="客厅灯"),
        2: legacy_light(2, name="卧室灯"),
    }
    coordinator.devices = coordinator.data
    listeners[0]()

    assert add_entities.call_count == 2
    assert [entity.unique_id for entity in add_entities.call_args.args[0]] == [
        "yeelight_pro_2_light"
    ]

    listeners[0]()
    assert add_entities.call_count == 2


@pytest.mark.asyncio
async def test_fan_platform_adds_new_entities_after_refresh(mock_hass) -> None:
    """fan 平台应在 coordinator refresh 后补建新风扇实体."""
    coordinator = MagicMock()
    coordinator.hass = None
    coordinator.data = {1: legacy_fan(1, name="客厅风扇")}
    coordinator.devices = coordinator.data
    coordinator.get_device.side_effect = (
        lambda device_id: coordinator.data.get(device_id)
    )
    listeners: list = []

    def _add_listener(listener):
        listeners.append(listener)
        return lambda: None

    coordinator.async_add_listener = MagicMock(side_effect=_add_listener)

    entry = entry_with_unload_hook()
    mock_hass.data = {DOMAIN: {entry.entry_id: {"coordinator": coordinator}}}
    add_entities = MagicMock()

    await async_setup_fan_entry(mock_hass, entry, add_entities)

    assert add_entities.call_count == 1
    first_entities = add_entities.call_args.args[0]
    assert [entity.unique_id for entity in first_entities] == [
        "yeelight_pro_1_fan"
    ]
    assert [entity._component_id for entity in first_entities] == ["fan"]
    assert len(listeners) == 1

    coordinator.data = {
        1: legacy_fan(1, name="客厅风扇"),
        2: legacy_fan(2, name="卧室风扇"),
    }
    coordinator.devices = coordinator.data
    listeners[0]()

    assert add_entities.call_count == 2
    second_entities = add_entities.call_args.args[0]
    assert [entity.unique_id for entity in second_entities] == [
        "yeelight_pro_2_fan"
    ]
    assert [entity._component_id for entity in second_entities] == ["fan"]

    listeners[0]()
    assert add_entities.call_count == 2
