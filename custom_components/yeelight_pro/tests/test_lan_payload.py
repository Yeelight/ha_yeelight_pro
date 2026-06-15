"""Yeelight Pro LAN gateway_post payload adapter tests."""
from __future__ import annotations

import pytest

from homeassistant.exceptions import HomeAssistantError

from custom_components.yeelight_pro.capabilities.registry import normalize_event_type
from custom_components.yeelight_pro.const import (
    ATTR_COMPONENT_ID,
    ATTR_EVENT_ATTRIBUTES,
    ATTR_EVENT_TYPE,
    ATTR_SOURCE_DEVICE_ID,
)
from custom_components.yeelight_pro.event_support import normalize_runtime_event_payload
from custom_components.yeelight_pro.lan_payload import (
    lan_event_payloads,
    lan_property_updates,
    lan_scene_updates,
)


def test_lan_property_updates_normalize_gateway_post_prop_frame() -> None:
    """LAN 状态同步帧应转换为本地状态更新，不混入网络职责。"""
    updates = lan_property_updates(
        {
            "id": 1,
            "method": "gateway_post.prop",
            "nodes": [
                {
                    "id": 1001,
                    "nt": 2,
                    "o": True,
                    "fv": "1.0.1",
                    "params": {"p": True, "l": 20, "c": 255, "ct": 4000, "m": 1},
                }
            ],
            "scenes": [{"id": 413, "n": "Home", "params": {"state": "active"}}],
        }
    )

    assert len(updates) == 1
    assert updates[0].node_id == 1001
    assert updates[0].node_type == 2
    assert updates[0].params == {
        "p": True,
        "l": 20,
        "c": 255,
        "ct": 4000,
        "m": 1,
        "o": True,
    }


def test_lan_scene_updates_preserve_scene_name_and_state() -> None:
    """LAN 场景状态帧应保留场景名称和状态，供 coordinator 合并。"""
    updates = lan_scene_updates(
        {
            "id": 1,
            "method": "gateway_post.prop",
            "nodes": [
                {
                    "id": 1001,
                    "nt": 2,
                    "params": {"p": True},
                }
            ],
            "scenes": [{"id": 413, "n": "Home", "params": {"state": "active"}}],
        }
    )

    assert len(updates) == 1
    assert updates[0].scene_id == 413
    assert updates[0].name == "Home"
    assert updates[0].state == "active"


    property_updates = lan_property_updates(
        {
            "method": "gateway_post.prop",
            "nodes": [{"id": 1001, "nt": 2, "o": False}],
        }
    )

    assert len(property_updates) == 1
    assert property_updates[0].params == {"o": False}


def test_lan_property_updates_ignore_outgoing_gateway_set_prop() -> None:
    """控制请求 gateway_set.prop 不能被误当成入站状态推送。"""
    assert (
        lan_property_updates(
            {
                "id": 125,
                "method": "gateway_set.prop",
                "nodes": [{"id": 7, "nt": 2, "set": {"p": True}}],
            }
        )
        == []
    )


def test_lan_event_payloads_normalize_gateway_post_event_frame() -> None:
    """LAN 事件帧应转换为现有 runtime event 入口格式。"""
    events = lan_event_payloads(
        {
            "id": 13810,
            "method": "gateway_post.event",
            "version": "1.0",
            "nodes": [
                {
                    "params": {"key": 3, "count": 1},
                    "value": "panel.click",
                    "id": 331915,
                    "nt": 2,
                }
            ],
        }
    )

    assert events == [
        {
            ATTR_SOURCE_DEVICE_ID: "331915",
            ATTR_COMPONENT_ID: "node_type_2",
            ATTR_EVENT_TYPE: "panel.click",
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
    assert normalize_runtime_event_payload(events[0]).event_type == "click"


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("panel.release", "release_after_hold"),
        ("keyClick", "click"),
        ("approach.true", "human_enter"),
        ("approach.false", "human_leave"),
        ("handwave", "handwave"),
    ],
)
def test_lan_event_aliases_cover_documented_values(
    source: str,
    expected: str,
) -> None:
    """LAN 文档事件值应在 registry alias 层保持稳定归一化."""
    assert normalize_event_type(source) == expected


def test_lan_event_payloads_redact_sensitive_event_params() -> None:
    """事件 attributes 只保留自动化所需字段，不复制 IP/MAC/DID/token。"""
    [event] = lan_event_payloads(
        {
            "id": 13811,
            "method": "gateway_post.event",
            "nodes": [
                {
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
                    "value": "motion.true",
                    "id": 1552,
                    "nt": 2,
                }
            ],
        }
    )

    params = event[ATTR_EVENT_ATTRIBUTES]["params"]
    assert params == {"key": 1, "count": 2}
    assert "192.168.1.101" not in str(event)
    assert "F8:24:41:00:23:A4" not in str(event)
    assert "22535" not in str(event)
    assert "secret-access-token" not in str(event)
    assert "secret-token" not in str(event)


def test_lan_device_event_payloads_normalize_wifi_panel_keyclick() -> None:
    """WiFi 全面屏文档的 keyClick 应进入同一个点击自动化事件类型。"""
    [event] = lan_event_payloads(
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

    assert event == {
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
    assert normalize_runtime_event_payload(event).event_type == "click"


@pytest.mark.parametrize(
    ("adapter", "method"),
    [
        (lan_property_updates, "gateway_post.prop"),
        (lan_event_payloads, "gateway_post.event"),
    ],
)
def test_lan_payload_adapters_reject_invalid_nodes_shape(adapter, method: str) -> None:
    """无效 nodes 不应被静默当作空 LAN 推送吞掉。"""
    with pytest.raises(HomeAssistantError):
        adapter({"method": method, "nodes": {"id": 1}})


@pytest.mark.parametrize(
    "node",
    [
        {"id": 1001, "nt": 2},
        {"id": 1001, "nt": 2, "params": None},
        {"id": 1001, "nt": 2, "params": []},
        "bad-node",
    ],
)
def test_lan_property_updates_reject_invalid_node_params(node) -> None:
    """半坏 prop 节点必须显式报错，避免状态更新静默丢失。"""
    with pytest.raises(HomeAssistantError):
        lan_property_updates({"method": "gateway_post.prop", "nodes": [node]})
