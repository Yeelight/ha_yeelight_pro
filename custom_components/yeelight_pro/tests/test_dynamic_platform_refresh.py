"""Platform-level dynamic entity refresh tests."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.yeelight_pro.const import DOMAIN
from custom_components.yeelight_pro.identity import entry_identity_scope, scoped_entity_unique_id
from custom_components.yeelight_pro.fan import async_setup_entry as async_setup_fan_entry
from custom_components.yeelight_pro.light import (
    _iter_light_entities,
    async_setup_entry as async_setup_light_entry,
)

from .dynamic_entity_helpers import (
    entry_with_unload_hook,
    legacy_fresh_air,
    legacy_light,
)


@pytest.mark.asyncio
async def test_light_platform_adds_new_entities_after_refresh(mock_hass) -> None:
    """light 平台应在 coordinator refresh 后补建新灯实体."""
    coordinator = MagicMock()
    coordinator.hass = None
    coordinator.data = {1: legacy_light(1, name="客厅灯")}
    coordinator.devices = coordinator.data
    coordinator.groups = []
    coordinator.rooms = []
    coordinator.areas = []
    coordinator.houses = []
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
async def test_light_platform_adds_topology_node_entities_after_refresh(mock_hass) -> None:
    """light 平台应在拓扑刷新后补建房间/区域/整屋总控实体."""
    coordinator = MagicMock()
    coordinator.hass = None
    coordinator.entry_data = {}
    coordinator.house_id = 12345
    coordinator.data = {}
    coordinator.devices = {}
    coordinator.groups = []
    coordinator.rooms = []
    coordinator.areas = []
    coordinator.houses = []
    coordinator.get_device.return_value = None
    listeners: list = []

    def _add_listener(listener):
        listeners.append(listener)
        return lambda: None

    coordinator.async_add_listener = MagicMock(side_effect=_add_listener)

    entry = entry_with_unload_hook()
    mock_hass.data = {DOMAIN: {entry.entry_id: {"coordinator": coordinator}}}
    add_entities = MagicMock()

    await async_setup_light_entry(mock_hass, entry, add_entities)

    assert add_entities.call_count == 0
    assert len(listeners) == 1

    coordinator.rooms = [{"id": "room_1", "name": "客厅", "params": {"p": True}}]
    coordinator.areas = [{"id": "area_1", "name": "一楼", "params": {"p": True}}]
    coordinator.houses = [{"id": "house_1", "name": "星河暖居", "params": {"p": True}}]
    listeners[0]()

    assert add_entities.call_count == 1
    scope = entry_identity_scope({}, 12345)
    assert [entity.unique_id for entity in add_entities.call_args.args[0]] == [
        scoped_entity_unique_id(scope, "room", "room_1", "light"),
        scoped_entity_unique_id(scope, "area", "area_1", "light"),
        scoped_entity_unique_id(scope, "house", "house_1", "light"),
    ]


def test_light_entity_factory_uses_payload_source_device_id() -> None:
    """平台实体创建必须使用 payload 真实 id，不能依赖 coordinator.data 的临时 key."""
    coordinator = MagicMock()
    coordinator.entry_data = {}
    coordinator.house_id = 0
    coordinator.data = {"temporary-key": legacy_light(304784333, name="厨房操作台灯")}
    coordinator.devices = {304784333: coordinator.data["temporary-key"]}
    coordinator.groups = []
    coordinator.rooms = []
    coordinator.areas = []
    coordinator.houses = []
    coordinator.get_device.side_effect = lambda device_id: coordinator.devices.get(
        int(device_id)
    )

    entities = _iter_light_entities(coordinator)

    assert [entity._device_id for entity in entities] == [304784333]
    assert [entity.unique_id for entity in entities] == ["yeelight_pro_304784333_light"]
    assert entities[0].name is None


@pytest.mark.asyncio
async def test_fan_platform_adds_new_entities_after_refresh(mock_hass) -> None:
    """fan 平台应在 coordinator refresh 后补建新风实体."""
    coordinator = MagicMock()
    coordinator.hass = None
    coordinator.data = {1: legacy_fresh_air(1, name="客厅新风")}
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
        "yeelight_pro_1_fresh_air"
    ]
    assert [entity._component_id for entity in first_entities] == ["fresh_air"]
    assert len(listeners) == 1

    coordinator.data = {
        1: legacy_fresh_air(1, name="客厅新风"),
        2: legacy_fresh_air(2, name="卧室新风"),
    }
    coordinator.devices = coordinator.data
    listeners[0]()

    assert add_entities.call_count == 2
    second_entities = add_entities.call_args.args[0]
    assert [entity.unique_id for entity in second_entities] == [
        "yeelight_pro_2_fresh_air"
    ]
    assert [entity._component_id for entity in second_entities] == ["fresh_air"]

    listeners[0]()
    assert add_entities.call_count == 2
