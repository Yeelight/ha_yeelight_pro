"""Proxy and direct-connect tests for the Yeelight Pro push transport."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from custom_components.yeelight_pro.push_transport import (
    YeelightPushWebSocketTransport,
)

from .push_transport_helpers import FakeSession, OpenFakeWebSocket


@pytest.mark.asyncio
async def test_push_transport_passes_configured_proxy_to_ws_connect() -> None:
    """底层 transport 仍支持显式注入代理，供测试或高级调用方使用。"""
    websocket = OpenFakeWebSocket()
    session = FakeSession(websocket)
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="fake-token",
        proxy=" http://proxy.example:8080 ",
    )

    await transport.async_start(AsyncMock())
    await websocket.waiting_for_message.wait()

    assert session.connected_kwargs[0]["proxy"] == "http://proxy.example:8080"
    assert transport.health.as_dict()["proxy_configured"] is True

    await transport.async_stop()


@pytest.mark.asyncio
async def test_push_transport_does_not_try_implicit_proxy_fallback() -> None:
    """连接失败时不猜测宿主机代理端口，避免把环境问题伪装成配置项。"""
    session = FakeSession(OSError("network-secret"))
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="fake-token",
        auto_reconnect=False,
    )

    with pytest.raises(OSError):
        await transport.async_start(AsyncMock())

    assert session.connected_kwargs == [{"timeout": 10, "proxy": None}]
    health = transport.health.as_dict()
    assert health["proxy_configured"] is False
    assert health["connect_attempts"] == 1


@pytest.mark.asyncio
async def test_push_transport_uses_only_explicit_proxy() -> None:
    """显式代理仅由调用方注入，不存在内部候选端口。"""
    websocket = OpenFakeWebSocket()
    session = FakeSession(websocket)
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="fake-token",
        proxy="http://proxy.example:8080",
    )

    await transport.async_start(AsyncMock())
    await websocket.waiting_for_message.wait()

    assert session.connected_kwargs == [
        {"timeout": 10, "proxy": "http://proxy.example:8080"}
    ]
    health = transport.health.as_dict()
    assert health["proxy_configured"] is True

    await transport.async_stop()


@pytest.mark.asyncio
async def test_push_transport_direct_connect_has_no_proxy_health_flags() -> None:
    """默认 WebSocket 路径只直连，不暴露自动代理状态。"""
    websocket = OpenFakeWebSocket()
    session = FakeSession(websocket)
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="fake-token",
    )

    await transport.async_start(AsyncMock())
    await websocket.waiting_for_message.wait()

    assert session.connected_kwargs == [{"timeout": 10, "proxy": None}]
    health = transport.health.as_dict()
    assert health["proxy_configured"] is False

    await transport.async_stop()
