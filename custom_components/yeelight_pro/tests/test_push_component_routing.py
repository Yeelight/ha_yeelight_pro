"""Component-scoped push update and event routing tests."""

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
from custom_components.yeelight_pro.switch import YeelightProSwitch


@pytest.mark.asyncio
async def test_coordinator_applies_indexed_push_data_rows_to_switch_entities(
    hass: HomeAssistant,
) -> None:
    """私有部署 data 行数组推送应立即刷新四键等多通道 switch 实体."""
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=MagicMock(),
        house_id=12345,
    )
    coordinator.devices = {
        228218: {
            "id": 228218,
            "device_id": 228218,
            "name": "四键开关",
            "category": "relay_switch",
            "type": "switch",
            "online": True,
            "params": {"1-sp": True, "2-sp": True, "3-sp": False, "4-sp": False},
        }
    }
    coordinator.data = coordinator.devices
    second_key = YeelightProSwitch(coordinator, 228218, component_id="switch_2")
    fourth_key = YeelightProSwitch(coordinator, 228218, component_id="switch_4")
    updates = 0

    def _listener() -> None:
        nonlocal updates
        updates += 1

    remove_listener = coordinator.async_add_listener(_listener)

    events = await coordinator.async_handle_push_payload(
        {
            "type": "prop",
            "nodes": [
                {
                    "resId": "228218",
                    "data": [
                        {"propId": "sp", "index": 2, "value": False},
                        {"propId": "sp", "index": 4, "value": True},
                    ],
                }
            ],
        }
    )

    try:
        assert events == []
        assert updates == 1
        assert second_key.is_on is False
        assert fourth_key.is_on is True
        refreshed = coordinator.get_device(228218)
        assert refreshed is not None
        assert refreshed["params"]["2-sp"] is False
        assert refreshed["params"]["4-sp"] is True
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

    remove_listener = coordinator.async_add_listener(_listener)

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


@pytest.mark.asyncio
async def test_coordinator_routes_multi_key_push_event_by_params_key(
    hass: HomeAssistant,
) -> None:
    """多情景按键共用 click 事件时，应按 params.key 路由到具体组件."""
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=MagicMock(),
        house_id=12345,
    )
    coordinator.devices = {
        228220: {
            "id": 228220,
            "device_id": 228220,
            "name": "Scene Panel",
            "category": "scene_panel",
            "type": "event",
            "ha_product_model": {
                "product": {
                    "model_id": "scene-panel-model",
                    "category": "scene_panel",
                    "name": "Scene Panel",
                    "manufacturer": "Yeelight",
                },
                "components": [
                    {
                        "component_id": "scene_button_1",
                        "category": "scene_panel",
                        "index": 1,
                        "events": [{"event_id": 1, "name": "click"}],
                    },
                    {
                        "component_id": "scene_button_2",
                        "category": "scene_panel",
                        "index": 2,
                        "events": [{"event_id": 1, "name": "click"}],
                    },
                ],
            },
        }
    }
    fired: list[dict] = []
    hass.bus.async_listen(DEVICE_EVENT_TYPE, lambda event: fired.append(event.data))

    events = await coordinator.async_handle_push_payload(
        {
            "type": "event",
            "msgId": "message-key-2",
            "nodes": [
                {
                    "id": 228220,
                    "nt": 2,
                    "event": "panel.click",
                    "params": {"key": 2, "count": 1},
                }
            ],
            "timestamp": 1724658984,
            "version": "1.0",
        }
    )
    await hass.async_block_till_done()

    assert [(event.component_id, event.event_type) for event in events] == [
        ("scene_button_2", "click")
    ]
    assert fired == [
        {
            ATTR_SOURCE_DEVICE_ID: "228220",
            ATTR_COMPONENT_ID: "scene_button_2",
            ATTR_EVENT_TYPE: "click",
            ATTR_EVENT_ATTRIBUTES: {
                "message_id": "message-key-2",
                "timestamp": 1724658984,
                "version": "1.0",
                "node_type": 2,
                "params": {"key": 2, "count": 1},
                "raw_event": "panel.click",
            },
        }
    ]
