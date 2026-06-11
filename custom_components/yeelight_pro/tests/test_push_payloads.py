"""Push payload adapter and event inference tests."""

from __future__ import annotations

import pytest

from homeassistant.exceptions import HomeAssistantError

from custom_components.yeelight_pro.const import (
    ATTR_COMPONENT_ID,
    ATTR_EVENT_ATTRIBUTES,
    ATTR_EVENT_TYPE,
    ATTR_SOURCE_DEVICE_ID,
)
from custom_components.yeelight_pro.event_support import infer_event_component_id
from custom_components.yeelight_pro.push import (
    push_event_payloads,
    push_property_updates,
)


def test_push_property_updates_normalize_open_platform_payload() -> None:
    """WebSocket prop payload 应先转换成本地状态覆盖，不直接耦合网络连接."""
    updates = push_property_updates(
        {
            "type": "prop",
            "msgId": "message-1",
            "nodes": [
                {
                    "id": 228215,
                    "nt": 2,
                    "params": {"p": True, "ct": 4500, "l": 100, "o": True},
                }
            ],
            "timestamp": 1724658984,
            "version": "1.0",
        }
    )

    assert len(updates) == 1
    assert updates[0].node_id == 228215
    assert updates[0].node_type == 2
    assert updates[0].params == {"p": True, "ct": 4500, "l": 100, "o": True}


def test_push_property_updates_do_not_fold_message_meta_into_state() -> None:
    """prop 消息元数据只用于传输追踪，不能混入设备状态 params."""
    updates = push_property_updates(
        {
            "type": "prop",
            "msgId": "message-secret",
            "nodes": [
                {
                    "id": 228215,
                    "nt": 2,
                    "componentId": "component-secret",
                    "roomName": "Room Secret",
                    "params": {"p": False},
                }
            ],
            "timestamp": 1724658984,
            "version": "1.0",
        }
    )

    assert len(updates) == 1
    assert updates[0].params == {"p": False}
    assert "message-secret" not in str(updates[0].params)
    assert "component-secret" not in str(updates[0].params)
    assert "Room Secret" not in str(updates[0].params)


def test_push_event_payloads_normalize_open_platform_payload() -> None:
    """WebSocket event payload 应转换为现有 runtime event 入口格式."""
    events = push_event_payloads(
        {
            "type": "event",
            "msgId": "message-1",
            "nodes": [{"id": 228215, "nt": 2, "event": 1}],
            "timestamp": 1724658984,
            "version": "1.0",
        }
    )

    assert events == [
        {
            ATTR_SOURCE_DEVICE_ID: "228215",
            ATTR_COMPONENT_ID: "node_type_2",
            ATTR_EVENT_TYPE: 1,
            ATTR_EVENT_ATTRIBUTES: {
                "message_id": "message-1",
                "timestamp": 1724658984,
                "version": "1.0",
                "node_type": 2,
                "raw_event": 1,
            },
        }
    ]


def test_push_event_payloads_redact_sensitive_event_params() -> None:
    """push event params 可供自动化使用，但不能复制 IP/MAC/DID/token。"""
    [event] = push_event_payloads(
        {
            "type": "event",
            "msgId": "message-2",
            "nodes": [
                {
                    "id": 228216,
                    "nt": 2,
                    "event": "panel.click",
                    "params": {
                        "key": 1,
                        "count": 2,
                        "ip": "192.168.1.101",
                        "mac": "F8:24:41:00:23:A4",
                        "did": "22535",
                        "device_id": "secret-device",
                        "access_token": "secret-access-token",
                        "token": "secret-token",
                    },
                }
            ],
            "timestamp": 1724658985,
            "version": "1.0",
        }
    )

    params = event[ATTR_EVENT_ATTRIBUTES]["params"]
    assert params == {"key": 1, "count": 2}
    assert "192.168.1.101" not in str(event)
    assert "F8:24:41:00:23:A4" not in str(event)
    assert "22535" not in str(event)
    assert "secret-access-token" not in str(event)
    assert "secret-token" not in str(event)


def test_infer_event_component_id_uses_unique_schema_event_match() -> None:
    """缺少 componentId 的 push event 可按唯一 schema 事件补全组件."""
    payload = {
        ATTR_SOURCE_DEVICE_ID: "228215",
        ATTR_COMPONENT_ID: "node_type_2",
        ATTR_EVENT_TYPE: 1,
    }
    device_payload = {
        "ha_product_model": {
            "components": [
                {
                    "component_id": "scene_panel",
                    "events": [{"event_id": 1, "name": "click"}],
                }
            ]
        }
    }

    inferred = infer_event_component_id(payload, device_payload)

    assert inferred[ATTR_COMPONENT_ID] == "scene_panel"
    assert payload[ATTR_COMPONENT_ID] == "node_type_2"


def test_infer_event_component_id_keeps_fallback_on_ambiguous_match() -> None:
    """多个组件声明同一事件时不能猜测路由目标."""
    payload = {
        ATTR_SOURCE_DEVICE_ID: "228215",
        ATTR_COMPONENT_ID: "node_type_2",
        ATTR_EVENT_TYPE: "click",
    }
    device_payload = {
        "ha_product_model": {
            "components": [
                {
                    "component_id": "scene_panel_1",
                    "events": [{"event_id": 1, "name": "click"}],
                },
                {
                    "component_id": "scene_panel_2",
                    "events": [{"event_id": 1, "name": "click"}],
                },
            ]
        }
    }

    inferred = infer_event_component_id(payload, device_payload)

    assert inferred[ATTR_COMPONENT_ID] == "node_type_2"


def test_infer_event_component_id_routes_smoke_alarm_fallback() -> None:
    """烟感告警事件无 schema 组件时应路由到安全事件实体。"""
    payload = {
        ATTR_SOURCE_DEVICE_ID: "311931214",
        ATTR_COMPONENT_ID: "push_event",
        ATTR_EVENT_TYPE: "power.alarm",
    }
    device_payload = {
        "name": "厨房烟雾传感器",
        "category": "light",
        "iot_category": "other",
        "ha_product_model": {"components": []},
    }

    inferred = infer_event_component_id(payload, device_payload)

    assert inferred[ATTR_COMPONENT_ID] == "safety_alarm"
    assert payload[ATTR_COMPONENT_ID] == "push_event"


def test_push_payload_rejects_invalid_nodes_shape() -> None:
    """无效 nodes 不应被静默当作空推送吞掉."""
    with pytest.raises(HomeAssistantError):
        push_property_updates({"type": "prop", "nodes": {"id": 1}})


@pytest.mark.parametrize(
    ("adapter", "payload_type"),
    [
        (push_property_updates, "prop"),
        (push_event_payloads, "event"),
    ],
)
def test_push_payload_rejects_invalid_node_items(adapter, payload_type: str) -> None:
    """nodes 列表内的坏节点也必须显式报错，不能半吞推送帧."""
    with pytest.raises(HomeAssistantError):
        adapter({"type": payload_type, "nodes": [{"id": 1}, "bad-node"]})
