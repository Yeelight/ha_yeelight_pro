"""Yeelight Pro LAN UDP discovery runtime tests."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from custom_components.yeelight_pro.lan_contract import (
    LAN_DISCOVERY_MESSAGE,
    LAN_DISCOVERY_PORT,
)
from custom_components.yeelight_pro.lan_discovery import (
    LAN_DISCOVERY_BROADCAST_HOST,
    LAN_DISCOVERY_MESSAGES,
    async_discover_lan_gateway,
)
from custom_components.yeelight_pro.lan_methods import LAN_DEVICE_DISCOVERY_MESSAGE


class FakeDatagramTransport:
    """Record UDP datagrams sent by discovery."""

    def __init__(self) -> None:
        self.sent: list[tuple[bytes, tuple[str, int]]] = []
        self.closed = False

    def sendto(self, data: bytes, addr: tuple[str, int]) -> None:
        """Record outgoing datagram."""
        self.sent.append((data, addr))

    def close(self) -> None:
        """Mark transport closed."""
        self.closed = True


@pytest.mark.asyncio
async def test_discover_lan_gateway_broadcasts_and_parses_first_response() -> None:
    """UDP discovery 应广播文档文本，并解析第一个合法响应。"""
    transport = FakeDatagramTransport()

    async def _open_endpoint(
        protocol_factory: Callable[[], Any],
        **kwargs: Any,
    ) -> tuple[FakeDatagramTransport, Any]:
        assert kwargs == {"local_addr": ("0.0.0.0", 0), "allow_broadcast": True}
        protocol = protocol_factory()
        protocol.connection_made(transport)
        protocol.datagram_received(
            b"pid:1\nmac:F8:24:41:00:23:A4\ndid:22535\nip:192.168.1.101",
            ("192.168.1.101", LAN_DISCOVERY_PORT),
        )
        return transport, protocol

    response = await async_discover_lan_gateway(
        open_datagram_endpoint=_open_endpoint
    )

    assert response is not None
    assert response.ip == "192.168.1.101"
    assert response.device_id == "22535"
    assert [item[0] for item in transport.sent] == [
        LAN_DISCOVERY_MESSAGE.encode("utf-8"),
        LAN_DEVICE_DISCOVERY_MESSAGE.encode("utf-8"),
    ]
    assert all(
        item[1] == (LAN_DISCOVERY_BROADCAST_HOST, LAN_DISCOVERY_PORT)
        for item in transport.sent
    )
    assert transport.closed is True


def test_lan_discovery_messages_cover_gateway_and_wifi_panel_docs() -> None:
    """自动发现应覆盖网关和 WiFi 全面屏两种文档广播文本。"""
    assert LAN_DISCOVERY_MESSAGES == (
        "YEELIGHT_GATEWAY_CONTROL_DISCOVER",
        "YEELIGHT_DEVICE_CONTROL_DISCOVER",
    )


@pytest.mark.asyncio
async def test_discover_lan_gateway_ignores_invalid_response_until_timeout() -> None:
    """无效 discovery 响应不能生成半可信 host。"""
    transport = FakeDatagramTransport()

    async def _open_endpoint(
        protocol_factory: Callable[[], Any],
        **kwargs: Any,
    ) -> tuple[FakeDatagramTransport, Any]:
        protocol = protocol_factory()
        protocol.connection_made(transport)
        protocol.datagram_received(b"pid:not-int", ("192.168.1.101", 1982))
        return transport, protocol

    response = await async_discover_lan_gateway(
        timeout_seconds=0.01,
        open_datagram_endpoint=_open_endpoint,
    )

    assert response is None
    assert transport.closed is True
