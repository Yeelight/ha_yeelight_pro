"""Push payload normalization and coordinator dispatch tests."""
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
    DOMAIN,
)
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

    remove_listener = coordinator.async_add_listener(_listener)

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


@pytest.mark.asyncio
async def test_coordinator_dispatches_push_event_payload(
    hass: HomeAssistant,
) -> None:
    """coordinator 应复用现有 HA 事件总线桥处理推送事件."""
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=MagicMock(),
        house_id=12345,
    )
    coordinator.devices = {
        228215: {
            "id": 228215,
            "device_id": 228215,
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
                        "component_id": "scene_panel",
                        "category": "scene_panel",
                        "events": [{"event_id": 1, "name": "click"}],
                    }
                ],
            },
        }
    }
    fired: list[dict] = []
    hass.bus.async_listen(DEVICE_EVENT_TYPE, lambda event: fired.append(event.data))

    events = await coordinator.async_handle_push_payload(
        {
            "type": "event",
            "msgId": "message-1",
            "nodes": [{"id": 228215, "nt": 2, "event": 1}],
            "timestamp": 1724658984,
            "version": "1.0",
        }
    )
    await hass.async_block_till_done()

    assert [event.event_type for event in events] == ["click"]
    assert fired == [
        {
            ATTR_SOURCE_DEVICE_ID: "228215",
            ATTR_COMPONENT_ID: "scene_panel",
            ATTR_EVENT_TYPE: "click",
            ATTR_EVENT_ATTRIBUTES: {
                "message_id": "message-1",
                "timestamp": 1724658984,
                "version": "1.0",
                "node_type": 2,
                "raw_event": 1,
            },
        }
    ]


@pytest.mark.asyncio
async def test_coordinator_deduplicates_replayed_push_event_message_id(
    hass: HomeAssistant,
) -> None:
    """WebSocket 重连重放同一 msgId/event 时不能重复触发 HA 自动化."""
    coordinator = _scene_panel_push_coordinator(hass)
    fired: list[dict] = []
    hass.bus.async_listen(DEVICE_EVENT_TYPE, lambda event: fired.append(event.data))
    payload = {
        "type": "event",
        "msgId": "message-duplicate",
        "nodes": [{"id": 228215, "nt": 2, "event": 1}],
        "timestamp": 1724658984,
        "version": "1.0",
    }

    first_events = await coordinator.async_handle_push_payload(payload)
    replayed_events = await coordinator.async_handle_push_payload(payload)
    await hass.async_block_till_done()

    assert [event.event_type for event in first_events] == ["click"]
    assert replayed_events == []
    assert len(fired) == 1
    assert "message-duplicate" in fired[0][ATTR_EVENT_ATTRIBUTES]["message_id"]


@pytest.mark.asyncio
async def test_coordinator_dedupes_push_events_by_message_and_event_identity(
    hass: HomeAssistant,
) -> None:
    """同一 msgId 下不同事件节点仍应分别触发，避免过度去重."""
    coordinator = _scene_panel_push_coordinator(hass)
    fired: list[dict] = []
    hass.bus.async_listen(DEVICE_EVENT_TYPE, lambda event: fired.append(event.data))

    first_events = await coordinator.async_handle_push_payload({
        "type": "event",
        "msgId": "message-shared",
        "nodes": [{"id": 228215, "nt": 2, "event": 1}],
    })
    second_events = await coordinator.async_handle_push_payload({
        "type": "event",
        "msgId": "message-shared",
        "nodes": [{"id": 228215, "nt": 2, "event": "hold"}],
    })
    await hass.async_block_till_done()

    assert [event.event_type for event in first_events] == ["click"]
    assert [event.event_type for event in second_events] == ["hold"]
    assert [event[ATTR_EVENT_TYPE] for event in fired] == ["click", "hold"]


@pytest.mark.asyncio
async def test_coordinator_does_not_dedupe_push_events_without_message_id(
    hass: HomeAssistant,
) -> None:
    """缺少 msgId 的事件不构造去重键，避免误吞厂商异常帧."""
    coordinator = _scene_panel_push_coordinator(hass)
    fired: list[dict] = []
    hass.bus.async_listen(DEVICE_EVENT_TYPE, lambda event: fired.append(event.data))
    payload = {
        "type": "event",
        "nodes": [{"id": 228215, "nt": 2, "event": 1}],
    }

    first_events = await coordinator.async_handle_push_payload(payload)
    second_events = await coordinator.async_handle_push_payload(payload)
    await hass.async_block_till_done()

    assert [event.event_type for event in first_events] == ["click"]
    assert [event.event_type for event in second_events] == ["click"]
    assert [event[ATTR_EVENT_TYPE] for event in fired] == ["click", "click"]


def _scene_panel_push_coordinator(hass: HomeAssistant) -> YeelightProCoordinator:
    """构造带 scene panel schema 的 push event coordinator."""
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=MagicMock(),
        house_id=12345,
    )
    coordinator.devices = {
        228215: {
            "id": 228215,
            "device_id": 228215,
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
                        "component_id": "scene_panel",
                        "category": "scene_panel",
                        "events": [
                            {"event_id": 1, "name": "click"},
                            {"event_id": 2, "name": "hold"},
                        ],
                    }
                ],
            },
        }
    }
    return coordinator


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
