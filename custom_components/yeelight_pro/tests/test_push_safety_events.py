"""Push safety-event routing tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.const import (
    ATTR_COMPONENT_ID,
    ATTR_EVENT_ATTRIBUTES,
    ATTR_EVENT_TYPE,
    ATTR_SOURCE_DEVICE_ID,
    DEVICE_EVENT_TYPE,
)
from custom_components.yeelight_pro.core.coordinator import YeelightProCoordinator


@pytest.mark.asyncio
async def test_coordinator_dispatches_smoke_alarm_push_event(
    hass: HomeAssistant,
) -> None:
    """schema 声明的告警 push 事件应落到对应事件组件。"""
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=MagicMock(),
        house_id=12345,
    )
    coordinator.devices = {
        311931214: {
            "id": 311931214,
            "device_id": 311931214,
            "name": "厨房烟雾传感器",
            "category": "light",
            "iot_category": "other",
            "ha_product_model": {
                "components": [
                    {
                        "component_id": "vendor_power_alarm",
                        "events": [
                            {"event_id": 14, "name": "power.alarm"},
                            {"event_id": 15, "name": "power.normal"},
                        ],
                    }
                ]
            },
        }
    }
    fired: list[dict] = []
    hass.bus.async_listen(DEVICE_EVENT_TYPE, lambda event: fired.append(event.data))

    events = await coordinator.async_handle_push_payload(
        {
            "type": "event",
            "msgId": "smoke-message-1",
            "nodes": [{"id": 311931214, "event": "power.alarm"}],
            "timestamp": 1724658984,
            "version": "1.0",
        }
    )
    await hass.async_block_till_done()

    assert [(event.component_id, event.event_type) for event in events] == [
        ("vendor_power_alarm", "power_alarm")
    ]
    assert fired == [
        {
            ATTR_SOURCE_DEVICE_ID: "311931214",
            ATTR_COMPONENT_ID: "vendor_power_alarm",
            ATTR_EVENT_TYPE: "power_alarm",
            ATTR_EVENT_ATTRIBUTES: {
                "message_id": "smoke-message-1",
                "timestamp": 1724658984,
                "version": "1.0",
                "raw_event": "power.alarm",
            },
        }
    ]


@pytest.mark.asyncio
async def test_coordinator_keeps_name_only_smoke_alarm_on_push_event_component(
    hass: HomeAssistant,
) -> None:
    """无 schema 时，真实 push 告警只保留 runtime bus fallback component。"""
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=MagicMock(),
        house_id=12345,
    )
    coordinator.devices = {
        311931214: {
            "id": 311931214,
            "device_id": 311931214,
            "name": "厨房烟雾传感器",
            "category": "light",
            "iot_category": "light",
            "ha_product_model": {"components": []},
        }
    }
    fired: list[dict] = []
    hass.bus.async_listen(DEVICE_EVENT_TYPE, lambda event: fired.append(event.data))

    events = await coordinator.async_handle_push_payload(
        {
            "type": "event",
            "msgId": "smoke-message-2",
            "nodes": [{"id": 311931214, "event": "power.alarm"}],
            "timestamp": 1724658985,
            "version": "1.0",
        }
    )
    await hass.async_block_till_done()

    assert [(event.component_id, event.event_type) for event in events] == [
        ("push_event", "power_alarm")
    ]
    assert fired == [
        {
            ATTR_SOURCE_DEVICE_ID: "311931214",
            ATTR_COMPONENT_ID: "push_event",
            ATTR_EVENT_TYPE: "power_alarm",
            ATTR_EVENT_ATTRIBUTES: {
                "message_id": "smoke-message-2",
                "timestamp": 1724658985,
                "version": "1.0",
                "raw_event": "power.alarm",
            },
        }
    ]
