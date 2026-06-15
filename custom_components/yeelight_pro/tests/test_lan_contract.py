"""Yeelight Pro LAN protocol no-network contract tests."""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.const import (
    CONNECTION_MODE_CLOUD,
    DOMAIN,
)
from custom_components.yeelight_pro.diagnostics import async_get_config_entry_diagnostics
from custom_components.yeelight_pro.lan_contract import (
    LAN_DISCOVERY_MESSAGE,
    LAN_DISCOVERY_PORT,
    LAN_GATEWAY_PORT,
    LanMessageBuilder,
    YeelightLanPropertyUpdate,
    build_get_node_message,
    build_get_topology_message,
    build_set_properties_message,
    decode_lan_frames,
    encode_lan_frame,
    is_lan_push_message,
    lan_event_payloads,
    lan_property_updates,
    parse_discovery_response,
)
from custom_components.yeelight_pro.lan_methods import LAN_DEVICE_DISCOVERY_MESSAGE

from .diagnostics_helpers import build_diagnostics_entry


def test_lan_constants_match_gateway_discovery_contract() -> None:
    """局域网发现常量必须匹配本地协议文档，不做真实广播."""
    assert LAN_DISCOVERY_MESSAGE == "YEELIGHT_GATEWAY_CONTROL_DISCOVER"
    assert LAN_DISCOVERY_PORT == 1982
    assert LAN_GATEWAY_PORT == 65443


def test_lan_constants_match_wifi_panel_discovery_contract() -> None:
    """WiFi 全面屏使用独立 UDP 发现文本和 device_* 方法族。"""
    assert LAN_DEVICE_DISCOVERY_MESSAGE == "YEELIGHT_DEVICE_CONTROL_DISCOVER"
    builder = LanMessageBuilder()

    topology = builder.device_get_topology()
    prop = builder.device_set_properties([
        {"id": 7919, "nt": 2, "set": {"1-p": False}},
    ])

    assert topology == {
        "version": "1.0",
        "id": 1,
        "method": "device_get.topology",
    }
    assert prop == {
        "version": "1.0",
        "id": 2,
        "method": "device_set.prop",
        "nodes": [{"id": 7919, "nt": 2, "set": {"1-p": False}}],
    }


def test_parse_discovery_response_accepts_documented_fields() -> None:
    """发现响应 parser 应接受文档中的 pid/mac/did/ip 文本格式."""
    response = parse_discovery_response(
        """
        pid:1
        mac:F8:24:41:00:23:A4
        did:22535
        ip:192.168.1.101
        """
    )

    assert response.product_id == 1
    assert response.mac == "F8:24:41:00:23:A4"
    assert response.device_id == "22535"
    assert response.ip == "192.168.1.101"


@pytest.mark.parametrize(
    "payload",
    [
        "pid:1\nmac:F8:24:41:00:23:A4\ndid:22535",
        "pid:not-int\nmac:F8:24:41:00:23:A4\ndid:22535\nip:192.168.1.101",
    ],
)
def test_parse_discovery_response_rejects_invalid_required_fields(
    payload: str,
) -> None:
    """缺少必需字段或 pid 非数字时必须拒绝，避免生成半可信网关。"""
    with pytest.raises(ValueError, match="LAN discovery response"):
        parse_discovery_response(payload)


def test_lan_request_builder_adds_version_id_method_without_network() -> None:
    """请求 builder 只构造文档帧，不打开 UDP/TCP。"""
    assert build_get_topology_message(123) == {
        "version": "1.0",
        "id": 123,
        "method": "gateway_get.topology",
    }
    assert build_get_node_message(124, node_id=1270) == {
        "version": "1.0",
        "id": 124,
        "method": "gateway_get.node",
        "params": {"id": 1270},
    }


