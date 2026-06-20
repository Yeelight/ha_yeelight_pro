"""Private-status and diagnostics tests for the Yeelight push transport."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

from aiohttp import WSMsgType
import pytest

from custom_components.yeelight_pro.push_transport import (
    YeelightPushWebSocketTransport,
)
from custom_components.yeelight_pro.push_transport_frames import safe_node_id_hash

from .push_transport_helpers import (
    FakeMessage,
    FakeSession,
    FakeWebSocket,
)


@pytest.mark.asyncio
async def test_push_transport_treats_private_subscribe_snapshot_as_control() -> None:
    """私有部署 subscribe ACK/快照帧是控制帧，不应分发到 coordinator."""
    websocket = FakeWebSocket(
        [
            FakeMessage(WSMsgType.TEXT, '{"result":"ok","timestamp":1}'),
            FakeMessage(
                WSMsgType.TEXT,
                (
                    '{"result":"ok","msgId":"redacted","timestamp":1,'
                    '"data":{"id":1,"method":"subscribe","params":{"type":2},'
                    '"version":"1.0","devices":[{"id":1,"resId":228215,'
                    '"groupId":228216,"roomId":228217}]}}'
                ),
            ),
            FakeMessage(
                WSMsgType.TEXT,
                (
                    '{"type":"prop","nodes":[{"id":1,"deviceId":228215,'
                    '"groupId":228216,"roomId":228217,"params":{"p":true}}]}'
                ),
            ),
        ]
    )
    session = FakeSession(websocket)
    callback = AsyncMock()
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="fake-token",
        auto_reconnect=False,
    )

    await transport.async_start(callback)
    await asyncio.sleep(0)

    callback.assert_awaited_once_with(
        {
            "type": "prop",
            "nodes": [
                {
                    "id": 1,
                    "deviceId": 228215,
                    "groupId": 228216,
                    "roomId": 228217,
                    "params": {"p": True},
                }
            ],
        }
    )
    health = transport.health.as_dict()
    assert health["control_frames"] == 2
    assert health["dispatched_payloads"] == 1
    assert health["last_control_method"] == "subscribe"
    assert health["last_subscribe_device_count"] == 1
    assert health["last_subscribe_state_device_count"] == 0
    assert health["last_subscribe_state_key_samples"] == []
    assert health["last_subscribe_node_hash_samples"] == ["f6fc42039fba3776"]
    assert health["last_subscribe_node_candidate_hash_samples"] == [
        [
            "f6fc42039fba3776",
            safe_node_id_hash(228215),
        ]
    ]
    assert health["last_data_node_hash_samples"] == ["f6fc42039fba3776"]
    assert health["last_data_node_candidate_hash_samples"] == [
        [
            "f6fc42039fba3776",
            safe_node_id_hash(228215),
        ]
    ]
    assert health["recent_data_node_hash_samples"] == ["f6fc42039fba3776"]
    assert health["recent_data_node_candidate_hash_samples"] == [
        [
            "f6fc42039fba3776",
            safe_node_id_hash(228215),
        ]
    ]
    assert health["last_runtime_error_type"] is None

    await transport.async_stop()

@pytest.mark.asyncio
async def test_push_transport_node_samples_ignore_device_relation_ids() -> None:
    """设备推送的 roomId/groupId 只是归属关系，不能进入节点匹配样本."""
    websocket = FakeWebSocket(
        [
            FakeMessage(
                WSMsgType.TEXT,
                (
                    '{"type":"prop","nodes":[{"id":1,"roomId":228217,'
                    '"groupId":228216,"params":{"p":true}}]}'
                ),
            )
        ]
    )
    session = FakeSession(websocket)
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="fake-token",
        auto_reconnect=False,
    )

    await transport.async_start(AsyncMock())
    await asyncio.sleep(0)

    health = transport.health.as_dict()
    expected = [[safe_node_id_hash(1)]]
    assert health["last_data_node_candidate_hash_samples"] == expected
    assert health["recent_data_node_candidate_hash_samples"] == expected
    assert safe_node_id_hash(228216) not in str(expected)
    assert safe_node_id_hash(228217) not in str(expected)

    await transport.async_stop()

@pytest.mark.asyncio
async def test_push_transport_summarizes_subscribe_snapshot_state_shape() -> None:
    """订阅快照若携带状态字段，只记录字段名和数量，不记录值。"""
    websocket = FakeWebSocket(
        [
            FakeMessage(
                WSMsgType.TEXT,
                (
                    '{"result":"ok","data":{"method":"subscribe","devices":['
                    '{"id":1,"params":{"secretValue":true}},'
                    '{"id":2,"properties":[{"propId":"p","value":false}]},'
                    '{"id":3,"o":false},'
                    '{"id":4,"propId":"p","value":true}'
                    ']}}'
                ),
            )
        ]
    )
    session = FakeSession(websocket)
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="fake-token",
        auto_reconnect=False,
    )

    await transport.async_start(AsyncMock())
    await asyncio.sleep(0)

    health = transport.health.as_dict()
    assert health["last_subscribe_device_count"] == 4
    assert health["last_subscribe_state_device_count"] == 4
    assert health["last_subscribe_state_key_samples"] == [
        "params",
        "properties",
        "o",
        "propId",
        "value",
    ]
    assert "secretValue" not in str(health)
    assert "true" not in str(health["last_subscribe_state_key_samples"])

    await transport.async_stop()

@pytest.mark.asyncio
async def test_push_transport_records_control_frames_as_control_ignored() -> None:
    """只有订阅/心跳 ACK 时，诊断应说明是控制帧而不是未知数据帧。"""
    websocket = FakeWebSocket(
        [FakeMessage(WSMsgType.TEXT, '{"method":"heartbeat","success":true}')]
    )
    session = FakeSession(websocket)
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="fake-token",
        auto_reconnect=False,
    )

    await transport.async_start(AsyncMock())
    await asyncio.sleep(0)

    health = transport.health.as_dict()
    assert health["control_frames"] == 1
    assert health["dispatched_payloads"] == 0
    assert health["ignored_messages"] == 2
    assert health["unsupported_messages"] == 0
    assert health["last_ignored_reason"] == "control_frame"
    assert health["last_ignored_payload_type"] is None
    assert health["last_unsupported_payload_shape"] is None
    assert health["last_control_method"] == "heartbeat"
    assert health["last_subscribe_device_count"] is None
    assert health["last_subscribe_state_device_count"] is None
    assert health["last_subscribe_state_key_samples"] == []
    assert health["last_data_node_hash_samples"] == []
    assert health["last_data_node_candidate_hash_samples"] == []
    assert health["recent_data_node_hash_samples"] == []
    assert health["recent_data_node_candidate_hash_samples"] == []

    await transport.async_stop()

@pytest.mark.asyncio
async def test_push_transport_treats_private_status_ack_as_control() -> None:
    """私有部署状态 ACK 只有结果文本时也应归类为控制帧。"""
    websocket = FakeWebSocket(
        [
            FakeMessage(
                WSMsgType.TEXT,
                '{"result":"ok","msgId":"redacted","data":{"message":"success"}}',
            )
        ]
    )
    session = FakeSession(websocket)
    callback = AsyncMock()
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="fake-token",
        auto_reconnect=False,
    )

    await transport.async_start(callback)
    await asyncio.sleep(0)

    health = transport.health.as_dict()
    callback.assert_not_awaited()
    assert health["control_frames"] == 1
    assert health["dispatched_payloads"] == 0
    assert health["unsupported_messages"] == 0
    assert health["last_control_method"] == "private_status_ack"
    assert health["private_status_frames"] == 1
    assert health["private_status_non_success_frames"] == 0
    assert health["last_private_status_result"] == "success"
    assert health["last_private_status_reason"] is None
    assert health["last_ignored_reason"] == "control_frame"
    assert health["last_unsupported_payload_shape"] is None

    await transport.async_stop()

@pytest.mark.asyncio
async def test_push_transport_ignores_private_status_text_without_closing() -> None:
    """私有部署状态文本帧不能打断后续业务 payload 接收。"""
    websocket = FakeWebSocket(
        [
            FakeMessage(
                WSMsgType.TEXT,
                '{"result":"error","msgId":"redacted","data":{"message":"secret"}}',
            ),
            FakeMessage(
                WSMsgType.TEXT,
                '{"type":"prop","nodes":[{"id":1,"params":{"p":true}}]}',
            ),
        ]
    )
    session = FakeSession(websocket)
    callback = AsyncMock()
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="fake-token",
        auto_reconnect=False,
    )

    await transport.async_start(callback)
    await asyncio.sleep(0)

    health = transport.health.as_dict()
    callback.assert_awaited_once_with(
        {"type": "prop", "nodes": [{"id": 1, "params": {"p": True}}]}
    )
    assert health["control_frames"] == 1
    assert health["dispatched_payloads"] == 1
    assert health["unsupported_messages"] == 0
    assert health["last_control_method"] == "private_status"
    assert health["private_status_frames"] == 1
    assert health["private_status_non_success_frames"] == 1
    assert health["last_private_status_result"] == "non_success"
    assert health["last_private_status_reason"] is None
    assert health["last_runtime_error_type"] is None
    assert health["last_disconnect_reason"] == "server_closed"
    assert health["last_ignored_reason"] is None
    assert health["last_unsupported_payload_shape"]["status"]["result_length"] == len(
        "error"
    )
    assert health["last_unsupported_payload_shape"]["status"]["data_keys"] == [
        "message"
    ]
    assert "secret" not in str(health)

    await transport.async_stop()

@pytest.mark.asyncio
async def test_push_transport_classifies_no_subscribable_devices_reason() -> None:
    """私有 push 无可订阅设备状态只记录固定 reason，不泄漏原文。"""
    websocket = FakeWebSocket(
        [
            FakeMessage(
                WSMsgType.TEXT,
                (
                    '{"result":"error","msgId":"redacted",'
                    '"data":{"message":"该用户无可订阅设备"}}'
                ),
            )
        ]
    )
    session = FakeSession(websocket)
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="fake-token",
        auto_reconnect=False,
    )

    await transport.async_start(AsyncMock())
    await asyncio.sleep(0)

    health = transport.health.as_dict()
    assert health["private_status_non_success_frames"] == 1
    assert health["last_private_status_result"] == "non_success"
    assert health["last_private_status_reason"] == "no_subscribable_devices"
    assert "该用户无可订阅设备" not in str(health)

    await transport.async_stop()

@pytest.mark.asyncio
async def test_push_transport_keeps_private_status_reason_after_success_ack() -> None:
    """后续成功 ACK 不应清空已识别的私有 push 订阅失败原因."""
    websocket = FakeWebSocket(
        [
            FakeMessage(
                WSMsgType.TEXT,
                (
                    '{"result":"error","msgId":"redacted",'
                    '"data":{"message":"该用户无可订阅设备"}}'
                ),
            ),
            FakeMessage(
                WSMsgType.TEXT,
                '{"result":"ok","msgId":"redacted","timestamp":1780000000}',
            ),
        ]
    )
    session = FakeSession(websocket)
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="fake-token",
        auto_reconnect=False,
    )

    await transport.async_start(AsyncMock())
    await asyncio.sleep(0)

    health = transport.health.as_dict()
    assert health["private_status_non_success_frames"] == 1
    assert health["last_private_status_result"] == "success"
    assert health["last_private_status_reason"] == "no_subscribable_devices"
    assert "该用户无可订阅设备" not in str(health)

    await transport.async_stop()
