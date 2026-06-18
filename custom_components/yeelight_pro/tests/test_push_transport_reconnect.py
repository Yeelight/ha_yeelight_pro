"""Reconnect and endpoint tests for the Yeelight Pro WebSocket push transport."""

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
    FakeSession,
    FakeMessage,
    FakeWebSocket,
    OpenFakeWebSocket,
    wait_for_sleep_calls,
)


@pytest.mark.asyncio
async def test_push_transport_uses_private_base_url_override() -> None:
    """私有部署 transport 应连接派生出的私有 WebSocket endpoint."""
    websocket = OpenFakeWebSocket()
    session = FakeSession(websocket)
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="fake-token",
        base_url="wss://private.example/ws",
    )

    await transport.async_start(AsyncMock())
    await transport.async_stop()

    assert session.connected_urls == ["wss://private.example/ws/fake-token"]


@pytest.mark.asyncio
async def test_push_transport_passes_bounded_connect_timeout() -> None:
    """WebSocket 初始连接必须有超时，避免 HA setup 被握手长时间阻塞."""

    class TimeoutAwareSession:
        def __init__(self) -> None:
            self.calls: list[tuple[str, float | None]] = []

        async def ws_connect(
            self,
            url: str,
            *,
            timeout: float | None = None,
            proxy: str | None = None,
            **kwargs: object,
        ) -> OpenFakeWebSocket:
            self.calls.append((url, timeout))
            return OpenFakeWebSocket()

    session = TimeoutAwareSession()
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="fake-token",
        connect_timeout_seconds=3,
    )

    await transport.async_start(AsyncMock())
    await transport.async_stop()

    assert session.calls == [("wss://push.yeelight.com/ws/fake-token", 3)]


@pytest.mark.asyncio
async def test_push_transport_clears_recoverable_start_error_after_reconnect() -> None:
    """后台重连成功后不应继续暴露旧的初始连接错误。"""
    reconnect_sleep = ControlledSleep()
    websocket = OpenFakeWebSocket()
    session = FakeSession([OSError("token-secret"), websocket])
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="fake-token",
        reconnect_sleep=reconnect_sleep,
    )

    await transport.async_start(AsyncMock())
    assert transport.last_start_error_type == "OSError"

    await wait_for_sleep_calls(reconnect_sleep, 1)
    reconnect_sleep.release.set()
    await websocket.waiting_for_message.wait()

    assert transport.last_start_error_type is None

    await transport.async_stop()


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
async def test_push_transport_uses_fresh_token_provider_on_reconnect() -> None:
    """OAuth 刷新后，WebSocket 重连应使用 token provider 返回的新 token。"""
    reconnect_sleep = ControlledSleep()
    first_websocket = FakeWebSocket([])
    second_websocket = OpenFakeWebSocket()
    tokens = ["initial-token", "fresh-token"]

    def token_provider() -> str:
        return tokens[0]

    session = FakeSession([first_websocket, second_websocket])
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="fallback-token",
        token_provider=token_provider,
        reconnect_sleep=reconnect_sleep,
    )

    await transport.async_start(AsyncMock())
    await asyncio.sleep(0)
    tokens[0] = "fresh-token"
    await wait_for_sleep_calls(reconnect_sleep, 1)
    reconnect_sleep.release.set()
    await second_websocket.waiting_for_message.wait()
    await transport.async_stop()

    assert session.connected_urls == [
        "wss://push.yeelight.com/ws/initial-token",
        "wss://push.yeelight.com/ws/fresh-token",
    ]


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
    assert transport.last_runtime_error_type is None


@pytest.mark.asyncio
async def test_push_transport_keeps_backoff_after_unstable_short_connections() -> None:
    """短连断开且未收到任何帧时不应重置退避，避免故障端点重连过密。"""
    reconnect_sleep = ControlledSleep()
    first_websocket = FakeWebSocket([])
    second_websocket = FakeWebSocket([])
    third_websocket = OpenFakeWebSocket()
    session = FakeSession([first_websocket, second_websocket, third_websocket])
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
    await third_websocket.waiting_for_message.wait()
    await transport.async_stop()

    assert reconnect_sleep.delays == [1.0, 2.0]
    assert len(session.connected_urls) == 3
    assert [message["method"] for message in third_websocket.sent_json] == [
        "subscribe"
    ]


@pytest.mark.asyncio
async def test_push_transport_keeps_backoff_after_short_snapshot_then_close() -> None:
    """订阅快照后立即关闭仍属不稳定短连，不能把退避重置回 1 秒。"""
    reconnect_sleep = ControlledSleep()
    snapshot = FakeMessage(
        WSMsgType.TEXT,
        '{"result":"ok","data":{"method":"subscribe","devices":[]}}',
    )
    first_websocket = FakeWebSocket([snapshot])
    second_websocket = FakeWebSocket([snapshot])
    third_websocket = OpenFakeWebSocket()
    session = FakeSession([first_websocket, second_websocket, third_websocket])
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
    await third_websocket.waiting_for_message.wait()
    await transport.async_stop()

    assert reconnect_sleep.delays == [1.0, 2.0]
    assert len(session.connected_urls) == 3


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
    assert transport.health.as_dict()["connect_attempts"] == 1
    await wait_for_sleep_calls(reconnect_sleep, 1)
    reconnect_sleep.release.set()
    await websocket.waiting_for_message.wait()
    health = transport.health.as_dict()
    assert health["connect_attempts"] == 2
    assert health["connected_count"] == 1
    assert health["reconnect_attempts"] == 1
    assert health["last_start_error_type"] is None
    await transport.async_stop()

    assert reconnect_sleep.delays == [1.0]
    assert session.connected_urls == [
        "wss://push.yeelight.com/ws/fake-token",
        "wss://push.yeelight.com/ws/fake-token",
    ]
    assert [message["method"] for message in websocket.sent_json] == ["subscribe"]
