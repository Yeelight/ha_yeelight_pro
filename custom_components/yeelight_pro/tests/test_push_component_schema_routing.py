"""Schema-backed component push routing tests."""

from __future__ import annotations

from unittest.mock import MagicMock
from types import MethodType

import pytest

from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.core.coordinator import YeelightProCoordinator
from custom_components.yeelight_pro.core.device_payload import DevicePayloadBuilder
from custom_components.yeelight_pro.switch import YeelightProSwitch

@pytest.mark.asyncio
async def test_coordinator_applies_schema_backed_multi_switch_push_to_entity(
    hass: HomeAssistant,
) -> None:
    """带产品 schema 的四键开关收到业务 push 后应立即刷新对应 HA 实体."""
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=MagicMock(),
        house_id=12345,
    )
    coordinator.devices = {
        50018395: {
            "id": 50018395,
            "device_id": 50018395,
            "name": "四键开关",
            "category": "relay_switch",
            "type": "switch",
            "online": True,
            "pid": 854041,
            "product_schema": _multi_switch_schema(),
            "params": {
                "1-p": True,
                "2-p": False,
                "3-p": True,
                "4-p": False,
                "p": True,
                "o": True,
            },
        }
    }
    DevicePayloadBuilder().attach_canonical_models_if_available(
        coordinator.devices[50018395]
    )
    coordinator.data = coordinator.devices
    second_key = YeelightProSwitch(coordinator, 50018395, component_id="switch_2")
    fourth_key = YeelightProSwitch(coordinator, 50018395, component_id="switch_4")
    updates = 0

    def _listener() -> None:
        nonlocal updates
        updates += 1

    remove_listener = coordinator.async_add_listener(
        _listener,
        ("device", "50018395"),
    )

    events = await coordinator.async_handle_push_payload(
        {
            "type": "prop",
            "nodes": [
                {
                    "id": 50018395,
                    "nt": 2,
                    "params": {
                        "1-p": True,
                        "2-p": True,
                        "3-p": True,
                        "4-p": True,
                        "p": True,
                        "o": True,
                    },
                }
            ],
        }
    )

    try:
        assert events == []
        assert updates == 1
        assert second_key.is_on is True
        assert fourth_key.is_on is True
        refreshed = coordinator.get_device(50018395)
        assert refreshed is not None
        assert refreshed["params"]["2-p"] is True
        assert refreshed["params"]["4-p"] is True
        components = {
            item["component_id"]: item["state"]
            for item in refreshed["ha_device_instance"]["components"]
        }
        assert components["relay_switch_2"]["p"] is True
        assert components["relay_switch_4"]["p"] is True
        assert coordinator.last_push_property_summary.affected_contexts == (
            ("device", "50018395"),
        )
    finally:
        remove_listener()


@pytest.mark.asyncio
async def test_schema_backed_switch_push_notifies_entity_callback_context_only(
    hass: HomeAssistant,
) -> None:
    """真实实体回调应自动定向到目标设备，避免全量刷新拖慢前端."""
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=MagicMock(),
        house_id=12345,
    )
    coordinator.devices = {
        50018395: {
            "id": 50018395,
            "device_id": 50018395,
            "name": "四键开关",
            "category": "relay_switch",
            "type": "switch",
            "online": True,
            "pid": 854041,
            "product_schema": _multi_switch_schema(),
            "params": {
                "1-p": False,
                "2-p": False,
                "3-p": False,
                "4-p": False,
                "p": True,
                "o": True,
            },
        },
        50018401: {
            "id": 50018401,
            "device_id": 50018401,
            "name": "Other switch",
            "category": "relay_switch",
            "type": "switch",
            "online": True,
            "params": {"1-p": False},
        },
    }
    DevicePayloadBuilder().attach_canonical_models_if_available(
        coordinator.devices[50018395]
    )
    coordinator.data = coordinator.devices
    target = YeelightProSwitch(coordinator, 50018395, component_id="switch_4")
    other = YeelightProSwitch(coordinator, 50018401, component_id="switch_1")
    counts = {"target": 0, "other": 0}

    def _target_update(self) -> None:
        counts["target"] += 1

    def _other_update(self) -> None:
        counts["other"] += 1

    target._handle_coordinator_update = MethodType(_target_update, target)
    other._handle_coordinator_update = MethodType(_other_update, other)
    remove_target = coordinator.async_add_listener(target._handle_coordinator_update)
    remove_other = coordinator.async_add_listener(other._handle_coordinator_update)

    events = await coordinator.async_handle_push_payload(
        {
            "type": "prop",
            "nodes": [
                {
                    "id": 50018395,
                    "nt": 2,
                    "params": {
                        "4-p": True,
                        "o": True,
                    },
                }
            ],
        }
    )

    try:
        assert events == []
        assert counts == {"target": 1, "other": 0}
        assert coordinator.last_listener_context_count == 1
        assert coordinator.last_listener_notification_count == 1
        assert target.is_on is True
    finally:
        remove_target()
        remove_other()


