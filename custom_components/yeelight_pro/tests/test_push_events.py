"""Push payload normalization and coordinator dispatch tests."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.const import DOMAIN
from custom_components.yeelight_pro.core.coordinator import YeelightProCoordinator
from custom_components.yeelight_pro.core.device_payload import DevicePayloadBuilder
from custom_components.yeelight_pro.light import YeelightProLight
from custom_components.yeelight_pro.projector.switch import project_switches


@pytest.mark.asyncio
async def test_coordinator_applies_push_property_updates(
    hass: HomeAssistant,
) -> None:
    """coordinator 应可消费已接收的属性推送并刷新实体监听器."""
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=MagicMock(),
        house_id=12345,
    )
    coordinator.devices = {
        228215: {
            "id": 228215,
            "device_id": 228215,
            "name": "Push Lamp",
            "type": "light",
            "online": True,
            "params": {"p": True, "l": 25},
        }
    }
    coordinator.data = coordinator.devices
    light = YeelightProLight(coordinator, 228215)
    updates = 0

    def _listener() -> None:
        nonlocal updates
        updates += 1

    remove_listener = coordinator.async_add_listener(
        _listener,
        ("device", "228215"),
    )

    events = await coordinator.async_handle_push_payload(
        {
            "type": "prop",
            "nodes": [{"id": 228215, "nt": 2, "params": {"p": False, "l": 80}}],
        }
    )

    try:
        assert events == []
        assert coordinator._runtime_state.overrides[228215]["params"] == {
            "p": False,
            "l": 80,
        }
        device = coordinator.get_device(228215)
        assert device is not None
        assert device["params"]["p"] is False
        assert device["params"]["l"] == 80
        assert light.is_on is False
        assert light.brightness == 203
        assert updates == 1
    finally:
        remove_listener()


@pytest.mark.asyncio
async def test_coordinator_applies_push_property_updates_to_canonical_state(
    hass: HomeAssistant,
) -> None:
    """schema-aware 设备收到 prop 推送后，canonical state 也应立即可读."""
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=MagicMock(),
        house_id=12345,
    )
    device = {
        "id": 228216,
        "device_id": 228216,
        "name": "Schema Push Lamp",
        "category": "light",
        "type": "light",
        "online": True,
        "pid": 100,
        "product_schema": _push_lamp_schema(),
        "params": {"p": True, "l": 25},
    }
    DevicePayloadBuilder().attach_canonical_models_if_available(device)
    coordinator.devices = {228216: device}
    coordinator.data = coordinator.devices
    light = YeelightProLight(coordinator, 228216)

    events = await coordinator.async_handle_push_payload(
        {
            "type": "prop",
            "nodes": [
                {
                    "id": 228216,
                    "nt": 2,
                    "params": {"p": False, "l": 80, "o": False},
                }
            ],
        }
    )

    assert events == []
    refreshed = coordinator.get_device(228216)
    assert refreshed is not None
    assert refreshed["params"]["p"] is False
    assert refreshed["params"]["l"] == 80
    assert refreshed["online"] is False
    component = refreshed["ha_device_instance"]["components"][0]
    assert refreshed["ha_device_instance"]["online"] is False
    assert component["available"] is False
    assert component["state"] == {"p": False, "l": 80}
    assert light.available is False
    assert light.is_on is False
    assert light.brightness == 203


@pytest.mark.asyncio
async def test_coordinator_routes_indexed_push_updates_to_matching_component(
    hass: HomeAssistant,
) -> None:
    """indexed prop 推送只应更新对应组件，不能串到其他开关通道."""
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=MagicMock(),
        house_id=12345,
    )
    coordinator.devices = {
        228217: {
            "id": 228217,
            "device_id": 228217,
            "name": "Dual Relay",
            "category": "relay_switch",
            "type": "switch",
            "online": True,
            "params": {"1-p": True, "2-p": True},
            "ha_device_instance": {
                "device_id": "228217",
                "name": "Dual Relay",
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

    await coordinator.async_handle_push_payload(
        {
            "type": "prop",
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






















def _push_lamp_schema() -> dict:
    """构造推送状态测试用的最小灯具 schema."""
    return {
        "pid": 100,
        "name": "Schema Lamp Product",
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