def test_build_set_properties_message_matches_documented_shape() -> None:
    """gateway_set.prop 应保留 set/toggle/action/scenes 结构。"""
    message = build_set_properties_message(
        125,
        nodes=[
            {
                "id": 7,
                "nt": 2,
                "duration": 500,
                "set": {"0-blp": True, "1-sp": False},
                "toggle": ["1-sp"],
                "action": {"motorAdjust": {"type": "pause"}},
            }
        ],
        scenes=[{"id": 1, "duration": 500}],
    )

    assert message == {
        "version": "1.0",
        "id": 125,
        "method": "gateway_set.prop",
        "nodes": [
            {
                "id": 7,
                "nt": 2,
                "duration": 500,
                "set": {"0-blp": True, "1-sp": False},
                "toggle": ["1-sp"],
                "action": {"motorAdjust": {"type": "pause"}},
            }
        ],
        "scenes": [{"id": 1, "duration": 500}],
    }


def test_build_set_properties_message_requires_nodes_or_scenes() -> None:
    """空控制请求必须拒绝，避免未来 transport 发送无意义帧。"""
    with pytest.raises(ValueError, match="requires nodes or scenes"):
        build_set_properties_message(1, nodes=[])


def test_lan_frame_codec_splits_crlf_json_messages() -> None:
    """TCP 帧 codec 应使用协议文档要求的 CRLF 分隔。"""
    first = {"id": 1, "method": "gateway_get.topology"}
    second = {"id": 2, "method": "gateway_post.prop", "nodes": []}

    encoded = encode_lan_frame(first) + encode_lan_frame(second)

    assert encoded.endswith(b"\r\n")
    assert b"\n{" in encoded
    assert decode_lan_frames(encoded) == [first, second]


def test_decode_lan_frames_rejects_non_object_json() -> None:
    """LAN frame 必须是 JSON object，不能接受数组或标量。"""
    with pytest.raises(ValueError, match="LAN frame must be a JSON object"):
        decode_lan_frames(json.dumps([{"id": 1}]) + "\r\n")


def test_lan_message_builder_increments_ids_across_methods() -> None:
    """builder 在不同 LAN 方法间共享递增 id。"""
    builder = LanMessageBuilder()

    topology = builder.get_topology()
    node = builder.get_node(1270)
    prop = builder.set_properties([{"id": 1270, "nt": 2, "set": {"p": True}}])

    assert topology["id"] == 1
    assert node["id"] == 2
    assert prop["id"] == 3
    assert topology["method"] == "gateway_get.topology"
    assert node["method"] == "gateway_get.node"
    assert prop["method"] == "gateway_set.prop"


def test_lan_contract_reexports_received_payload_adapters() -> None:
    """旧 lan_contract import 路径必须继续导出已拆分的 payload adapter。"""
    updates = lan_property_updates(
        {"method": "gateway_post.prop", "nodes": [{"id": 7, "params": {"p": True}}]}
    )

    assert updates == [YeelightLanPropertyUpdate(node_id=7, node_type=None, params={"p": True})]
    assert lan_event_payloads({"method": "gateway_post.event", "nodes": []}) == []


@pytest.mark.parametrize(
    "method",
    ["gateway_post.topology", "gateway_post.prop", "gateway_post.event"],
)
def test_gateway_post_messages_are_push_frames(method: str) -> None:
    """gateway_post.* 属于网关主动推送帧。"""
    assert is_lan_push_message({"method": method}) is True


@pytest.mark.asyncio
async def test_lan_contract_diagnostics_include_live_lan_runtime(
    hass: HomeAssistant,
) -> None:
    """未加载 entry 时只声明 LAN 静态合同，不误报 live runtime。"""
    entry: MagicMock = build_diagnostics_entry()
    hass.data[DOMAIN] = {}

    data = await async_get_config_entry_diagnostics(hass, entry)

    assert data["runtime"]["client_capabilities"] == {
        "connection_mode": CONNECTION_MODE_CLOUD,
        "supported_connection_modes": ["cloud", "private", "lan"],
        "cloud_http_polling": False,
        "private_http_polling": False,
        "lan_direct_control": False,
        "scan_login_contract": True,
        "scan_login_runtime": False,
        "push_message_adapter": True,
        "runtime_payload_bridge": True,
        "websocket_message_contract": True,
        "websocket_transport_runtime": False,
        "push_manager_contract": True,
        "lan_discovery_parser": True,
        "lan_message_contract": True,
        "lan_payload_adapter": True,
        "push_connection": False,
        "websocket_subscription": False,
        "websocket_event_notifications": False,
        "local_gateway_control": False,
        "lan_control": False,
        "mqtt_subscription": False,
    }
