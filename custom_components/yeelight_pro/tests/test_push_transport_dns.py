"""DNS fallback tests for the Yeelight Pro WebSocket transport."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from custom_components.yeelight_pro import push_transport_dns
from custom_components.yeelight_pro import push_transport_connection
from custom_components.yeelight_pro.push_transport import (
    YeelightPushWebSocketTransport,
)

from .push_transport_helpers import FakeSession, OpenFakeWebSocket


@pytest.mark.asyncio
async def test_fake_ip_detection_matches_clash_docker_range() -> None:
    """fake-ip 检测只覆盖 Clash/Docker 常见 198.18.0.0/15 网段。"""
    assert push_transport_dns.is_fake_ip_address("198.18.0.8") is True
    assert push_transport_dns.is_fake_ip_address("198.19.255.254") is True
    assert push_transport_dns.is_fake_ip_address("198.20.0.1") is False
    assert push_transport_dns.is_fake_ip_address("203.0.113.8") is False
    assert push_transport_dns.is_fake_ip_address("ws-test.yeedev.com") is False


@pytest.mark.asyncio
async def test_push_transport_uses_real_ip_fallback_for_wss_fake_ip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """wss fake-ip fallback 应直连真实 IP，并保留原 Host 与 SNI。"""
    websocket = OpenFakeWebSocket()
    session = FakeSession(websocket)
    monkeypatch.setattr(
        push_transport_connection,
        "websocket_ip_fallback",
        push_transport_dns.websocket_ip_fallback,
    )
    monkeypatch.setattr(
        push_transport_dns, "resolve_host_ips", AsyncMock(return_value=["198.18.0.8"])
    )
    monkeypatch.setattr(
        push_transport_dns,
        "resolve_public_dns_ips",
        AsyncMock(return_value=["47.100.10.20"]),
    )
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="fake-token",
        base_url="wss://ws-test.yeedev.com/ws",
        enable_ip_fallback=True,
    )

    await transport.async_start(AsyncMock())
    await websocket.waiting_for_message.wait()

    assert session.connected_urls == ["wss://47.100.10.20/ws/fake-token"]
    assert session.connected_kwargs == [
        {
            "timeout": 10,
            "proxy": None,
            "headers": {"Host": "ws-test.yeedev.com"},
            "server_hostname": "ws-test.yeedev.com",
        }
    ]

    await transport.async_stop()


@pytest.mark.asyncio
async def test_push_transport_uses_real_ip_fallback_for_ws_fake_ip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ws fake-ip fallback 应只保留 Host，不传 TLS SNI。"""
    websocket = OpenFakeWebSocket()
    session = FakeSession(websocket)
    monkeypatch.setattr(
        push_transport_connection,
        "websocket_ip_fallback",
        push_transport_dns.websocket_ip_fallback,
    )
    monkeypatch.setattr(
        push_transport_dns, "resolve_host_ips", AsyncMock(return_value=["198.18.0.9"])
    )
    monkeypatch.setattr(
        push_transport_dns,
        "resolve_public_dns_ips",
        AsyncMock(return_value=["47.100.10.21"]),
    )
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="fake-token",
        base_url="ws://ws-test.yeedev.com:8080/ws",
        enable_ip_fallback=True,
    )

    await transport.async_start(AsyncMock())
    await websocket.waiting_for_message.wait()

    assert session.connected_urls == ["ws://47.100.10.21:8080/ws/fake-token"]
    assert session.connected_kwargs == [
        {
            "timeout": 10,
            "proxy": None,
            "headers": {"Host": "ws-test.yeedev.com:8080"},
        }
    ]

    await transport.async_stop()


@pytest.mark.asyncio
async def test_push_transport_keeps_normal_dns_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """非 fake-ip DNS 不应改写 WebSocket 连接 URL。"""
    websocket = OpenFakeWebSocket()
    session = FakeSession(websocket)
    public_resolver = AsyncMock(return_value=["47.100.10.20"])
    monkeypatch.setattr(
        push_transport_connection,
        "websocket_ip_fallback",
        push_transport_dns.websocket_ip_fallback,
    )
    monkeypatch.setattr(
        push_transport_dns,
        "resolve_host_ips",
        AsyncMock(return_value=["47.100.10.20"]),
    )
    monkeypatch.setattr(push_transport_dns, "resolve_public_dns_ips", public_resolver)
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="fake-token",
        base_url="wss://ws-test.yeedev.com/ws",
        enable_ip_fallback=True,
    )

    await transport.async_start(AsyncMock())
    await websocket.waiting_for_message.wait()

    assert session.connected_urls == ["wss://ws-test.yeedev.com/ws/fake-token"]
    assert session.connected_kwargs == [{"timeout": 10, "proxy": None}]
    public_resolver.assert_not_awaited()

    await transport.async_stop()


@pytest.mark.asyncio
async def test_explicit_proxy_skips_real_ip_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """显式 private_push_proxy 优先，不能再触发真实 IP fallback。"""
    websocket = OpenFakeWebSocket()
    session = FakeSession(websocket)
    local_resolver = AsyncMock(return_value=["198.18.0.8"])
    monkeypatch.setattr(
        push_transport_connection,
        "websocket_ip_fallback",
        push_transport_dns.websocket_ip_fallback,
    )
    monkeypatch.setattr(push_transport_dns, "resolve_host_ips", local_resolver)
    transport = YeelightPushWebSocketTransport(
        session=session,
        token="fake-token",
        base_url="wss://ws-test.yeedev.com/ws",
        proxy="http://host.docker.internal:7890",
        enable_ip_fallback=True,
    )

    await transport.async_start(AsyncMock())
    await websocket.waiting_for_message.wait()

    assert session.connected_urls == ["wss://ws-test.yeedev.com/ws/fake-token"]
    assert session.connected_kwargs == [
        {"timeout": 10, "proxy": "http://host.docker.internal:7890"}
    ]
    local_resolver.assert_not_awaited()

    await transport.async_stop()