@pytest.mark.asyncio
async def test_coordinator_applies_schema_backed_wireless_switch_sp_push_to_entity(
    hass: HomeAssistant,
) -> None:
    """854041 四键无线通道收到 N-sp 外部推送时，应立即刷新对应 HA 实体."""
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=MagicMock(),
        house_id=12345,
    )
    coordinator.devices = {
        50018395: {
            "id": 50018395,
            "device_id": 50018395,
            "name": "四键开关",
            "category": "relay_switch",
            "type": "switch",
            "online": True,
            "pid": 854041,
            "product_schema": _wireless_switch_schema(),
            "params": {
                "1-sp": True,
                "2-sp": True,
                "3-sp": False,
                "4-sp": False,
                "p": True,
                "o": True,
            },
        }
    }
    DevicePayloadBuilder().attach_canonical_models_if_available(
        coordinator.devices[50018395]
    )
    coordinator.data = coordinator.devices
    second_key = YeelightProSwitch(coordinator, 50018395, component_id="switch_2")
    fourth_key = YeelightProSwitch(coordinator, 50018395, component_id="switch_4")
    updates = 0

    def _listener() -> None:
        nonlocal updates
        updates += 1

    remove_listener = coordinator.async_add_listener(
        _listener,
        ("device", "50018395"),
    )

    events = await coordinator.async_handle_push_payload(
        {
            "type": "prop",
            "nodes": [
                {
                    "id": 50018395,
                    "nt": 2,
                    "params": {
                        "2-sp": False,
                        "4-sp": True,
                        "o": True,
                    },
                }
            ],
        }
    )

    try:
        assert events == []
        assert updates == 1
        assert second_key.name == "按键 2"
        assert fourth_key.name == "按键 4"
        assert second_key.is_on is False
        assert fourth_key.is_on is True
        refreshed = coordinator.get_device(50018395)
        assert refreshed is not None
        assert refreshed["params"]["2-sp"] is False
        assert refreshed["params"]["4-sp"] is True
        assert coordinator.last_push_property_summary.as_dict()["unknown_device_updates"] == 0
    finally:
        remove_listener()


@pytest.mark.asyncio
async def test_coordinator_routes_component_index_push_update_to_matching_component(
    hass: HomeAssistant,
) -> None:
    """带 index 的 plain params 推送只应更新对应继电器通道."""
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=MagicMock(),
        house_id=12345,
    )
    coordinator.devices = {
        228219: {
            "id": 228219,
            "device_id": 228219,
            "name": "Dual Relay",
            "category": "relay_switch",
            "type": "switch",
            "online": True,
            "params": {"1-p": True, "2-p": True},
        }
    }
    coordinator.data = coordinator.devices
    first_relay = YeelightProSwitch(coordinator, 228219, component_id="switch_1")
    second_relay = YeelightProSwitch(coordinator, 228219, component_id="switch_2")
    updates = 0

    def _listener() -> None:
        nonlocal updates
        updates += 1

    remove_listener = coordinator.async_add_listener(
        _listener,
        ("device", "228219"),
    )

    events = await coordinator.async_handle_push_payload(
        {
            "type": "prop",
            "nodes": [
                {
                    "id": 228219,
                    "nt": 2,
                    "index": 2,
                    "params": {"p": False},
                }
            ],
        }
    )

    try:
        assert events == []
        assert updates == 1
        assert first_relay.is_on is True
        assert second_relay.is_on is False
        refreshed = coordinator.get_device(228219)
        assert refreshed is not None
        assert refreshed["params"]["1-p"] is True
        assert refreshed["params"]["2-p"] is False
        assert "p" not in refreshed["params"]
    finally:
        remove_listener()


def _multi_switch_schema() -> dict:
    """构造四键开关 push 测试用的最小产品 schema."""
    return {
        "pid": 854041,
        "name": "四键开关",
        "category": "relay_switch",
        "components": [
            {
                "cid": 1,
                "name": "按键 1",
                "type": 0,
                "category": "relay_switch",
                "index": 1,
                "properties": [{"propId": "p", "operators": ["set"]}],
            },
            {
                "cid": 2,
                "name": "按键 2",
                "type": 0,
                "category": "relay_switch",
                "index": 2,
                "properties": [{"propId": "p", "operators": ["set"]}],
            },
            {
                "cid": 3,
                "name": "按键 3",
                "type": 0,
                "category": "relay_switch",
                "index": 3,
                "properties": [{"propId": "p", "operators": ["set"]}],
            },
            {
                "cid": 4,
                "name": "按键 4",
                "type": 0,
                "category": "relay_switch",
                "index": 4,
                "properties": [{"propId": "p", "operators": ["set"]}],
            },
        ],
    }


def _wireless_switch_schema() -> dict:
    """构造无线开关通道 push 测试用的最小产品 schema."""
    return {
        "pid": 854041,
        "name": "四键开关",
        "category": "relay_switch",
        "components": [
            {
                "cid": index,
                "name": "wireless switch channel",
                "type": 0,
                "category": "relay_switch",
                "index": index,
                "properties": [{"propId": "sp", "operators": ["set"]}],
            }
            for index in range(1, 5)
        ],
    }
