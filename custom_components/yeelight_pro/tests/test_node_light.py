"""Topology node light entity tests."""

from __future__ import annotations

import pytest

from custom_components.yeelight_pro.identity import entry_identity_scope, scoped_entity_unique_id
from custom_components.yeelight_pro.node_light import YeelightProNodeLight


@pytest.mark.parametrize(
    ("node_kind", "collection", "node_id"),
    [
        ("room", "rooms", "room_1"),
        ("area", "areas", "area_1"),
        ("house", "houses", "house_1"),
    ],
)
def test_node_light_reads_cached_topology_state(
    mock_coordinator,
    node_kind: str,
    collection: str,
    node_id: str,
) -> None:
    """节点 light 应从对应拓扑缓存读取名称、状态和属性."""
    setattr(
        mock_coordinator,
        collection,
        [
            {
                "id": node_id,
                "name": "客厅",
                "online": True,
                "params": {"p": True, "l": 80, "ct": 4000},
            }
        ],
    )
    entity = YeelightProNodeLight(mock_coordinator, node_kind, node_id)

    scope = entry_identity_scope(mock_coordinator.entry_data, mock_coordinator.house_id)
    assert entity.unique_id == scoped_entity_unique_id(scope, node_kind, node_id, "light")
    assert entity.name == "客厅"
    assert entity.available is True
    assert entity.is_on is True
    assert entity.brightness == 204
    assert entity.color_temp_kelvin == 4000
    assert entity.device_info["model"] == "Yeelight Pro 家庭"


def test_node_light_parses_string_power_and_online_values(mock_coordinator) -> None:
    """节点 light 应按协议布尔字符串解析在线和开关状态。"""
    mock_coordinator.rooms = [
        {"id": "room_1", "name": "客厅", "online": "false", "params": {"p": "false"}}
    ]
    entity = YeelightProNodeLight(mock_coordinator, "room", "room_1")

    assert entity.available is False
    assert entity.is_on is False


@pytest.mark.asyncio
async def test_node_light_turn_on_maps_ha_brightness_to_iot_percent(
    mock_coordinator,
) -> None:
    """节点 light 开灯时应把 HA 亮度转换为 Yeelight l 百分比."""
    mock_coordinator.rooms = [
        {
            "id": "room_1",
            "name": "客厅",
            "online": True,
            "params": {"p": False, "l": 50, "ct": 4000},
        }
    ]
    entity = YeelightProNodeLight(mock_coordinator, "room", "room_1")

    await entity.async_turn_on(brightness=128, color_temp_kelvin=4100)

    mock_coordinator.async_control_node.assert_awaited_once_with(
        "room",
        "room_1",
        {"p": True, "l": 50, "ct": 4100},
    )


@pytest.mark.asyncio
async def test_node_light_turn_off_controls_power(mock_coordinator) -> None:
    """节点 light 关灯时只下发 p=false."""
    mock_coordinator.areas = [
        {"id": "area_1", "name": "一楼", "online": True, "params": {"p": True}}
    ]
    entity = YeelightProNodeLight(mock_coordinator, "area", "area_1")

    await entity.async_turn_off()

    mock_coordinator.async_control_node.assert_awaited_once_with(
        "area",
        "area_1",
        {"p": False},
    )


def test_node_light_unavailable_when_node_missing(mock_coordinator) -> None:
    """节点缓存缺失时实体应不可用，避免误导控制状态."""
    entity = YeelightProNodeLight(mock_coordinator, "house", "house_1")

    assert entity.available is False
    assert entity.name is None
    assert entity.is_on is False
