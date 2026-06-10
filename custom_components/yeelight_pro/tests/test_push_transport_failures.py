"""Failure cleanup tests for the Yeelight Pro WebSocket push transport."""

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
    FailingCloseWebSocket,
    FailingHeartbeatWebSocket,
    FailingReaderWebSocket,
    FailingSubscribeWebSocket,
    FakeMessage,
    FakeSession,
    FakeWebSocket,
    wait_for_sleep_calls,
)


@pytest.mark.asyncio
async def test_push_transport_closes_websocket_when_subscribe_fails() -> None:
    """订阅帧发送失败时必须关闭半启动 websocket，且不泄漏后台任务."""
    websocket = FailingSubscribeWebSocket([])
    session = FakeSession(websocket)
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="fake-token",
    )

    with pytest.raises(ConnectionError):
        await transport.async_start(AsyncMock())

    assert [message["method"] for message in websocket.sent_json] == ["subscribe"]
    assert websocket.closed is True


@pytest.mark.asyncio
async def test_push_transport_control_error_frame_closes_websocket() -> None:
    """服务器返回订阅错误控制帧时应关闭并只保留聚合错误类型。"""
    websocket = FakeWebSocket([
        FakeMessage(
            WSMsgType.TEXT,
            '{"method":"subscribe","code":"401","msg":"token-secret device-secret"}',
        )
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

    assert transport.last_runtime_error_type == "PushControlFrameError"
    callback.assert_not_awaited()
    assert websocket.closed is True

    await transport.async_stop()

    assert websocket.closed is True


@pytest.mark.asyncio
async def test_push_transport_stop_failure_keeps_websocket_for_retry() -> None:
    """websocket close 失败后必须保留引用，允许下一次 stop 重试关闭."""
    websocket = FailingCloseWebSocket()
    session = FakeSession(websocket)
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="fake-token",
    )

    await transport.async_start(AsyncMock())
    await websocket.waiting_for_message.wait()

    with pytest.raises(OSError):
        await transport.async_stop()

    assert websocket.close_attempts == 1
    assert websocket.closed is False

    await transport.async_stop()

    assert websocket.close_attempts == 2
    assert websocket.closed is True


@pytest.mark.asyncio
async def test_push_transport_heartbeat_failure_closes_websocket() -> None:
    """heartbeat 发送失败后应关闭 websocket 并清理后台 reader task."""
    sleep = ControlledSleep()
    websocket = FailingHeartbeatWebSocket()
    session = FakeSession(websocket)
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="fake-token",
        sleep=sleep,
        auto_reconnect=False,
    )

    await transport.async_start(AsyncMock())
    await websocket.waiting_for_message.wait()
    await wait_for_sleep_calls(sleep, 1)
    sleep.release.set()
    await asyncio.wait_for(websocket.closed_event.wait(), timeout=1)

    assert [message["method"] for message in websocket.sent_json] == [
        "subscribe",
        "heartbeat",
    ]
    assert websocket.closed is True
    assert transport.last_runtime_error_type == "OSError"
    assert "token-secret" not in str(transport.last_runtime_error_type)

    await transport.async_stop()

    assert websocket.closed is True


@pytest.mark.asyncio
async def test_push_transport_reader_failure_closes_websocket() -> None:
    """reader 后台失败时应关闭 websocket、取消 heartbeat 并吞掉异常."""
    sleep = ControlledSleep()
    websocket = FailingReaderWebSocket()
    session = FakeSession(websocket)
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="fake-token",
        sleep=sleep,
        auto_reconnect=False,
    )

    await transport.async_start(AsyncMock())
    await websocket.reader_started.wait()
    await asyncio.wait_for(websocket.closed_event.wait(), timeout=1)
    sleep.release.set()
    await asyncio.sleep(0)

    assert [message["method"] for message in websocket.sent_json] == ["subscribe"]
    assert websocket.closed is True
    assert transport.last_runtime_error_type == "OSError"
    assert "token-secret" not in str(transport.last_runtime_error_type)

    await transport.async_stop()

    assert websocket.closed is True


@pytest.mark.asyncio
async def test_push_transport_callback_failure_closes_websocket() -> None:
    """payload callback 后台失败时也应关闭 websocket 并清理 heartbeat."""
    sleep = ControlledSleep()
    websocket = FakeWebSocket(
        [FakeMessage(WSMsgType.TEXT, '{"type":"prop","nodes":[{"id":1}]}')]
    )
    session = FakeSession(websocket)
    callback = AsyncMock(side_effect=RuntimeError("token-secret"))
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="fake-token",
        sleep=sleep,
        auto_reconnect=False,
    )

    await transport.async_start(callback)
    await asyncio.sleep(0)
    sleep.release.set()
    await asyncio.sleep(0)

    callback.assert_awaited_once()
    assert websocket.closed is True
    assert transport.last_runtime_error_type == "RuntimeError"
    assert "token-secret" not in str(transport.last_runtime_error_type)

    await transport.async_stop()

    assert websocket.closed is True
