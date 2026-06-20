"""Runtime bridge push node-alias routing tests."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.core.coordinator import YeelightProCoordinator


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

    remove_listener = coordinator.async_add_listener(
        _listener,
        ("device", "228230"),
    )

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
            "empty_param_updates": 0,
            "applied_device_updates": 1,
            "unknown_device_updates": 0,
            "group_updates": 0,
            "topology_node_updates": 0,
            "routed_updates": 1,
            "changed": True,
            "device_import_filter_enabled": False,
            "applied_node_samples": [
                {
                    "node_id_hash": "d7d20a1a6a984ed0",
                    "node_type": 2,
                    "param_keys": ["2-mv"],
                    "matched_collections": ["devices", "data"],
                }
            ],
            "unknown_node_samples": [],
            "affected_context_count": 1,
            "affected_context_samples": [
                {
                    "kind": "device",
                    "node_id_hash": "d7d20a1a6a984ed0",
                }
            ],
        }
        assert 999999 not in coordinator._runtime_state.overrides
    finally:
        remove_listener()

@pytest.mark.asyncio
async def test_push_update_uses_device_id_alias_when_row_id_is_not_loaded(
    hass: HomeAssistant,
) -> None:
    """推送行 id 未加载但 deviceId 已在拓扑中时，应命中当前设备。"""
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=MagicMock(),
        house_id=12345,
    )
    coordinator.devices = {
        228233: {
            "id": 228233,
            "deviceId": 228233,
            "name": "Four Key Switch",
            "category": "relay_switch",
            "type": "switch",
            "online": True,
            "params": {"1-p": True, "2-p": True},
        }
    }
    coordinator.data = coordinator.devices
    coordinator.options = {
        "device_import_filter": {
            "enabled": True,
            "mode": "include",
            "include": {"category": ["light"]},
        }
    }

    await coordinator.async_handle_push_payload(
        {
            "type": "prop",
            "nodes": [
                {
                    "id": 999998,
                    "deviceId": "228233",
                    "nt": 2,
                    "params": {"1-p": False},
                }
            ],
        }
    )

    refreshed = coordinator.get_device(228233)
    assert refreshed is not None
    assert refreshed["params"]["1-p"] is False
    assert 999998 not in coordinator._runtime_state.overrides
    summary = coordinator.last_push_property_summary.as_dict()
    assert summary["applied_device_updates"] == 1
    assert summary["unknown_device_updates"] == 0
    assert summary["routed_updates"] == 1
    assert summary["device_import_filter_enabled"] is True
    assert summary["applied_node_samples"] == [
        {
            "node_id_hash": "ae7ac0cc1cbc2b02",
            "node_type": 2,
            "param_keys": ["1-p"],
            "matched_collections": ["devices", "data"],
        }
    ]
    assert summary["unknown_node_samples"] == []

@pytest.mark.asyncio
async def test_push_update_reports_unknown_alias_without_filtering_reason(
    hass: HomeAssistant,
) -> None:
    """所有候选 ID 都不在当前拓扑时，应诊断为未知节点而非导入过滤。"""
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=MagicMock(),
        house_id=12345,
    )
    coordinator.devices = {}
    coordinator.data = {}
    coordinator.options = {
        "device_import_filter": {
            "enabled": True,
            "mode": "include",
            "include": {"category": ["light"]},
        }
    }

    await coordinator.async_handle_push_payload(
        {
            "type": "prop",
            "nodes": [
                {
                    "id": 999998,
                    "deviceId": "228233",
                    "nt": 2,
                    "params": {"1-p": False},
                }
            ],
        }
    )

    summary = coordinator.last_push_property_summary.as_dict()
    assert summary["unknown_device_updates"] == 1
    assert summary["device_import_filter_enabled"] is True
    assert summary["unknown_node_samples"] == [
        {
            "node_id_hash": "3cb3b39217202d10",
            "node_type": 2,
            "param_keys": ["1-p"],
            "matched_collections": [],
            "reason": "not_loaded",
            "device_import_filter_enabled": True,
            "node_id_candidates": [
                {
                    "field": "id",
                    "node_id_hash": "3cb3b39217202d10",
                    "matched_collections": [],
                },
                {
                    "field": "deviceId",
                    "node_id_hash": "ae7ac0cc1cbc2b02",
                    "matched_collections": [],
                },
            ],
        }
    ]

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
    assert summary["applied_node_samples"] == []
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

@pytest.mark.asyncio
async def test_push_device_update_does_not_route_by_room_relation_id(
    hass: HomeAssistant,
) -> None:
    """设备推送中的 roomId 是归属关系，不能替代缺失的设备节点 ID。"""
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
                    "nt": 2,
                    "params": {"p": False},
                }
            ],
        }
    )

    summary = coordinator.last_push_property_summary.as_dict()

    assert summary["unknown_device_updates"] == 1
    assert summary["topology_node_updates"] == 0
    assert summary["routed_updates"] == 0
    assert coordinator.rooms == [{"id": 228231, "name": "Room", "params": {"p": True}}]
