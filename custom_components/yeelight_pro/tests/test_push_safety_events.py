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
    """烟感 push 告警即使无 schema events 也应落到安全事件组件。"""
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
            "ha_product_model": {"components": []},
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
        ("safety_alarm", "power_alarm")
    ]
    assert fired == [
        {
            ATTR_SOURCE_DEVICE_ID: "311931214",
            ATTR_COMPONENT_ID: "safety_alarm",
            ATTR_EVENT_TYPE: "power_alarm",
            ATTR_EVENT_ATTRIBUTES: {
                "message_id": "smoke-message-1",
                "timestamp": 1724658984,
                "version": "1.0",
                "raw_event": "power.alarm",
            },
        }
    ]
