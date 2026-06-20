"""Push event payload adapter and component inference tests."""

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
    ATTR_NODE_ID_CANDIDATES,
    push_event_payloads,
)


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


def test_push_event_payloads_carry_internal_node_id_candidates() -> None:
    """多 ID event 帧应带内部候选 ID，但不能写进 HA 事件属性。"""
    [event] = push_event_payloads(
        {
            "type": "event",
            "msgId": "message-alias",
            "nodes": [
                {
                    "id": 999998,
                    "deviceId": "228215",
                    "roomId": "228231",
                    "nt": 2,
                    "event": 1,
                }
            ],
        }
    )

    assert event[ATTR_SOURCE_DEVICE_ID] == "999998"
    assert event[ATTR_NODE_ID_CANDIDATES] == (
        ("id", 999998),
        ("deviceId", 228215),
        ("roomId", 228231),
    )
    assert ATTR_NODE_ID_CANDIDATES not in event[ATTR_EVENT_ATTRIBUTES]


def test_push_event_payloads_accept_device_post_event_payload() -> None:
    """WebSocket 私有部署复用 device_post.event 时也应进入 HA 事件总线。"""
    events = push_event_payloads(
        {
            "method": "device_post.event",
            "id": 116,
            "params": {
                "id": 7919,
                "type": "keyClick",
                "params": {"key": 1, "count": 1},
            },
        }
    )

    assert events == [
        {
            ATTR_SOURCE_DEVICE_ID: "7919",
            ATTR_COMPONENT_ID: "wifi_panel",
            ATTR_EVENT_TYPE: "keyClick",
            ATTR_EVENT_ATTRIBUTES: {
                "method": "device_post.event",
                "message_id": "116",
                "params": {"key": 1, "count": 1},
                "raw_event": "keyClick",
            },
        }
    ]


@pytest.mark.parametrize("wrapper_key", ["params", "result"])
def test_push_event_payloads_accept_alternate_wrapped_payloads(
    wrapper_key: str,
) -> None:
    """私有部署包裹 event 帧时，自动化事件仍应即时进入 HA。"""
    events = push_event_payloads(
        {
            "method": "message",
            wrapper_key: {
                "type": "event",
                "msgId": "message-3",
                "nodes": [
                    {
                        "id": 228217,
                        "nt": 2,
                        "event": "panel.click",
                        "params": {"key": 1},
                    }
                ],
            },
        }
    )

    assert events == [
        {
            ATTR_SOURCE_DEVICE_ID: "228217",
            ATTR_COMPONENT_ID: "node_type_2",
            ATTR_EVENT_TYPE: "panel.click",
            ATTR_EVENT_ATTRIBUTES: {
                "message_id": "message-3",
                "node_type": 2,
                "params": {"key": 1},
                "raw_event": "panel.click",
            },
        }
    ]


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
    """多个组件声明同一事件且没有 key/index 时不能猜测路由目标."""
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


def test_infer_event_component_id_routes_ambiguous_match_by_params_key() -> None:
    """多个组件声明同一事件时，可按文档 key 参数路由到具体按键."""
    payload = {
        ATTR_SOURCE_DEVICE_ID: "228215",
        ATTR_COMPONENT_ID: "node_type_2",
        ATTR_EVENT_TYPE: "click",
        ATTR_EVENT_ATTRIBUTES: {"params": {"key": 2}},
    }
    device_payload = {
        "ha_product_model": {
            "components": [
                {
                    "component_id": "scene_panel_1",
                    "index": 1,
                    "events": [{"event_id": 1, "name": "click"}],
                },
                {
                    "component_id": "scene_panel_2",
                    "index": 2,
                    "events": [{"event_id": 1, "name": "click"}],
                },
            ]
        }
    }

    inferred = infer_event_component_id(payload, device_payload)

    assert inferred[ATTR_COMPONENT_ID] == "scene_panel_2"


def test_infer_event_component_id_keeps_name_only_alarm_fallback() -> None:
    """安全事件路由不能只依赖设备名称。"""
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

    assert inferred[ATTR_COMPONENT_ID] == "push_event"
    assert payload[ATTR_COMPONENT_ID] == "push_event"


def test_infer_event_component_id_routes_declared_alarm_event_component() -> None:
    """schema 明确声明 power 告警事件时才补全事件组件。"""
    payload = {
        ATTR_SOURCE_DEVICE_ID: "311931214",
        ATTR_COMPONENT_ID: "push_event",
        ATTR_EVENT_TYPE: "power.alarm",
    }
    device_payload = {
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

    inferred = infer_event_component_id(payload, device_payload)

    assert inferred[ATTR_COMPONENT_ID] == "vendor_power_alarm"
    assert payload[ATTR_COMPONENT_ID] == "push_event"


def test_push_event_payload_rejects_invalid_nodes_shape() -> None:
    """event nodes 无效时也应显式报错，不能静默吞帧."""
    with pytest.raises(HomeAssistantError):
        push_event_payloads({"type": "event", "nodes": {"id": 1}})


def test_push_event_payload_rejects_invalid_node_items() -> None:
    """event nodes 列表内的坏节点必须显式报错."""
    with pytest.raises(HomeAssistantError):
        push_event_payloads({"type": "event", "nodes": [{"id": 1}, "bad-node"]})
