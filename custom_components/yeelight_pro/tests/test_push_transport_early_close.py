"""Early-close diagnostics tests for the Yeelight Pro push transport."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

from aiohttp import WSMsgType
import pytest

from custom_components.yeelight_pro.push_transport import (
    YeelightPushWebSocketTransport,
)

from .push_transport_helpers import (
    ClosedBeforeFirstFrameWebSocket,
    ControlledSleep,
    FakeMessage,
    FakeSession,
    FakeWebSocket,
    OpenFakeWebSocket,
    wait_for_sleep_calls,
)

QueuedWebSocket = ClosedBeforeFirstFrameWebSocket | OpenFakeWebSocket


@pytest.mark.asyncio
async def test_push_transport_records_abnormal_close_before_first_frame() -> None:
    """101 后首帧前异常关闭必须进入诊断，避免被误判为状态应用延迟."""
    websocket = ClosedBeforeFirstFrameWebSocket(
        close_code=1006,
        exception=ConnectionResetError("token-secret"),
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
    assert health["received_messages"] == 0
    assert health["decoded_json_messages"] == 0
    assert health["dispatched_payloads"] == 0
    assert health["subscribe_sent_count"] == 1
    assert health["first_frame_received"] is False
    assert health["last_subscribe_error_type"] is None
    assert health["last_subscribe_sent_at"] is not None
    assert health["last_close_code"] == 1006
    assert health["last_close_exception_type"] == "ConnectionResetError"
    assert health["last_disconnect_reason"] == "abnormal_close_before_first_frame"
    assert health["pre_first_frame_abnormal_close_count"] == 1
    assert health["consecutive_pre_first_frame_abnormal_close_count"] == 1
    assert "token-secret" not in str(health)

    await transport.async_stop()


@pytest.mark.asyncio
async def test_push_transport_uses_long_backoff_after_abnormal_close_before_first_frame() -> None:
    """首帧前 1006 后按普通退避重连，不能进入长时间不可用状态。"""
    reconnect_sleep = ControlledSleep()
    first_websocket = ClosedBeforeFirstFrameWebSocket(
        close_code=1006,
        exception=ConnectionResetError("token-secret"),
    )
    second_websocket = ClosedBeforeFirstFrameWebSocket(
        close_code=1006,
        exception=ConnectionResetError("token-secret"),
    )
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

    assert reconnect_sleep.delays == [1.0]
    health = transport.health.as_dict()
    assert health["pre_first_frame_abnormal_close_count"] == 1
    assert health["consecutive_pre_first_frame_abnormal_close_count"] == 1
    assert health["reconnect_pending"] is True
    assert health["reconnect_suspended"] is False
    assert health["next_reconnect_delay"] == 1.0

    reconnect_sleep.release.set()
    await wait_for_sleep_calls(reconnect_sleep, 2)

    health = transport.health.as_dict()
    assert reconnect_sleep.delays == [1.0, 2.0]
    assert health["pre_first_frame_abnormal_close_count"] == 2
    assert health["consecutive_pre_first_frame_abnormal_close_count"] == 2
    assert health["next_reconnect_delay"] == 2.0

    await transport.async_stop()


@pytest.mark.asyncio
async def test_push_transport_does_not_suspend_after_repeated_abnormal_close_before_first_frame() -> None:
    """连续首帧前 1006 也只走普通有界退避，避免长时间不可用."""
    reconnect_sleep = ControlledSleep()
    websockets: list[QueuedWebSocket] = [
        ClosedBeforeFirstFrameWebSocket(
            close_code=1006,
            exception=ConnectionResetError("token-secret"),
        )
        for _ in range(3)
    ]
    websockets.append(OpenFakeWebSocket())
    session = FakeSession(websockets)
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="fake-token",
        reconnect_sleep=reconnect_sleep,
    )

    await transport.async_start(AsyncMock())
    await asyncio.sleep(0)
    for count in range(1, 4):
        await wait_for_sleep_calls(reconnect_sleep, count)
        if count < 3:
            reconnect_sleep.release.set()
            await asyncio.sleep(0)

    assert reconnect_sleep.delays == [1.0, 2.0, 4.0]
    health = transport.health.as_dict()
    assert health["pre_first_frame_abnormal_close_count"] == 3
    assert health["consecutive_pre_first_frame_abnormal_close_count"] == 3
    assert health["reconnect_pending"] is True
    assert health["reconnect_suspended"] is False
    assert health["next_reconnect_delay"] == 4.0

    await transport.async_stop()


@pytest.mark.asyncio
async def test_push_transport_keeps_existing_token_after_abnormal_close_before_first_frame() -> None:
    """订阅阶段早期 1006 不是 token refresh 信号，应直接按原 token 重连."""
    reconnect_sleep = ControlledSleep()
    first_websocket = ClosedBeforeFirstFrameWebSocket(
        close_code=1006,
        exception=ConnectionResetError("token-secret"),
    )
    second_websocket = OpenFakeWebSocket()
    session = FakeSession([first_websocket, second_websocket])
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="stable-token",
        reconnect_sleep=reconnect_sleep,
    )

    await transport.async_start(AsyncMock())
    await asyncio.sleep(0)
    await wait_for_sleep_calls(reconnect_sleep, 1)
    reconnect_sleep.release.set()
    await second_websocket.waiting_for_message.wait()

    health = transport.health.as_dict()
    assert session.connected_urls == [
        "wss://push.yeelight.com/ws/stable-token",
        "wss://push.yeelight.com/ws/stable-token",
    ]
    assert reconnect_sleep.delays == [1.0]
    assert health["pre_first_frame_abnormal_close_count"] == 1
    assert health["consecutive_pre_first_frame_abnormal_close_count"] == 1
    assert "token-secret" not in str(health)

    await transport.async_stop()


@pytest.mark.asyncio
async def test_push_transport_uses_bounded_backoff_after_repeated_early_close() -> None:
    """早期关闭重复发生时继续使用有界退避，不进入 60 秒固定等待."""
    reconnect_sleep = ControlledSleep()
    first_websocket = ClosedBeforeFirstFrameWebSocket(
        close_code=1006,
        exception=ConnectionResetError("token-secret"),
    )
    second_websocket = ClosedBeforeFirstFrameWebSocket(
        close_code=1006,
        exception=ConnectionResetError("token-secret"),
    )
    third_websocket = OpenFakeWebSocket()
    session = FakeSession([first_websocket, second_websocket, third_websocket])
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="stable-token",
        reconnect_sleep=reconnect_sleep,
    )

    await transport.async_start(AsyncMock())
    await asyncio.sleep(0)
    await wait_for_sleep_calls(reconnect_sleep, 1)
    reconnect_sleep.release.set()
    await wait_for_sleep_calls(reconnect_sleep, 2)

    health = transport.health.as_dict()
    assert session.connected_urls == [
        "wss://push.yeelight.com/ws/stable-token",
        "wss://push.yeelight.com/ws/stable-token",
    ]
    assert reconnect_sleep.delays == [1.0, 2.0]
    assert health["pre_first_frame_abnormal_close_count"] == 2
    assert health["consecutive_pre_first_frame_abnormal_close_count"] == 2
    assert "token-secret" not in str(health)

    reconnect_sleep.release.set()
    await third_websocket.waiting_for_message.wait()
    await transport.async_stop()


@pytest.mark.asyncio
async def test_push_transport_resets_abnormal_close_streak_after_first_frame() -> None:
    """收到任意首帧后应清零早期 1006 streak，避免正常重连被长暂停。"""
    websocket = FakeWebSocket([
        FakeMessage(WSMsgType.TEXT, '{"method":"subscribe","result":"ok"}')
    ])
    session = FakeSession(websocket)
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="fake-token",
        auto_reconnect=False,
    )
    transport.health.consecutive_pre_first_frame_abnormal_close_count = 2

    await transport.async_start(AsyncMock())
    await asyncio.sleep(0)

    health = transport.health.as_dict()
    assert health["first_frame_received"] is True
    assert health["consecutive_pre_first_frame_abnormal_close_count"] == 0

    await transport.async_stop()
