"""Tests for the Yeelight Pro WebSocket push transport."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

from aiohttp import WSMsgType
import pytest

from custom_components.yeelight_pro.push_transport import (
    YeelightPushWebSocketTransport,
)

from .push_transport_helpers import (
    ControlledSleep,
    FakeMessage,
    FakeSession,
    FakeWebSocket,
    OpenFakeWebSocket,
    wait_for_sleep_calls,
)


@pytest.mark.asyncio
async def test_push_transport_connects_subscribes_and_dispatches_json_objects() -> None:
    """transport 打开 URL 后先订阅，再只分发 JSON object payload."""
    websocket = FakeWebSocket(
        [
            FakeMessage(WSMsgType.TEXT, '{"method":"subscribe","code":"200"}'),
            FakeMessage(WSMsgType.TEXT, '{"method":"heartbeat","success":true}'),
            FakeMessage(WSMsgType.TEXT, '{"type":"prop","nodes":[{"id":1}]}'),
            FakeMessage(
                WSMsgType.TEXT,
                (
                    '{"method":"message","data":{"type":"prop",'
                    '"nodes":[{"id":2,"params":{"p":true}}]}}'
                ),
            ),
            FakeMessage(
                WSMsgType.TEXT,
                (
                    '{"method":"message","params":{"type":"prop",'
                    '"nodes":[{"id":3,"params":{"p":false}}]}}'
                ),
            ),
            FakeMessage(
                WSMsgType.TEXT,
                (
                    '{"result":{"type":"event",'
                    '"nodes":[{"id":4,"event":"panel.click"}]}}'
                ),
            ),
            FakeMessage(
                WSMsgType.TEXT,
                (
                    '{"type":"prop","id":5,"propId":"p","value":true}'
                ),
            ),
            FakeMessage(
                WSMsgType.TEXT,
                (
                    '{"method":"message","data":{"type":"prop","resId":"6",'
                    '"data":[{"propId":"sp","index":1,"value":false}]}}'
                ),
            ),
            FakeMessage(
                WSMsgType.TEXT,
                (
                    '{"method":"message","result":{"code":200,"data":'
                    '{"method":"gateway_post.prop","nodes":[{"id":9,'
                    '"params":{"1-p":false}}]}}}'
                ),
            ),
            FakeMessage(
                WSMsgType.TEXT,
                (
                    '{"method":"gateway_post.prop",'
                    '"nodes":[{"id":7,"nt":2,"params":{"p":true}}]}'
                ),
            ),
            FakeMessage(
                WSMsgType.TEXT,
                (
                    '{"method":"device_post.event",'
                    '"params":{"id":8,"type":"keyClick","params":{"key":1}}}'
                ),
            ),
            FakeMessage(WSMsgType.TEXT, '["not-object"]'),
            FakeMessage(WSMsgType.TEXT, "not-json"),
            FakeMessage(WSMsgType.TEXT, '{"type":"unknown","nodes":[]}'),
            FakeMessage(WSMsgType.BINARY, b'{"type":"event","nodes":[]}'),
            FakeMessage(WSMsgType.CLOSE, None),
        ]
    )
    session = FakeSession(websocket)
    callback = AsyncMock()
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="Bearer fake-token",
        auto_reconnect=False,
    )

    await transport.async_start(callback)
    await asyncio.sleep(0)

    assert session.connected_urls == ["wss://push.yeelight.com/ws/fake-token"]
    assert websocket.sent_json == [
        {
            "id": 1,
            "method": "subscribe",
            "params": {"type": 2},
            "timestamp": websocket.sent_json[0]["timestamp"],
            "version": "1.0",
        }
    ]
    assert isinstance(websocket.sent_json[0]["timestamp"], int)
    assert callback.await_args_list[0].args[0] == {
        "type": "prop",
        "nodes": [{"id": 1}],
    }
    assert callback.await_args_list[1].args[0] == {
        "method": "message",
        "data": {"type": "prop", "nodes": [{"id": 2, "params": {"p": True}}]},
    }
    assert callback.await_args_list[2].args[0] == {
        "method": "message",
        "params": {"type": "prop", "nodes": [{"id": 3, "params": {"p": False}}]},
    }
    assert callback.await_args_list[3].args[0] == {
        "result": {"type": "event", "nodes": [{"id": 4, "event": "panel.click"}]},
    }
    assert callback.await_args_list[4].args[0] == {
        "type": "prop",
        "id": 5,
        "propId": "p",
        "value": True,
    }
    assert callback.await_args_list[5].args[0] == {
        "method": "message",
        "data": {
            "type": "prop",
            "resId": "6",
            "data": [{"propId": "sp", "index": 1, "value": False}],
        },
    }
    assert callback.await_args_list[6].args[0] == {
        "method": "message",
        "result": {
            "code": 200,
            "data": {
                "method": "gateway_post.prop",
                "nodes": [{"id": 9, "params": {"1-p": False}}],
            },
        },
    }
    assert callback.await_args_list[7].args[0] == {
        "method": "gateway_post.prop",
        "nodes": [{"id": 7, "nt": 2, "params": {"p": True}}],
    }
    assert callback.await_args_list[8].args[0] == {
        "method": "device_post.event",
        "params": {"id": 8, "type": "keyClick", "params": {"key": 1}},
    }
    assert callback.await_args_list[9].args[0] == {"type": "event", "nodes": []}
    assert callback.await_count == 10
    health = transport.health.as_dict()
    assert health["running"] is True
    assert health["websocket_open"] is False
    assert health["connect_attempts"] == 1
    assert health["connected_count"] == 1
    assert health["disconnected_count"] == 1
    assert health["reconnect_attempts"] == 0
    assert health["received_messages"] == 15
    assert health["decoded_json_messages"] == 13
    assert health["dispatched_payloads"] == 10
    assert health["ignored_messages"] == 4
    assert health["malformed_messages"] == 2
    assert health["control_frames"] == 3
    assert health["subscribe_sent_count"] == 1
    assert health["heartbeat_sent_count"] == 0
    assert health["last_subscribe_error_type"] is None
    assert health["last_start_error_type"] is None
    assert health["last_runtime_error_type"] is None
    assert health["last_handshake_status"] is None
    assert health["last_disconnect_reason"] == "server_closed"
    assert health["last_close_code"] is None
    assert health["last_close_exception_type"] is None
    assert health["first_frame_received"] is True
    assert health["last_payload_type"] == "event"
    assert health["last_ignored_reason"] is None
    assert health["last_ignored_payload_type"] is None
    assert health["last_subscribe_sent_at"] is not None
    assert health["last_message_at"] is not None
    assert health["last_dispatched_at"] is not None

    await transport.async_stop()


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
                    '"version":"1.0","devices":[{"id":1}]}}'
                ),
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

    callback.assert_awaited_once_with(
        {"type": "prop", "nodes": [{"id": 1, "params": {"p": True}}]}
    )
    health = transport.health.as_dict()
    assert health["control_frames"] == 2
    assert health["dispatched_payloads"] == 1
    assert health["last_runtime_error_type"] is None

    await transport.async_stop()


@pytest.mark.asyncio
async def test_push_transport_sends_heartbeat_until_stopped() -> None:
    """transport 订阅后按文档间隔发送 heartbeat，stop 后取消心跳任务."""
    sleep = ControlledSleep()
    websocket = OpenFakeWebSocket()
    session = FakeSession(websocket)
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="fake-token",
        sleep=sleep,
    )

    await transport.async_start(AsyncMock())
    await websocket.waiting_for_message.wait()
    await wait_for_sleep_calls(sleep, 1)
    sleep.release.set()
    await wait_for_sleep_calls(sleep, 2)

    assert [message["method"] for message in websocket.sent_json] == [
        "subscribe",
        "heartbeat",
    ]
    assert websocket.sent_json[1]["id"] == 2
    assert "params" not in websocket.sent_json[1]

    await transport.async_stop()
    sleep.release.set()
    await asyncio.sleep(0)

    assert [message["method"] for message in websocket.sent_json] == [
        "subscribe",
        "heartbeat",
    ]
    assert websocket.closed is True


@pytest.mark.asyncio
async def test_push_transport_stop_closes_opened_websocket_once() -> None:
    """stop 只关闭已打开 websocket，重复调用保持幂等."""
    websocket = FakeWebSocket([])
    session = FakeSession(websocket)
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="fake-token",
    )

    await transport.async_start(AsyncMock())
    await transport.async_stop()
    await transport.async_stop()

    assert websocket.closed is True


@pytest.mark.asyncio
async def test_push_transport_start_is_idempotent_while_open() -> None:
    """transport 已打开时重复 start 不应重连或替换 callback."""
    websocket = OpenFakeWebSocket()
    session = FakeSession(websocket)
    first_callback = AsyncMock()
    second_callback = AsyncMock()
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="fake-token",
    )

    await transport.async_start(first_callback)
    await websocket.waiting_for_message.wait()
    await transport.async_start(second_callback)
    await transport.async_stop()

    assert session.connected_urls == ["wss://push.yeelight.com/ws/fake-token"]
    assert [message["method"] for message in websocket.sent_json] == ["subscribe"]


@pytest.mark.asyncio
async def test_push_transport_rejects_empty_token_before_connect() -> None:
    """空 token 在 URL helper 边界拒绝，不能调用 ws_connect."""
    websocket = FakeWebSocket([])
    session = FakeSession(websocket)
    transport = YeelightPushWebSocketTransport(session=session, token="Bearer")

    with pytest.raises(ValueError, match="push token is required"):
        await transport.async_start(AsyncMock())

    assert session.connected_urls == []


@pytest.mark.asyncio
async def test_push_transport_ignores_control_ack_frames() -> None:
    """订阅/心跳 ACK 不能进入 coordinator payload 计数。"""
    websocket = FakeWebSocket([
        FakeMessage(WSMsgType.TEXT, '{"method":"subscribe","code":"200"}'),
        FakeMessage(WSMsgType.TEXT, '{"method":"heartbeat","success":true}'),
        FakeMessage(WSMsgType.TEXT, '{"result":true,"timestamp":"secret-time"}'),
        FakeMessage(
            WSMsgType.TEXT,
            (
                '{"data":{"deviceId":"device-secret"},"msgId":"message-secret",'
                '"result":{"success":true},"timestamp":"secret-time"}'
            ),
        ),
    ])
    session = FakeSession(websocket)
    callback = AsyncMock()
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="fake-token",
        auto_reconnect=False,
    )

    await transport.async_start(callback)
    await asyncio.sleep(0)
    await transport.async_stop()

    callback.assert_not_awaited()
