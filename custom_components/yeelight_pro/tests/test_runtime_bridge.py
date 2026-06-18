"""Runtime bridge tests for received push and LAN payloads."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.const import DOMAIN
from custom_components.yeelight_pro.core.coordinator import YeelightProCoordinator
from custom_components.yeelight_pro.core.device_payload import DevicePayloadBuilder
from custom_components.yeelight_pro.core.runtime_bridge import (
    RuntimeEventDeduper,
    runtime_event_dedupe_key,
)
from custom_components.yeelight_pro.light import YeelightProLight
from custom_components.yeelight_pro.node_light import YeelightProNodeLight
from custom_components.yeelight_pro.projector.sensor import project_sensors
from custom_components.yeelight_pro.projector.switch import project_switches


@pytest.mark.asyncio
async def test_coordinator_applies_lan_property_updates_to_runtime_state(
    hass: HomeAssistant,
) -> None:
    """LAN 属性推送应复用运行时状态合并路径并刷新监听器。"""
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=MagicMock(),
        house_id=12345,
    )
    coordinator.devices = {
        228216: {
            "id": 228216,
            "device_id": 228216,
            "name": "LAN Lamp",
            "category": "light",
            "type": "light",
            "online": True,
            "pid": 100,
            "product_schema": _lamp_schema(),
            "params": {"p": True, "l": 25},
        }
    }
    DevicePayloadBuilder().attach_canonical_models_if_available(
        coordinator.devices[228216]
    )
    coordinator.data = coordinator.devices
    light = YeelightProLight(coordinator, 228216)
    updates = 0

    def _listener() -> None:
        nonlocal updates
        updates += 1

    remove_listener = coordinator.async_add_listener(_listener)

    events = await coordinator.async_handle_lan_payload(
        {
            "method": "gateway_post.prop",
            "nodes": [
                {
                    "id": 228216,
                    "nt": 2,
                    "o": False,
                    "params": {"p": False, "l": 80},
                }
            ],
        }
    )

    try:
        assert events == []
        assert coordinator._runtime_state.overrides[228216]["params"] == {
            "p": False,
            "l": 80,
            "o": False,
        }
        refreshed = coordinator.get_device(228216)
        assert refreshed is not None
        assert refreshed["online"] is False
        assert refreshed["params"]["p"] is False
        assert refreshed["params"]["l"] == 80
        assert refreshed["ha_device_instance"]["online"] is False
        assert refreshed["ha_device_instance"]["components"][0]["available"] is False
        assert light.available is False
        assert light.is_on is False
        assert light.brightness == 203
        assert updates == 1
    finally:
        remove_listener()


@pytest.mark.asyncio
async def test_coordinator_routes_indexed_lan_updates_to_matching_component(
    hass: HomeAssistant,
) -> None:
    """LAN indexed prop 只应更新对应组件，不能串到其他开关通道。"""
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=MagicMock(),
        house_id=12345,
    )
    coordinator.devices = {
        228217: {
            "id": 228217,
            "device_id": 228217,
            "name": "LAN Dual Relay",
            "category": "relay_switch",
            "type": "switch",
            "online": True,
            "params": {"1-p": True, "2-p": True},
            "ha_device_instance": {
                "device_id": "228217",
                "name": "LAN Dual Relay",
                "online": True,
                "components": [
                    {
                        "component_id": "relay_switch_1",
                        "category": "relay_switch",
                        "available": True,
                        "state": {"p": True},
                    },
                    {
                        "component_id": "relay_switch_2",
                        "category": "relay_switch",
                        "available": True,
                        "state": {"p": True},
                    },
                ],
            },
        }
    }
    coordinator.data = coordinator.devices

    await coordinator.async_handle_lan_payload(
        {
            "method": "gateway_post.prop",
            "nodes": [{"id": 228217, "nt": 2, "params": {"2-p": False}}],
        }
    )

    refreshed = coordinator.get_device(228217)
    assert refreshed is not None
    assert refreshed["ha_device_instance"]["components"][0]["state"] == {"p": True}
    assert refreshed["ha_device_instance"]["components"][1]["state"] == {"p": False}
    projections = project_switches(refreshed, domain=DOMAIN)
    values = {projection.component_id: projection.is_on for projection in projections}
    assert values == {"relay_switch_1": True, "relay_switch_2": False}


@pytest.mark.asyncio
async def test_push_update_resolves_loaded_node_id_alias(
    hass: HomeAssistant,
) -> None:
    """若私有推送 id 是行 ID、resId 才是设备 ID，应路由到已加载设备。"""
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=MagicMock(),
        house_id=12345,
    )
    coordinator.devices = {
        228230: {
            "id": 228230,
            "device_id": 228230,
            "name": "Motion Panel",
            "category": "other",
            "type": "sensor",
            "online": True,
            "params": {"2-mv": 0},
        }
    }
    coordinator.data = coordinator.devices
    updates = 0

    def _listener() -> None:
        nonlocal updates
        updates += 1

    remove_listener = coordinator.async_add_listener(_listener)

    await coordinator.async_handle_push_payload(
        {
            "method": "gateway_post.prop",
            "nodes": [
                {
                    "id": 999999,
                    "resId": "228230",
                    "nt": 2,
                    "params": {"2-mv": 1},
                }
            ],
        }
    )

    try:
        refreshed = coordinator.get_device(228230)
        assert refreshed is not None
        assert refreshed["params"]["2-mv"] == 1
        assert updates == 1
        assert coordinator.last_push_property_summary.as_dict() == {
            "input_updates": 1,
            "applied_device_updates": 1,
            "unknown_device_updates": 0,
            "group_updates": 0,
            "topology_node_updates": 0,
            "changed": True,
            "device_import_filter_enabled": False,
            "unknown_node_samples": [],
        }
        assert 999999 not in coordinator._runtime_state.overrides
    finally:
        remove_listener()


@pytest.mark.asyncio
async def test_lan_runtime_update_rebuilds_scaled_canonical_state(
    hass: HomeAssistant,
) -> None:
    """LAN 更新后 canonical state 仍应按 product schema 保持实际值。"""
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=MagicMock(),
        house_id=12345,
    )
    coordinator.devices = {
        228218: {
            "id": 228218,
            "device_id": 228218,
            "name": "LAN Power Meter",
            "category": "other",
            "type": "sensor",
            "online": True,
            "pid": 1012,
            "product_schema": _power_meter_schema(),
            "params": {"curp": 10, "iec": 1000},
        }
    }
    DevicePayloadBuilder().attach_canonical_models_if_available(
        coordinator.devices[228218]
    )
    coordinator.data = coordinator.devices

    await coordinator.async_handle_lan_payload(
        {
            "method": "gateway_post.prop",
            "nodes": [
                {
                    "id": 228218,
                    "nt": 2,
                    "params": {"curp": "12", "iec": 2500},
                }
            ],
        }
    )

    refreshed = coordinator.get_device(228218)
    assert refreshed is not None
    assert refreshed["params"] == {"curp": "12", "iec": 2500}
    assert refreshed["ha_device_instance"]["components"][0]["state"] == {
        "curp": 120,
        "iec": 25.0,
    }
    by_component = {
        projection.component_id: projection
        for projection in project_sensors(refreshed, domain=DOMAIN)
    }
    assert by_component["current_power"].native_value == 120
    assert by_component["energy_consumption"].native_value == 25.0


@pytest.mark.asyncio
async def test_lan_runtime_update_scales_temperature_humidity_raw_value(
    hass: HomeAssistant,
) -> None:
    """LAN type=136 后续属性推送也必须按协议把 t/100。"""
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=MagicMock(),
        house_id=12345,
    )
    coordinator.devices = {
        228219: {
            "id": 228219,
            "device_id": 228219,
            "name": "LAN Temp Humidity",
            "category": "other",
            "type": "other",
            "online": True,
            "lan_type": 136,
            "params": {"t": 0.0, "h": 0},
            "ha_device_instance": {
                "device_id": "228219",
                "name": "LAN Temp Humidity",
                "online": True,
                "components": [
                    {
                        "component_id": "temp_humidity",
                        "category": "temperature humidity sensor",
                        "available": True,
                        "state": {"t": 0.0, "h": 0},
                    }
                ],
            },
        }
    }
    coordinator.data = coordinator.devices

    await coordinator.async_handle_lan_payload(
        {
            "method": "gateway_post.prop",
            "nodes": [{"id": 228219, "nt": 2, "params": {"t": 2534, "h": 58}}],
        }
    )

    refreshed = coordinator.get_device(228219)
    assert refreshed is not None
    assert refreshed["params"] == {"t": 25.34, "h": 58}
    assert refreshed["ha_device_instance"]["components"][0]["state"] == {
        "t": 25.34,
        "h": 58,
    }
    by_component = {
        projection.component_id: projection
        for projection in project_sensors(refreshed, domain=DOMAIN)
    }
    assert by_component["temperature"].native_value == 25.34


@pytest.mark.asyncio
async def test_push_updates_room_area_house_node_light_state(
    hass: HomeAssistant,
) -> None:
    """WebSocket nodeType=1/3/5 属性推送应即时刷新拓扑总控实体。"""
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=MagicMock(),
        house_id=12345,
    )
    coordinator.rooms = [{"id": 201, "name": "客厅", "params": {"p": True}}]
    coordinator.areas = [{"id": 301, "name": "一楼", "params": {"p": True}}]
    coordinator.houses = [{"id": 5001, "name": "我的家", "params": {"p": True}}]
    room_light = YeelightProNodeLight(coordinator, "room", "201")
    area_light = YeelightProNodeLight(coordinator, "area", "301")
    house_light = YeelightProNodeLight(coordinator, "house", "5001")
    updates = 0

    def _listener() -> None:
        nonlocal updates
        updates += 1

    remove_listener = coordinator.async_add_listener(_listener)

    events = await coordinator.async_handle_push_payload(
        {
            "type": "prop",
            "nodes": [
                {"id": 201, "nt": 1, "params": {"p": False, "l": 25}},
                {"id": 301, "nt": 3, "params": {"p": False}},
                {"id": 5001, "nt": 5, "params": {"p": False, "o": True}},
            ],
        }
    )

    try:
        assert events == []
        assert coordinator.rooms[0]["params"] == {"p": False, "l": 25}
        assert coordinator.areas[0]["params"] == {"p": False}
        assert coordinator.houses[0]["params"] == {"p": False, "o": True}
        assert room_light.is_on is False
        assert area_light.is_on is False
        assert house_light.is_on is False
        assert updates == 1
        assert coordinator.last_push_property_summary.as_dict() == {
            "input_updates": 3,
            "applied_device_updates": 0,
            "unknown_device_updates": 0,
            "group_updates": 0,
            "topology_node_updates": 3,
            "changed": True,
            "device_import_filter_enabled": False,
            "unknown_node_samples": [],
        }
        assert coordinator.last_push_event_count == 0
    finally:
        remove_listener()


@pytest.mark.asyncio
async def test_push_unknown_update_summary_classifies_missing_node_type(
    hass: HomeAssistant,
) -> None:
    """未知推送诊断应脱敏说明是缺 nodeType，还是完全未加载节点。"""
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=MagicMock(),
        house_id=12345,
        options={
            "device_import_filter": {
                "enabled": True,
                "include": {"devices": ["filtered-secret"]},
                "exclude": {},
                "mode": "or",
            }
        },
    )
    coordinator.groups = [{"id": 401, "name": "灯组", "params": {"p": True}}]
    coordinator.data = {}

    await coordinator.async_handle_push_payload(
        {
            "type": "prop",
            "nodes": [
                {"id": 401, "params": {"p": False}},
                {"id": 999, "params": {"1-p": True, "secret": "value"}},
            ],
        }
    )

    summary = coordinator.last_push_property_summary.as_dict()

    assert summary["unknown_device_updates"] == 2
    assert summary["device_import_filter_enabled"] is True
    assert summary["unknown_node_samples"] == [
        {
            "node_id_hash": "24816ecaefa2baf2",
            "node_type": None,
            "param_keys": ["p"],
            "matched_collections": ["groups"],
            "reason": "missing_group_node_type",
            "device_import_filter_enabled": True,
        },
        {
            "node_id_hash": "4ffe0cb3de9f85b4",
            "node_type": None,
            "param_keys": ["1-p", "secret"],
            "matched_collections": [],
            "reason": "not_loaded",
            "device_import_filter_enabled": True,
        },
    ]
    assert "401" not in str(summary)
    assert "999" not in str(summary)
    assert "value" not in str(summary)


@pytest.mark.asyncio
async def test_push_unknown_update_summary_reports_id_alias_candidates(
    hass: HomeAssistant,
) -> None:
    """未知节点诊断应脱敏列出多 ID 候选及其集合命中情况。"""
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=MagicMock(),
        house_id=12345,
    )
    coordinator.data = {}

    await coordinator.async_handle_push_payload(
        {
            "method": "gateway_post.prop",
            "nodes": [
                {
                    "id": 998,
                    "resId": "999",
                    "nt": 2,
                    "params": {"4-mv": 1},
                }
            ],
        }
    )

    summary = coordinator.last_push_property_summary.as_dict()

    assert summary["unknown_device_updates"] == 1
    assert summary["unknown_node_samples"] == [
        {
            "node_id_hash": "ada57d8e7ef57315",
            "node_type": 2,
            "param_keys": ["4-mv"],
            "matched_collections": [],
            "reason": "not_loaded",
            "device_import_filter_enabled": False,
            "node_id_candidates": [
                {
                    "field": "id",
                    "node_id_hash": "ada57d8e7ef57315",
                    "matched_collections": [],
                },
                {
                    "field": "resId",
                    "node_id_hash": "4ffe0cb3de9f85b4",
                    "matched_collections": [],
                },
            ],
        }
    ]
    assert "998" not in str(summary)
    assert "999" not in str(summary)


def test_runtime_event_dedupe_key_is_bounded_and_identifier_safe() -> None:
    """事件去重键不能包含 msgId、设备 ID 或原始事件值。"""
    payload = {
        "source_device_id": "device-secret",
        "component_id": "scene_panel",
        "event_type": "click",
        "event_attributes": {
            "message_id": "message-secret",
            "raw_event": "raw-secret",
        },
    }

    key = runtime_event_dedupe_key(payload)
    deduper = RuntimeEventDeduper(max_keys=1)

    assert isinstance(key, str)
    assert key
    assert "message-secret" not in key
    assert "device-secret" not in key
    assert "raw-secret" not in key
    assert deduper.is_duplicate(payload) is False
    assert deduper.is_duplicate(payload) is True


def _lamp_schema() -> dict:
    """构造运行时 bridge 测试用灯具 schema。"""
    return {
        "pid": 100,
        "name": "LAN Lamp Product",
        "category": "light",
        "components": [
            {
                "cid": 4,
                "name": "brightness light",
                "type": 0,
                "category": "light",
                "index": 1,
                "properties": [
                    {"propId": "p", "operators": ["set"]},
                    {"propId": "l", "operators": ["set"]},
                ],
            }
        ],
    }


def _power_meter_schema() -> dict:
    """构造运行时 bridge 测试用缩放遥测 schema。"""
    return {
        "pid": 1012,
        "name": "LAN Power Meter Product",
        "category": "other",
        "components": [
            {
                "cid": 63,
                "name": "power meter",
                "type": 0,
                "category": "power meter",
                "properties": [
                    {
                        "propId": "curp",
                        "format": "int",
                        "access": 5,
                        "zoom": -1,
                        "scale": 10,
                    },
                    {
                        "propId": "iec",
                        "format": "int",
                        "access": 5,
                        "zoom": 1,
                        "scale": 100,
                    },
                ],
            }
        ],
    }
