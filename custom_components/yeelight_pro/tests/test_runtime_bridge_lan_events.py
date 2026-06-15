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


@pytest.mark.asyncio
async def test_coordinator_infers_wifi_panel_device_event_component(
    hass: HomeAssistant,
) -> None:
    """device_post.event 的 wifi_panel fallback 应按 schema 推断真实组件。"""
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=MagicMock(),
        house_id=12345,
    )
    coordinator.devices = {
        7919: {
            "id": 7919,
            "device_id": 7919,
            "name": "WiFi Panel",
            "category": "scene_panel",
            "type": "event",
            "ha_product_model": {
                "components": [
                    {
                        "component_id": "scene_panel",
                        "category": "scene_panel",
                        "events": [{"name": "panel.click"}],
                    }
                ],
            },
        }
    }
    fired: list[dict] = []
    hass.bus.async_listen(DEVICE_EVENT_TYPE, lambda event: fired.append(event.data))

    events = await coordinator.async_handle_lan_payload(
        {
            "id": 116,
            "method": "device_post.event",
            "version": "1.0",
            "params": {
                "id": 7919,
                "type": "keyClick",
                "params": {"key": 1, "count": 1},
            },
        }
    )
    await hass.async_block_till_done()

    assert [event.component_id for event in events] == ["scene_panel"]
    assert [event.event_type for event in events] == ["click"]
    assert fired == [
        {
            ATTR_SOURCE_DEVICE_ID: "7919",
            ATTR_COMPONENT_ID: "scene_panel",
            ATTR_EVENT_TYPE: "click",
            ATTR_EVENT_ATTRIBUTES: {
                "method": "device_post.event",
                "message_id": "116",
                "params": {"key": 1, "count": 1},
                "raw_event": "keyClick",
            },
        }
    ]


@pytest.mark.asyncio
async def test_coordinator_applies_lan_topology_auxiliary_nodes(
    hass: HomeAssistant,
) -> None:
    """LAN 拓扑推送应同步设备、房间、灯组和情景缓存。"""
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=None,
        house_id=12345,
    )
    listener = MagicMock()
    remove_listener = coordinator.async_add_listener(listener)

    events = await coordinator.async_handle_lan_payload(
        {
            "id": 13812,
            "method": "gateway_post.topology",
            "nodes": [
                {"id": 1001, "nt": 2, "type": 3, "n": "客厅灯", "roomid": 2001},
                {"id": 2001, "nt": 1, "n": "客厅"},
                {"id": 3001, "nt": 4, "type": 1, "n": "客厅灯组"},
                {"id": 4001, "nt": 6, "n": "回家"},
            ],
        }
    )

    assert events == []
    assert coordinator.data == coordinator.devices
    device = coordinator.devices[1001]
    assert device["name"] == "客厅灯"
    assert device["iot_category"] == "light"
    assert device["ha_platform"] == "light"
    assert device["device_info"]["model"] == "色温灯"
    assert device["device_info"]["suggested_area"] == "客厅"
    assert coordinator.rooms == [
        {"id": 2001, "name": "客厅", "type": None, "node_type": 1}
    ]
    assert coordinator.groups == [
        {"id": 3001, "name": "客厅灯组", "type": 1, "node_type": 4}
    ]
    assert coordinator.scenes == [{"id": 4001, "name": "回家"}]
    listener.assert_called_once()
    remove_listener()
    await coordinator.async_shutdown()
