"""LAN topology normalization tests based on Yeelight IoT documents."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.yeelight_pro.const import DOMAIN
from custom_components.yeelight_pro.core.coordinator import YeelightProCoordinator
from custom_components.yeelight_pro.core.device_payload import DevicePayloadBuilder
from custom_components.yeelight_pro.core.lan_topology_payload import (
    build_lan_topology_payloads,
)
from custom_components.yeelight_pro.entity_candidates import iter_device_entity_candidates
from custom_components.yeelight_pro.ha_device_registry import async_sync_gateway_devices


def _build(nodes: list[dict]) -> dict[int, dict]:
    return build_lan_topology_payloads(
        nodes,
        builder=DevicePayloadBuilder(),
        apply_runtime_overrides=lambda payload: payload,
    ).devices


def test_lan_topology_builds_canonical_light_with_room_metadata() -> None:
    """LAN type=3 应按易来色温灯能力入模，并带入房间和设备 registry 元数据."""
    result = build_lan_topology_payloads(
        [
            {"id": 201, "nt": 1, "n": "客厅"},
            {"id": 1001, "nt": 2, "type": 3, "n": "客厅灯", "roomid": 201},
        ],
        builder=DevicePayloadBuilder(),
        apply_runtime_overrides=lambda payload: payload,
    )

    device = result.devices[1001]
    device_info = device["ha_device_instance"]["device_info"]

    assert device["iot_category"] == "light"
    assert device["ha_platform_candidates"] == ["light"]
    assert device["model"] == "色温灯"
    assert device["model_id"] == "YL-LAN-3"
    assert device["room_name"] == "客厅"
    assert device_info["suggested_area"] == "客厅"
    assert device_info["identifiers"] == [
        ["yeelight_pro", "1001"],
        ["yeelight_pro", "device:1001"],
    ]


def test_lan_topology_ignores_misleading_user_device_names() -> None:
    """用户名称不能覆盖 LAN type 和属性能力给出的真实设备类型。"""
    devices = _build([
        {"id": 1002, "nt": 2, "type": 3, "n": "厨房烟雾传感器"},
        {"id": 1003, "nt": 2, "type": 130, "n": "客厅灯"},
    ])

    light = devices[1002]
    contact = devices[1003]

    assert light["iot_category"] == "light"
    assert light["ha_platform"] == "light"
    assert light["device_info"]["model"] == "色温灯"
    assert contact["iot_category"] == "contact_sensor"
    assert contact["ha_platform_candidates"] == ["binary_sensor", "event"]
    assert contact["device_info"]["model"] == "门磁传感器"


def test_lan_temperature_humidity_sensor_stays_sensor_not_climate() -> None:
    """LAN type=136 是温湿度传感器，不应被温控类 climate 抢占。"""
    device = _build([
        {"id": 1004, "nt": 2, "type": 136, "n": "主卧环境"},
    ])[1004]
    candidates = list(iter_device_entity_candidates(device))

    assert device["iot_category"] == "other"
    assert device["ha_platform_candidates"] == ["sensor"]
    assert device["device_info"]["model"] == "温湿度传感器"
    assert {(item.platform, item.name) for item in candidates} == {
        ("sensor", "温度"),
        ("sensor", "湿度"),
    }


def test_lan_multi_switch_channels_use_friendly_names() -> None:
    """LAN ch_num/cids 应生成索引组件，让多键开关显示左键/中键/右键。"""
    device = _build([
        {
            "id": 1005,
            "nt": 2,
            "type": 13,
            "n": "厨房开关",
            "ch_num": 3,
            "cids": [11, 12, 13],
        },
    ])[1005]
    candidates = [
        item
        for item in iter_device_entity_candidates(device)
        if item.platform == "switch"
    ]

    assert device["iot_category"] == "relay_switch"
    assert device["params"] == {"1-sp": False, "2-sp": False, "3-sp": False}
    assert [item.component_id for item in candidates] == [
        "switch_1",
        "switch_2",
        "switch_3",
    ]
    assert [item.name for item in candidates] == ["左键", "中键", "右键"]


@pytest.mark.asyncio
async def test_lan_topology_syncs_source_devices_and_relinks_entities(
    hass: HomeAssistant,
) -> None:
    """LAN-only 拓扑设备也必须进入 HA device registry 并回链既有实体。"""
    entry = MockConfigEntry(domain=DOMAIN, entry_id="entry-lan")
    entry.add_to_hass(hass)
    entity_registry = er.async_get(hass)
    entity_entry = entity_registry.async_get_or_create(
        "light",
        DOMAIN,
        "yeelight_pro_1001_light",
        config_entry=entry,
    )
    coordinator = YeelightProCoordinator(hass=hass, client=None, house_id=0)

    await coordinator.async_handle_lan_payload(
        {
            "id": 13812,
            "method": "gateway_post.topology",
            "nodes": [
                {"id": 201, "nt": 1, "n": "客厅"},
                {"id": 1001, "nt": 2, "type": 3, "n": "客厅灯", "roomid": 201},
            ],
        }
    )
    await async_sync_gateway_devices(hass, entry, coordinator)

    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, "1001")})
    linked_entity = entity_registry.async_get(entity_entry.entity_id)

    assert device is not None
    assert device.name == "客厅灯"
    assert device.model == "色温灯"
    assert linked_entity is not None
    assert linked_entity.device_id == device.id
    await coordinator.async_shutdown()


@pytest.mark.asyncio
async def test_coordinator_applies_lan_areas_groups_scenes(
    hass: HomeAssistant,
) -> None:
    """LAN nt=1/3/4/6 应分别进入房间、区域、组和情景缓存。"""
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=None,
        house_id=12345,
    )
    listener = MagicMock()
    remove_listener = coordinator.async_add_listener(listener)

    events = await coordinator.async_handle_lan_payload(
        {
            "id": 13813,
            "method": "gateway_post.topology",
            "nodes": [
                {"id": 201, "nt": 1, "n": "客厅", "o": True, "params": {"p": True}},
                {"id": 301, "nt": 3, "n": "一楼", "o": False, "params": {"p": False}},
                {"id": 5001, "nt": 5, "n": "绿地中央公园"},
                {"id": 1001, "nt": 2, "type": 3, "n": "客厅灯", "roomid": 201},
                {
                    "id": 3001,
                    "nt": 4,
                    "type": 1,
                    "n": "客厅灯组",
                    "o": True,
                    "params": {"p": True, "l": 80, "ct": 4000},
                },
                {"id": 4001, "nt": 6, "n": "回家", "params": {"state": "inactive"}},
            ],
        }
    )

    assert events == []
    assert coordinator.data == coordinator.devices
    assert list(coordinator.devices) == [1001]
    assert coordinator.rooms == [
        {
            "id": 201,
            "name": "客厅",
            "type": None,
            "node_type": 1,
            "online": True,
            "params": {"p": True},
        }
    ]
    assert coordinator.areas == [
        {
            "id": 301,
            "name": "一楼",
            "type": None,
            "node_type": 3,
            "online": False,
            "params": {"p": False},
        }
    ]
    assert coordinator.groups == [
        {
            "id": 3001,
            "name": "客厅灯组",
            "type": 1,
            "node_type": 4,
            "online": True,
            "params": {"p": True, "l": 80, "ct": 4000},
        }
    ]
    assert coordinator.houses == [
        {"id": 5001, "name": "绿地中央公园", "type": None, "node_type": 5}
    ]
    assert coordinator.scenes == [
        {"id": 4001, "name": "回家", "params": {"state": "inactive"}, "state": "inactive"}
    ]
    assert coordinator.topology_generation == 1
    listener.assert_called_once()
    remove_listener()
    await coordinator.async_shutdown()


@pytest.mark.asyncio
async def test_coordinator_merges_lan_scene_state_push(
    hass: HomeAssistant,
) -> None:
    """LAN prop 场景状态推送应合并进现有场景缓存并通知监听器。"""
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=None,
        house_id=12345,
    )
    coordinator.scenes = [{"id": 4001, "name": "回家"}]
    listener = MagicMock()
    remove_listener = coordinator.async_add_listener(listener)

    events = await coordinator.async_handle_lan_payload(
        {
            "id": 13814,
            "method": "gateway_post.prop",
            "nodes": [
                {"id": 1001, "nt": 2, "params": {"p": True}},
            ],
            "scenes": [
                {"id": 4001, "n": "回家", "params": {"state": "active"}},
                {"id": 4002, "n": "离家", "params": {"state": "inactive"}},
            ],
        }
    )

    assert events == []
    assert coordinator.scenes == [
        {"id": 4001, "name": "回家", "state": "active", "params": {"state": "active"}},
        {"id": 4002, "name": "离家", "state": "inactive", "params": {"state": "inactive"}},
    ]
    listener.assert_called_once()
    remove_listener()
    await coordinator.async_shutdown()
