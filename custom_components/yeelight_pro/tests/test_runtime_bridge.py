"""Runtime bridge tests for received push and LAN payloads."""
from __future__ import annotations

from unittest.mock import MagicMock
from types import SimpleNamespace

import pytest

from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.const import DOMAIN
from custom_components.yeelight_pro.core.coordinator import YeelightProCoordinator
from custom_components.yeelight_pro.core.device_payload import DevicePayloadBuilder
from custom_components.yeelight_pro.light import YeelightProLight
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

    remove_listener = coordinator.async_add_listener(
        _listener,
        ("device", "228216"),
    )

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
async def test_lan_property_update_notifies_only_affected_device_context(
    hass: HomeAssistant,
) -> None:
    """运行时属性推送只刷新受影响设备，避免 HA 前端状态事件风暴。"""
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
            "params": {"p": True},
        },
        228217: {
            "id": 228217,
            "device_id": 228217,
            "name": "Other Lamp",
            "category": "light",
            "type": "light",
            "online": True,
            "params": {"p": True},
        },
    }
    coordinator.data = coordinator.devices
    counts = {"target": 0, "other": 0, "global": 0}

    def _target_listener() -> None:
        counts["target"] += 1

    def _other_listener() -> None:
        counts["other"] += 1

    def _global_listener() -> None:
        counts["global"] += 1

    remove_target = coordinator.async_add_listener(
        _target_listener,
        ("device", "228216"),
    )
    remove_other = coordinator.async_add_listener(
        _other_listener,
        ("device", "228217"),
    )
    remove_global = coordinator.async_add_listener(_global_listener)

    await coordinator.async_handle_lan_payload(
        {
            "method": "gateway_post.prop",
            "nodes": [{"id": 228216, "nt": 2, "params": {"p": False}}],
        }
    )

    try:
        assert counts == {"target": 1, "other": 0, "global": 0}
        device = coordinator.get_device(228216)
        assert device is not None
        assert device["params"]["p"] is False
    finally:
        remove_target()
        remove_other()
        remove_global()


@pytest.mark.asyncio
async def test_lan_property_update_matches_entity_object_listener_context(
    hass: HomeAssistant,
) -> None:
    """真实 HA 若以实体对象作为 context，push 定向刷新仍必须命中实体."""
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
            "params": {"p": True},
        },
        228217: {
            "id": 228217,
            "device_id": 228217,
            "name": "Other Lamp",
            "category": "light",
            "type": "light",
            "online": True,
            "params": {"p": True},
        },
    }
    coordinator.data = coordinator.devices
    counts = {"target": 0, "other": 0}

    def _target_listener() -> None:
        counts["target"] += 1

    def _other_listener() -> None:
        counts["other"] += 1

    remove_target = coordinator.async_add_listener(
        _target_listener,
        SimpleNamespace(_device_id=228216),
    )
    remove_other = coordinator.async_add_listener(
        _other_listener,
        SimpleNamespace(_device_id=228217),
    )

    await coordinator.async_handle_lan_payload(
        {
            "method": "gateway_post.prop",
            "nodes": [{"id": 228216, "nt": 2, "params": {"p": False}}],
        }
    )

    try:
        assert counts == {"target": 1, "other": 0}
        device = coordinator.get_device(228216)
        assert device is not None
        assert device["params"]["p"] is False
    finally:
        remove_target()
        remove_other()


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
