"""LAN topology normalization tests based on Yeelight IoT documents."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.yeelight_pro.const import (
    CONF_CONNECTION_MODE,
    CONF_LAN_GATEWAY_IP,
    CONF_LAN_GATEWAY_PORT,
    CONNECTION_MODE_LAN,
    DOMAIN,
)
from custom_components.yeelight_pro.core.coordinator import YeelightProCoordinator
from custom_components.yeelight_pro.core.device_payload import DevicePayloadBuilder
from custom_components.yeelight_pro.core.lan_topology_payload import (
    build_lan_topology_payloads,
)
from custom_components.yeelight_pro.entity_candidates import iter_device_entity_candidates
from custom_components.yeelight_pro.ha_device_registry import async_sync_gateway_devices
from custom_components.yeelight_pro.identity import (
    entry_identity_scope,
    scoped_device_identifier,
    scoped_entity_unique_id,
)
from custom_components.yeelight_pro.projector.sensor import project_sensors
from custom_components.yeelight_pro.projector.event import project_events
from custom_components.yeelight_pro.projector.property_controls import project_select_controls


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


def test_lan_temperature_humidity_sensor_scales_documented_raw_temperature() -> None:
    """LAN type=136 的 t 是摄氏度放大 100 倍，入站时应转成真实摄氏值。"""
    device = _build([
        {
            "id": 1006,
            "nt": 2,
            "type": 136,
            "n": "主卧环境",
            "params": {"t": 2534, "h": 58},
        },
    ])[1006]

    sensors = project_sensors(device, domain=DOMAIN)
    by_component = {item.component_id: item for item in sensors}

    assert device["params"]["t"] == 25.34
    assert device["ha_device_instance"]["components"][0]["state"]["t"] == 25.34
    assert by_component["temperature"].native_value == 25.34
    assert by_component["humidity"].native_value == 58


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


def test_lan_scene_panel_projects_all_documented_panel_events() -> None:
    """LAN type=128 应包含 click/hold/release 三类面板事件。"""
    device = _build([
        {"id": 1007, "nt": 2, "type": 128, "n": "玄关情景面板"},
    ])[1007]

    events = project_events(device, domain=DOMAIN)

    assert device["events"] == [
        {"name": "click"},
        {"name": "hold"},
        {"name": "release_after_hold"},
    ]
    assert len(events) == 1
    assert events[0].event_types == ["click", "hold", "release_after_hold"]


def test_lan_bath_heater_projects_documented_auxiliary_controls() -> None:
    """LAN type=2049 浴霸应保留换气/吹风/加热档位和延时关闭控件。"""
    device = _build([
        {"id": 1008, "nt": 2, "type": 2049, "n": "主卫浴霸"},
    ])[1008]
    candidates = {
        (item.platform, item.component_id, item.entity_category)
        for item in iter_device_entity_candidates(device)
    }

    assert device["device_info"]["model"] == "浴霸加热器"
    assert device["params"] == {
        "p": False,
        "bhm": 1,
        "do": 1,
        "ve": 0,
        "fa": 0,
        "he": 0,
        "tgt": 26,
        "t": 26,
    }
    assert ("climate", "temp_control", None) in candidates
    assert ("select", "temp_control_bhm_select", None) in candidates
    assert ("number", "temp_control_do_number", None) in candidates
    assert ("select", "temp_control_ve_select", None) in candidates
    assert ("select", "temp_control_fa_select", None) in candidates
    assert ("select", "temp_control_he_select", None) in candidates
    bath_mode = next(
        item for item in project_select_controls(device, domain=DOMAIN) if item.prop_id == "bhm"
    )
    assert [item.value for item in bath_mode.options] == ["1", "2", "3", "4"]


def test_lan_tof_sensor_projects_only_documented_handwave_event() -> None:
    """LAN type=2052 是 TOF 传感器，只应暴露 handwave 事件。"""
    device = _build([
        {"id": 1009, "nt": 2, "type": 2052, "n": "玄关 TOF"},
    ])[1009]

    events = project_events(device, domain=DOMAIN)

    assert device["iot_category"] == "other"
    assert device["device_info"]["model"] == "TOF传感器"
    assert device["events"] == [{"name": "handwave"}]
    assert len(events) == 1
    assert events[0].event_types == ["handwave"]


@pytest.mark.asyncio
async def test_lan_topology_syncs_source_devices_and_relinks_entities(
    hass: HomeAssistant,
) -> None:
    """LAN-only 拓扑设备也必须进入 HA device registry 并回链既有实体。"""
    entry = MockConfigEntry(domain=DOMAIN, entry_id="entry-lan")
    entry.add_to_hass(hass)
    entity_registry = er.async_get(hass)
    lan_entry_data = {
        CONF_CONNECTION_MODE: CONNECTION_MODE_LAN,
        CONF_LAN_GATEWAY_IP: "127.0.0.1",
        CONF_LAN_GATEWAY_PORT: 65443,
    }
    lan_scope = entry_identity_scope(lan_entry_data, 0)
    entity_entry = entity_registry.async_get_or_create(
        "light",
        DOMAIN,
        scoped_entity_unique_id(lan_scope, "device", 1001, "light"),
        config_entry=entry,
    )
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=None,
        house_id=0,
        entry_data=lan_entry_data,
    )

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

    device = dr.async_get(hass).async_get_device(
        identifiers={(DOMAIN, scoped_device_identifier(lan_scope, 1001))}
    )
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
