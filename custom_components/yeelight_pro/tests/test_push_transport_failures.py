"""Failure cleanup tests for the Yeelight Pro WebSocket push transport."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

from aiohttp import WSServerHandshakeError, WSMsgType
import pytest

from custom_components.yeelight_pro.push_transport import (
    YeelightPushWebSocketTransport,
)

from .push_transport_helpers import (
    ClosedBeforeFirstFrameWebSocket,
    ControlledSleep,
    FailingCloseWebSocket,
    FailingHeartbeatWebSocket,
    FailingReaderWebSocket,
    FailingSubscribeWebSocket,
    FakeMessage,
    FakeSession,
    FakeWebSocket,
    HangingSubscribeWebSocket,
    OpenFakeWebSocket,
    wait_for_sleep_calls,
)


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
    assert health["first_frame_received"] is False
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
    await second_websocket.waiting_for_message.wait()
    await transport.async_stop()


@pytest.mark.asyncio
async def test_push_transport_does_not_suspend_after_repeated_abnormal_close_before_first_frame() -> None:
    """连续首帧前 1006 也不应长暂停，恢复应依赖 token 刷新和短退避。"""
    reconnect_sleep = ControlledSleep()
    websockets = [
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
async def test_push_transport_refreshes_token_after_abnormal_close_before_first_frame() -> None:
    """订阅阶段早期 1006 后应先刷新 token，再用新 token 重连。"""
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
    refresh_handler = AsyncMock(return_value="fresh-token")
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="old-token",
        token_refresh_handler=refresh_handler,
        reconnect_sleep=reconnect_sleep,
    )

    await transport.async_start(AsyncMock())
    await asyncio.sleep(0)
    await wait_for_sleep_calls(reconnect_sleep, 1)
    reconnect_sleep.release.set()
    await second_websocket.waiting_for_message.wait()

    health = transport.health.as_dict()
    refresh_handler.assert_awaited_once()
    assert session.connected_urls == [
        "wss://push.yeelight.com/ws/old-token",
        "wss://push.yeelight.com/ws/fresh-token",
    ]
    assert health["token_refresh_attempts"] == 1
    assert health["token_refresh_successes"] == 1
    assert health["last_token_refresh_error_type"] is None

    await transport.async_stop()


@pytest.mark.asyncio
async def test_push_transport_records_token_refresh_failure_after_early_close() -> None:
    """早期关闭后的 token refresh 失败只能记录聚合错误，不能泄露凭证。"""
    reconnect_sleep = ControlledSleep()
    first_websocket = ClosedBeforeFirstFrameWebSocket(
        close_code=1006,
        exception=ConnectionResetError("token-secret"),
    )
    second_websocket = OpenFakeWebSocket()
    session = FakeSession([first_websocket, second_websocket])
    refresh_handler = AsyncMock(side_effect=RuntimeError("token-secret"))
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="old-token",
        token_refresh_handler=refresh_handler,
        reconnect_sleep=reconnect_sleep,
    )

    await transport.async_start(AsyncMock())
    await asyncio.sleep(0)
    await wait_for_sleep_calls(reconnect_sleep, 1)
    reconnect_sleep.release.set()
    await wait_for_sleep_calls(reconnect_sleep, 2)

    health = transport.health.as_dict()
    refresh_handler.assert_awaited_once()
    assert session.connected_urls == [
        "wss://push.yeelight.com/ws/old-token",
        "wss://push.yeelight.com/ws/old-token",
    ]
    assert reconnect_sleep.delays == [1.0, 60.0]
    assert health["token_refresh_attempts"] == 1
    assert health["token_refresh_successes"] == 0
    assert health["last_token_refresh_error_type"] == "RuntimeError"
    assert "token-secret" not in str(health)

    reconnect_sleep.release.set()
    await third_websocket.waiting_for_message.wait()
    await transport.async_stop()


@pytest.mark.asyncio
async def test_push_transport_resets_abnormal_close_streak_after_first_frame() -> None:
    """收到任意首帧后应清零早期 1006 streak，避免正常重连被长暂停。"""
    websocket = FakeWebSocket([FakeMessage(WSMsgType.TEXT, '{"method":"subscribe","result":"ok"}')])
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


@pytest.mark.asyncio
async def test_push_transport_closes_websocket_when_subscribe_fails() -> None:
    """订阅帧发送失败时必须关闭半启动 websocket，且不泄漏后台任务."""
    websocket = FailingSubscribeWebSocket([])
    session = FakeSession(websocket)
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="fake-token",
        auto_reconnect=False,
    )

    with pytest.raises(ConnectionError):
        await transport.async_start(AsyncMock())

    assert [message["method"] for message in websocket.sent_json] == ["subscribe"]
    assert websocket.closed is True
    assert transport.health.as_dict()["last_disconnect_reason"] == "subscribe_failed"


@pytest.mark.asyncio
async def test_push_transport_subscribe_timeout_schedules_reconnect() -> None:
    """订阅发送卡住时不阻塞 HA setup，应关闭连接并后台退避重连。"""
    reconnect_sleep = ControlledSleep()
    hanging_websocket = HangingSubscribeWebSocket()
    reconnect_websocket = OpenFakeWebSocket()
    session = FakeSession([hanging_websocket, reconnect_websocket])
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="fake-token",
        reconnect_sleep=reconnect_sleep,
        connect_timeout_seconds=0.01,
    )

    await transport.async_start(AsyncMock())

    assert transport.last_start_error_type == "TimeoutError"
    assert [message["method"] for message in hanging_websocket.sent_json] == [
        "subscribe"
    ]
    assert hanging_websocket.closed is True

    await wait_for_sleep_calls(reconnect_sleep, 1)
    reconnect_sleep.release.set()
    await reconnect_websocket.waiting_for_message.wait()
    await transport.async_stop()

    assert session.connected_urls == [
        "wss://push.yeelight.com/ws/fake-token",
        "wss://push.yeelight.com/ws/fake-token",
    ]
    assert [message["method"] for message in reconnect_websocket.sent_json] == [
        "subscribe"
    ]


@pytest.mark.asyncio
async def test_push_transport_records_handshake_status_without_endpoint() -> None:
    """WebSocket 握手失败时只记录聚合状态码，不暴露 URL/token/header."""
    reconnect_sleep = ControlledSleep()
    session = FakeSession(
        WSServerHandshakeError(None, (), status=403, message="token-secret")
    )
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="fake-token",
        reconnect_sleep=reconnect_sleep,
    )

    await transport.async_start(AsyncMock())

    health = transport.health.as_dict()
    assert transport.last_start_error_type == "WSServerHandshakeError"
    assert health["last_handshake_status"] == 403
    assert health["last_disconnect_reason"] == "handshake_failed"
    assert "token-secret" not in str(health)

    await transport.async_stop()


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
async def test_push_transport_methodless_result_error_closes_websocket() -> None:
    """生产 result-only 错误控制帧应关闭连接，且不分发到 coordinator。"""
    websocket = FakeWebSocket([
        FakeMessage(
            WSMsgType.TEXT,
            (
                '{"data":{"detail":"device-secret"},"msgId":"message-secret",'
                '"result":{"code":"401","message":"token-secret"},'
                '"timestamp":"secret-time"}'
            ),
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
    assert transport.health.as_dict()["last_disconnect_reason"] == (
        "background_failure"
    )
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
    assert transport.health.as_dict()["last_disconnect_reason"] == (
        "reader_exception"
    )
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
    assert transport.health.as_dict()["last_disconnect_reason"] == (
        "reader_exception"
    )
    assert "token-secret" not in str(transport.last_runtime_error_type)

    await transport.async_stop()

    assert websocket.closed is True
