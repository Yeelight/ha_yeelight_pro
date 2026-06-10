"""Tests for the Yeelight Pro WebSocket push transport."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

from aiohttp import WSMsgType
import pytest

from custom_components.yeelight_pro.push_contract import (
    PUSH_HEARTBEAT_INTERVAL_SECONDS,
)
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
    assert callback.await_args_list[1].args[0] == {"type": "event", "nodes": []}
    assert callback.await_count == 2

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

    assert sleep.delays == [PUSH_HEARTBEAT_INTERVAL_SECONDS]
    assert [message["method"] for message in websocket.sent_json] == ["subscribe"]

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
async def test_push_transport_reconnects_after_reader_finishes() -> None:
    """有限流 reader 结束后应按退避策略自动重连并重新订阅."""
    reconnect_sleep = ControlledSleep()
    first_websocket = FakeWebSocket([])
    second_websocket = OpenFakeWebSocket()
    session = FakeSession([first_websocket, second_websocket])
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="fake-token",
        reconnect_sleep=reconnect_sleep,
    )

    await transport.async_start(AsyncMock())
    await asyncio.sleep(0)
    await wait_for_sleep_calls(reconnect_sleep, 1)
    reconnect_sleep.release.set()
    await second_websocket.waiting_for_message.wait()
    await transport.async_stop()

    assert session.connected_urls == [
        "wss://push.yeelight.com/ws/fake-token",
        "wss://push.yeelight.com/ws/fake-token",
    ]
    assert [message["method"] for message in first_websocket.sent_json] == [
        "subscribe"
    ]
    assert [message["method"] for message in second_websocket.sent_json] == [
        "subscribe"
    ]
    assert second_websocket.sent_json[0]["id"] == 2


@pytest.mark.asyncio
async def test_push_transport_reconnect_backoff_retries_until_success() -> None:
    """重连失败时应继续退避重试，成功后重新发送 subscribe frame."""
    reconnect_sleep = ControlledSleep()
    first_websocket = FakeWebSocket([])
    second_websocket = OpenFakeWebSocket()
    session = FakeSession([
        first_websocket,
        OSError("token-secret"),
        second_websocket,
    ])
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="fake-token",
        reconnect_sleep=reconnect_sleep,
    )

    await transport.async_start(AsyncMock())
    await asyncio.sleep(0)
    await wait_for_sleep_calls(reconnect_sleep, 1)
    reconnect_sleep.release.set()
    await wait_for_sleep_calls(reconnect_sleep, 2)
    reconnect_sleep.release.set()
    await second_websocket.waiting_for_message.wait()
    await transport.async_stop()

    assert reconnect_sleep.delays == [1.0, 2.0]
    assert session.connected_urls == [
        "wss://push.yeelight.com/ws/fake-token",
        "wss://push.yeelight.com/ws/fake-token",
        "wss://push.yeelight.com/ws/fake-token",
    ]
    assert [message["method"] for message in second_websocket.sent_json] == [
        "subscribe"
    ]
    assert second_websocket.sent_json[0]["id"] == 2
    assert transport.last_runtime_error_type == "OSError"


@pytest.mark.asyncio
async def test_push_transport_initial_connect_failure_schedules_reconnect() -> None:
    """初始 WebSocket 网络失败不应阻塞 runtime，应后台退避重连."""
    reconnect_sleep = ControlledSleep()
    websocket = OpenFakeWebSocket()
    session = FakeSession([OSError("token-secret"), websocket])
    callback = AsyncMock()
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="fake-token",
        reconnect_sleep=reconnect_sleep,
    )

    await transport.async_start(callback)

    assert transport.last_start_error_type == "OSError"
    await wait_for_sleep_calls(reconnect_sleep, 1)
    reconnect_sleep.release.set()
    await websocket.waiting_for_message.wait()
    await transport.async_stop()

    assert reconnect_sleep.delays == [1.0]
    assert session.connected_urls == [
        "wss://push.yeelight.com/ws/fake-token",
        "wss://push.yeelight.com/ws/fake-token",
    ]
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
