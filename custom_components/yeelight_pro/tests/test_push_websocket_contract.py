"""WebSocket-only event notification contract tests."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

from aiohttp import WSMsgType
import pytest

from custom_components.yeelight_pro.push_contract import (
    DEFAULT_PUSH_BASE_URL,
    PUSH_CONTROL_METHODS,
    PUSH_DATA_TYPES,
    PUSH_EVENT_NOTIFICATION_TRANSPORT,
    PushMessageBuilder,
    build_push_url,
)
from custom_components.yeelight_pro.push_transport import (
    YeelightPushWebSocketTransport,
)

from .push_transport_helpers import FakeMessage, FakeSession, FakeWebSocket


def test_yeelight_event_notifications_use_websocket_url_contract() -> None:
    """易来事件通知只使用开放平台 WebSocket URL，不保留 SSE 入口。"""
    assert PUSH_EVENT_NOTIFICATION_TRANSPORT == "WebSocket"
    assert DEFAULT_PUSH_BASE_URL == "wss://push.yeelight.com/ws"
    assert build_push_url("Bearer fake-token") == (
        "wss://push.yeelight.com/ws/fake-token"
    )
    assert PUSH_CONTROL_METHODS == frozenset({"subscribe", "heartbeat"})
    assert PUSH_DATA_TYPES == frozenset({"prop", "event"})
    assert "sse" not in PUSH_DATA_TYPES
    assert "eventsource" not in PUSH_DATA_TYPES


def test_yeelight_websocket_subscribe_and_heartbeat_frames_match_docs() -> None:
    """订阅和心跳帧应匹配开放平台 3.3 文档。"""
    builder = PushMessageBuilder()

    assert builder.next_subscribe(timestamp=1722133937) == {
        "id": 1,
        "method": "subscribe",
        "params": {"type": 2},
        "timestamp": 1722133937,
        "version": "1.0",
    }
    assert builder.next_heartbeat(timestamp=1722133938) == {
        "id": 2,
        "method": "heartbeat",
        "timestamp": 1722133938,
        "version": "1.0",
    }


@pytest.mark.asyncio
async def test_websocket_transport_dispatches_only_documented_data_frames() -> None:
    """WebSocket transport 只分发文档中的 prop/event 数据帧。"""
    websocket = FakeWebSocket(
        [
            FakeMessage(WSMsgType.TEXT, '{"method":"subscribe","code":"200"}'),
            FakeMessage(WSMsgType.TEXT, '{"method":"heartbeat","success":true}'),
            FakeMessage(WSMsgType.TEXT, '{"type":"prop","nodes":[{"id":1}]}'),
            FakeMessage(WSMsgType.TEXT, '{"type":"event","nodes":[{"id":1}]}'),
            FakeMessage(WSMsgType.TEXT, '{"type":"eventsource","nodes":[{"id":1}]}'),
            FakeMessage(WSMsgType.TEXT, '{"type":"sse","nodes":[{"id":1}]}'),
            FakeMessage(WSMsgType.TEXT, '{"type":"unknown","nodes":[{"id":1}]}'),
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
    await transport.async_stop()

    assert [call.args[0]["type"] for call in callback.await_args_list] == [
        "prop",
        "event",
    ]


@pytest.mark.asyncio
async def test_websocket_transport_does_not_dispatch_polling_or_sse_events() -> None:
    """云端事件通知只能由 WebSocket prop/event 帧驱动，不接受 SSE/轮询伪帧。"""
    websocket = FakeWebSocket(
        [
            FakeMessage(WSMsgType.TEXT, '{"method":"subscribe","code":"200"}'),
            FakeMessage(WSMsgType.TEXT, '{"type":"polling","nodes":[{"id":1}]}'),
            FakeMessage(WSMsgType.TEXT, '{"type":"eventstream","nodes":[{"id":1}]}'),
            FakeMessage(WSMsgType.TEXT, '{"type":"server_sent","nodes":[{"id":1}]}'),
            FakeMessage(WSMsgType.TEXT, '{"type":"event","nodes":[{"id":1}]}'),
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
    await transport.async_stop()

    assert [call.args[0]["type"] for call in callback.await_args_list] == ["event"]
