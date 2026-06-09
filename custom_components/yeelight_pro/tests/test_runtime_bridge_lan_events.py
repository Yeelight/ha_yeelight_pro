"""Runtime bridge tests for received LAN event payloads."""

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
async def test_coordinator_dispatches_lan_event_payload(
    hass: HomeAssistant,
) -> None:
    """LAN 事件推送应复用 runtime event bridge 和 schema 组件推断。"""
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=MagicMock(),
        house_id=12345,
    )
    coordinator.devices = {
        331915: {
            "id": 331915,
            "device_id": 331915,
            "name": "LAN Scene Panel",
            "category": "scene_panel",
            "type": "event",
            "ha_product_model": {
                "components": [
                    {
                        "component_id": "scene_panel",
                        "category": "scene_panel",
                        "events": [{"name": "click"}],
                    }
                ],
            },
        }
    }
    fired: list[dict] = []
    hass.bus.async_listen(DEVICE_EVENT_TYPE, lambda event: fired.append(event.data))

    events = await coordinator.async_handle_lan_payload(
        {
            "id": 13810,
            "method": "gateway_post.event",
            "version": "1.0",
            "nodes": [
                {
                    "id": 331915,
                    "nt": 2,
                    "value": "panel.click",
                    "params": {"key": 3, "count": 1},
                }
            ],
        }
    )
    await hass.async_block_till_done()

    assert [event.event_type for event in events] == ["click"]
    assert fired == [
        {
            ATTR_SOURCE_DEVICE_ID: "331915",
            ATTR_COMPONENT_ID: "scene_panel",
            ATTR_EVENT_TYPE: "click",
            ATTR_EVENT_ATTRIBUTES: {
                "method": "gateway_post.event",
                "message_id": "13810",
                "version": "1.0",
                "node_type": 2,
                "params": {"key": 3, "count": 1},
                "raw_event": "panel.click",
            },
        }
    ]


@pytest.mark.asyncio
async def test_coordinator_infers_lan_event_component_without_node_type(
    hass: HomeAssistant,
) -> None:
    """LAN 事件缺少 nt 时也应把 lan_event fallback 交给 schema 推断。"""
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=MagicMock(),
        house_id=12345,
    )
    coordinator.devices = {
        331916: {
            "id": 331916,
            "device_id": 331916,
            "name": "LAN Button",
            "category": "scene_panel",
            "type": "event",
            "ha_product_model": {
                "components": [
                    {
                        "component_id": "scene_button",
                        "category": "scene_panel",
                        "events": [{"name": "hold"}],
                    }
                ],
            },
        }
    }
    fired: list[dict] = []
    hass.bus.async_listen(DEVICE_EVENT_TYPE, lambda event: fired.append(event.data))

    events = await coordinator.async_handle_lan_payload(
        {
            "id": 13811,
            "method": "gateway_post.event",
            "nodes": [
                {
                    "id": 331916,
                    "value": "panel.hold",
                    "params": {"key": 2},
                }
            ],
        }
    )
    await hass.async_block_till_done()

    assert [event.component_id for event in events] == ["scene_button"]
    assert [event.event_type for event in events] == ["hold"]
    assert fired[0][ATTR_COMPONENT_ID] == "scene_button"
    assert fired[0][ATTR_EVENT_TYPE] == "hold"
