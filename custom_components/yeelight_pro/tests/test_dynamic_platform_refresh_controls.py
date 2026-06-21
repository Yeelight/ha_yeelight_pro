"""Dynamic refresh tests for property-control and diagnostic platforms."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.yeelight_pro.const import DOMAIN
from custom_components.yeelight_pro.number import async_setup_entry as async_setup_number_entry
from custom_components.yeelight_pro.sensor import async_setup_entry as async_setup_sensor_entry
from custom_components.yeelight_pro.switch import async_setup_entry as async_setup_switch_entry

from .dynamic_entity_helpers import entry_with_unload_hook
from .projection_helpers import projection_payload


@pytest.mark.asyncio
async def test_property_control_platforms_add_p20_entities_after_refresh(
    mock_hass,
) -> None:
    """P20 音乐组件属性在拓扑刷新后应补建 switch/number/sensor 实体."""
    coordinator = MagicMock()
    coordinator.hass = None
    coordinator.hide_unknown_entities = True
    coordinator.data = {}
    coordinator.devices = {}
    coordinator.groups = []
    coordinator.get_device.side_effect = (
        lambda device_id: coordinator.data.get(str(device_id))
    )
    listeners: list = []

    def _add_listener(listener):
        listeners.append(listener)
        return lambda: None

    coordinator.async_add_listener = MagicMock(side_effect=_add_listener)

    entry = entry_with_unload_hook()
    mock_hass.data = {DOMAIN: {entry.entry_id: {"coordinator": coordinator}}}
    switch_add = MagicMock()
    number_add = MagicMock()
    sensor_add = MagicMock()

    await async_setup_switch_entry(mock_hass, entry, switch_add)
    await async_setup_number_entry(mock_hass, entry, number_add)
    await async_setup_sensor_entry(mock_hass, entry, sensor_add)

    switch_add.assert_not_called()
    number_add.assert_not_called()
    sensor_add.assert_not_called()
    assert len(listeners) == 3

    coordinator.data = {"p20-1": _p20_music_payload("p20-1")}
    coordinator.devices = coordinator.data
    for listener in listeners:
        listener()

    assert [entity.unique_id for entity in switch_add.call_args.args[0]] == [
        "yeelight_pro_p20-1_other_mpmp_switch",
        "yeelight_pro_p20-1_other_mpmr_switch",
    ]
    assert [entity.unique_id for entity in number_add.call_args.args[0]] == [
        "yeelight_pro_p20-1_other_mpml_number",
        "yeelight_pro_p20-1_other_mppm_number",
    ]
    assert [entity.unique_id for entity in sensor_add.call_args.args[0]] == [
        "yeelight_pro_p20-1_online_status"
    ]


@pytest.mark.asyncio
async def test_sensor_platform_adds_gateway_online_status_after_refresh(
    mock_hass,
) -> None:
    """网关设备刷新出现后，sensor 平台应补建在线状态诊断实体."""
    coordinator = MagicMock()
    coordinator.hass = None
    coordinator.hide_unknown_entities = True
    coordinator.data = {}
    coordinator.devices = {}
    coordinator.get_device.side_effect = (
        lambda device_id: coordinator.data.get(str(device_id))
    )
    listeners: list = []

    def _add_listener(listener):
        listeners.append(listener)
        return lambda: None

    coordinator.async_add_listener = MagicMock(side_effect=_add_listener)

    entry = entry_with_unload_hook()
    mock_hass.data = {DOMAIN: {entry.entry_id: {"coordinator": coordinator}}}
    add_entities = MagicMock()

    await async_setup_sensor_entry(mock_hass, entry, add_entities)

    add_entities.assert_not_called()

    coordinator.data = {"gateway-1": _gateway_payload("gateway-1")}
    coordinator.devices = coordinator.data
    listeners[0]()

    assert [entity.unique_id for entity in add_entities.call_args.args[0]] == [
        "yeelight_pro_gateway-1_online_status"
    ]


def _p20_music_payload(device_id: str) -> dict:
    """Build a P20-like music component payload from documented properties."""
    device = projection_payload(
        device_id=device_id,
        category="other",
        component_id="other",
        component_category="other",
        state={},
        params={},
        online=True,
    )
    device["name"] = "P20 全景屏"
    device["ha_device_instance"]["name"] = "P20 全景屏"
    device["ha_product_model"]["components"][0]["properties"] = [
        {
            "prop_id": "mpmp",
            "name": "music player play pause,音乐播放器播放/暂停",
            "access": "read_write",
            "property_type": "config",
            "format": "boolean",
        },
        {
            "prop_id": "mpmr",
            "name": "music player music rhythm,音乐播放器音乐律动",
            "access": "read_write",
            "property_type": "config",
            "format": "boolean",
        },
        {
            "prop_id": "mpml",
            "name": "music player music list,音乐播放器歌单ID",
            "access": "read_write",
            "property_type": "config",
            "format": "uint16",
            "value_range": {"min": 0, "max": 65535, "step": 1},
        },
        {
            "prop_id": "mppm",
            "name": "music player play mode,音乐播放器播放模式",
            "access": "read_write",
            "property_type": "config",
            "format": "uint16",
            "value_range": {"min": 0, "max": 10, "step": 1},
        },
        {
            "prop_id": "o",
            "name": "在线状态",
            "access": "read_only",
            "property_type": "bool",
            "format": "boolean",
        },
    ]
    device["ha_device_instance"]["components"][0]["state"] = {"o": True}
    return device


def _gateway_payload(device_id: str) -> dict:
    """Build a gateway payload with only documented online-state evidence."""
    device = projection_payload(
        device_id=device_id,
        category="gateway",
        component_id="gateway",
        component_category="gateway",
        state={"o": True},
        params={"o": True},
        online=True,
    )
    device["name"] = "DALI 网关"
    device["ha_device_instance"]["name"] = "DALI 网关"
    device["ha_product_model"]["components"][0]["properties"] = [
        {
            "prop_id": "o",
            "name": "在线状态",
            "access": "read_only",
            "property_type": "bool",
            "format": "boolean",
        }
    ]
    return device
