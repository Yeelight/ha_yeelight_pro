"""Direct-connect tests for the Yeelight Pro push transport."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from custom_components.yeelight_pro.push_transport import (
    YeelightPushWebSocketTransport,
)

from .push_transport_helpers import FakeSession, OpenFakeWebSocket


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

    assert session.connected_kwargs == [{"timeout": 10}]
    health = transport.health.as_dict()
    assert "proxy_configured" not in health
    assert health["connect_attempts"] == 1


@pytest.mark.asyncio
async def test_push_transport_direct_connect_has_no_proxy_health_flags() -> None:
    """默认 WebSocket 路径只直连，不暴露代理状态。"""
    websocket = OpenFakeWebSocket()
    session = FakeSession(websocket)
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="fake-token",
    )

    await transport.async_start(AsyncMock())
    await websocket.waiting_for_message.wait()

    assert session.connected_kwargs == [{"timeout": 10}]
    health = transport.health.as_dict()
    assert "proxy_configured" not in health

    await transport.async_stop()
