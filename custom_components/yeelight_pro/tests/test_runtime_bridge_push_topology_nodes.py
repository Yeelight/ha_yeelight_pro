"""Runtime bridge push node-alias routing tests."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.core.coordinator import YeelightProCoordinator
from custom_components.yeelight_pro.node_light import YeelightProNodeLight


@pytest.mark.asyncio
async def test_push_update_resolves_loaded_group_id_alias(
    hass: HomeAssistant,
) -> None:
    """若私有推送 id 是行 ID、groupId 才是灯组 ID，应即时更新灯组状态。"""
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=MagicMock(),
        house_id=12345,
    )
    coordinator.groups = [
        {
            "id": 228231,
            "name": "Alias Group",
            "category": "group",
            "type": "light",
            "params": {"p": True},
        }
    ]
    coordinator.devices = {}
    coordinator.data = {}
    updates = 0

    def _listener() -> None:
        nonlocal updates
        updates += 1

    remove_listener = coordinator.async_add_listener(
        _listener,
        ("group", "228231"),
    )

    await coordinator.async_handle_push_payload(
        {
            "type": "prop",
            "nodes": [
                {
                    "id": 999999,
                    "groupId": "228231",
                    "nt": 4,
                    "params": {"p": False},
                }
            ],
        }
    )

    try:
        assert coordinator.groups[0]["params"]["p"] is False
        assert updates == 1
        assert coordinator.last_push_property_summary.as_dict() == {
            "input_updates": 1,
            "empty_param_updates": 0,
            "applied_device_updates": 0,
            "unknown_device_updates": 0,
            "group_updates": 1,
            "topology_node_updates": 0,
            "routed_updates": 1,
            "changed": True,
            "device_import_filter_enabled": False,
            "applied_node_samples": [
                {
                    "node_id_hash": "a3a5e11b6c78b858",
                    "node_type": 4,
                    "param_keys": ["p"],
                    "matched_collections": ["groups"],
                }
            ],
            "unknown_node_samples": [],
        }
    finally:
        remove_listener()

@pytest.mark.asyncio
async def test_push_update_prefers_node_type_alias_over_colliding_id(
    hass: HomeAssistant,
) -> None:
    """推送内部行 id 撞到拓扑节点时，应按 nodeType 选择真实目标别名。"""
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=MagicMock(),
        house_id=12345,
    )
    coordinator.rooms = [{"id": 999999, "name": "Collision Room", "params": {"p": True}}]
    coordinator.groups = [
        {
            "id": 228232,
            "name": "Target Group",
            "category": "group",
            "type": "light",
            "params": {"p": True},
        }
    ]
    coordinator.devices = {}
    coordinator.data = {}

    await coordinator.async_handle_push_payload(
        {
            "type": "prop",
            "nodes": [
                {
                    "id": 999999,
                    "groupId": "228232",
                    "nt": 4,
                    "params": {"p": False},
                }
            ],
        }
    )

    assert coordinator.rooms[0]["params"] == {"p": True}
    assert coordinator.groups[0]["params"] == {"p": False}
    assert coordinator.last_push_property_summary.as_dict() == {
        "input_updates": 1,
        "empty_param_updates": 0,
        "applied_device_updates": 0,
        "unknown_device_updates": 0,
        "group_updates": 1,
        "topology_node_updates": 0,
        "routed_updates": 1,
        "changed": True,
        "device_import_filter_enabled": False,
        "applied_node_samples": [
            {
                "node_id_hash": "628ba186a44ea4f1",
                "node_type": 4,
                "param_keys": ["p"],
                "matched_collections": ["groups"],
            }
        ],
        "unknown_node_samples": [],
    }

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

    remove_listener = coordinator.async_add_listener(
        _listener,
        ("room", "201"),
    )

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
            "empty_param_updates": 0,
            "applied_device_updates": 0,
            "unknown_device_updates": 0,
            "group_updates": 0,
            "topology_node_updates": 3,
            "routed_updates": 3,
            "changed": True,
            "device_import_filter_enabled": False,
            "applied_node_samples": [
                {
                    "node_id_hash": "8d31226932892e43",
                    "node_type": 1,
                    "param_keys": ["l", "p"],
                    "matched_collections": ["rooms"],
                },
                {
                    "node_id_hash": "866761928584c395",
                    "node_type": 3,
                    "param_keys": ["p"],
                    "matched_collections": ["areas"],
                },
                {
                    "node_id_hash": "af3ef8742514e404",
                    "node_type": 5,
                    "param_keys": ["o", "p"],
                    "matched_collections": ["houses"],
                },
            ],
            "unknown_node_samples": [],
        }
        assert coordinator.last_push_event_count == 0
    finally:
        remove_listener()

@pytest.mark.asyncio
async def test_push_unknown_update_summary_classifies_missing_node_type(
    hass: HomeAssistant,
) -> None:
    """唯一命中已加载灯组的无 nodeType 推送应更新，其余未知节点保持脱敏诊断。"""
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

    assert summary["unknown_device_updates"] == 1
    assert summary["group_updates"] == 1
    assert summary["device_import_filter_enabled"] is True
    assert summary["applied_node_samples"] == [
        {
            "node_id_hash": "24816ecaefa2baf2",
            "node_type": None,
            "param_keys": ["p"],
            "matched_collections": ["groups"],
        },
    ]
    assert summary["unknown_node_samples"] == [
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
async def test_push_topology_update_routes_by_matching_relation_id(
    hass: HomeAssistant,
) -> None:
    """node_type 明确为房间时，roomId 可作为拓扑节点 ID 候选。"""
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=MagicMock(),
        house_id=12345,
    )
    coordinator.devices = {}
    coordinator.data = {}
    coordinator.rooms = [{"id": 228231, "name": "Room", "params": {"p": True}}]

    await coordinator.async_handle_push_payload(
        {
            "type": "prop",
            "nodes": [
                {
                    "id": 998,
                    "roomId": 228231,
                    "nt": 1,
                    "params": {"p": False},
                }
            ],
        }
    )

    summary = coordinator.last_push_property_summary.as_dict()

    assert summary["unknown_device_updates"] == 0
    assert summary["topology_node_updates"] == 1
    assert summary["routed_updates"] == 1
    assert coordinator.rooms[0]["params"]["p"] is False
