"""Push event coordinator routing and dedupe tests."""
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
async def test_coordinator_routes_push_event_by_device_id_alias(
    hass: HomeAssistant,
) -> None:
    """私有部署 event 帧使用行 ID + deviceId 时，应按已加载设备 ID 触发。"""
    coordinator = _scene_panel_push_coordinator(hass)
    fired: list[dict] = []
    hass.bus.async_listen(DEVICE_EVENT_TYPE, lambda event: fired.append(event.data))

    events = await coordinator.async_handle_push_payload(
        {
            "type": "event",
            "msgId": "message-device-alias",
            "nodes": [
                {
                    "id": 999998,
                    "deviceId": "228215",
                    "nt": 2,
                    "event": 1,
                }
            ],
        }
    )
    await hass.async_block_till_done()

    assert [
        (event.source_device_id, event.component_id, event.event_type)
        for event in events
    ] == [("228215", "scene_panel", "click")]
    assert fired == [
        {
            ATTR_SOURCE_DEVICE_ID: "228215",
            ATTR_COMPONENT_ID: "scene_panel",
            ATTR_EVENT_TYPE: "click",
            ATTR_EVENT_ATTRIBUTES: {
                "message_id": "message-device-alias",
                "node_type": 2,
                "raw_event": 1,
            },
        }
    ]
    assert "_node_id_candidates" not in str(fired)
    assert "999998" not in str(fired)

@pytest.mark.asyncio
async def test_coordinator_routes_push_event_by_res_id_alias(
    hass: HomeAssistant,
) -> None:
    """私有部署 event 帧使用 resId 时，也应命中已加载设备。"""
    coordinator = _scene_panel_push_coordinator(hass)

    events = await coordinator.async_handle_push_payload(
        {
            "type": "event",
            "msgId": "message-res-alias",
            "nodes": [
                {
                    "id": 999997,
                    "resId": "228215",
                    "nt": 2,
                    "event": 1,
                }
            ],
        }
    )

    assert [
        (event.source_device_id, event.component_id, event.event_type)
        for event in events
    ] == [("228215", "scene_panel", "click")]

@pytest.mark.asyncio
async def test_push_device_event_does_not_route_by_room_relation_id(
    hass: HomeAssistant,
) -> None:
    """设备事件里的 roomId 是归属关系，不能替代缺失的设备节点 ID。"""
    coordinator = _scene_panel_push_coordinator(hass)
    coordinator.rooms = [{"id": 228231, "name": "Room", "params": {"p": True}}]

    events = await coordinator.async_handle_push_payload(
        {
            "type": "event",
            "msgId": "message-room-relation",
            "nodes": [
                {
                    "id": 999996,
                    "roomId": 228231,
                    "nt": 2,
                    "event": 1,
                }
            ],
        }
    )

    assert [
        (event.source_device_id, event.component_id, event.event_type)
        for event in events
    ] == [("999996", "node_type_2", "click")]

@pytest.mark.asyncio
async def test_push_event_alias_routes_loaded_device_when_import_filter_enabled(
    hass: HomeAssistant,
) -> None:
    """导入过滤开启时，已加载设备的 event alias 仍应即时触发。"""
    coordinator = _scene_panel_push_coordinator(hass)
    coordinator.options = {
        "device_import_filter": {
            "enabled": True,
            "mode": "include",
            "include": {"category": ["scene_panel"]},
        }
    }

    events = await coordinator.async_handle_push_payload(
        {
            "type": "event",
            "msgId": "message-import-filter-alias",
            "nodes": [{"id": 999994, "deviceId": "228215", "nt": 2, "event": 1}],
        }
    )

    assert [
        (event.source_device_id, event.component_id, event.event_type)
        for event in events
    ] == [("228215", "scene_panel", "click")]

@pytest.mark.asyncio
async def test_coordinator_deduplicates_event_after_alias_resolution(
    hass: HomeAssistant,
) -> None:
    """同一事件先用 id 后用 deviceId 到达时，应按解析后的设备 ID 去重。"""
    coordinator = _scene_panel_push_coordinator(hass)
    first_payload = {
        "type": "event",
        "msgId": "message-alias-dedupe",
        "nodes": [{"id": 228215, "nt": 2, "event": 1}],
    }
    alias_payload = {
        "type": "event",
        "msgId": "message-alias-dedupe",
        "nodes": [{"id": 999995, "deviceId": "228215", "nt": 2, "event": 1}],
    }

    first_events = await coordinator.async_handle_push_payload(first_payload)
    alias_events = await coordinator.async_handle_push_payload(alias_payload)

    assert [(event.source_device_id, event.event_type) for event in first_events] == [
        ("228215", "click")
    ]
    assert alias_events == []

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
