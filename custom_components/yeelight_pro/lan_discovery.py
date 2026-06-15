"""UDP discovery runtime for Yeelight Pro local gateways."""
from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from .lan_contract import (
    LAN_DISCOVERY_MESSAGE,
    LAN_DISCOVERY_PORT,
    LanDiscoveryResponse,
    parse_discovery_response,
)
from .lan_methods import LAN_DEVICE_DISCOVERY_MESSAGE

LAN_DISCOVERY_TIMEOUT_SECONDS = 3.0
LAN_DISCOVERY_BROADCAST_HOST = "255.255.255.255"
LAN_DISCOVERY_MESSAGES = (
    LAN_DISCOVERY_MESSAGE,
    LAN_DEVICE_DISCOVERY_MESSAGE,
)


class LanDatagramTransport(Protocol):
    """Subset of asyncio DatagramTransport used by discovery."""

    def sendto(self, data: bytes, addr: tuple[str, int]) -> None:
        """Send one datagram."""

    def close(self) -> None:
        """Close the UDP transport."""


OpenDatagramEndpoint = Callable[..., Any]


@dataclass(slots=True)
class LanDiscoveryProtocol(asyncio.DatagramProtocol):
    """Collect the first valid Yeelight Pro discovery response."""

    loop: asyncio.AbstractEventLoop
    discovery_messages: tuple[str, ...] = LAN_DISCOVERY_MESSAGES
    response: asyncio.Future[LanDiscoveryResponse] = field(init=False)
    transport: LanDatagramTransport | None = None

    def __post_init__(self) -> None:
        """Create the response future on the owning event loop."""
        self.response = self.loop.create_future()

    def connection_made(self, transport: Any) -> None:
        """Keep the UDP transport and send the documented broadcast request."""
        self.transport = transport
        for message in self.discovery_messages:
            transport.sendto(
                message.encode("utf-8"),
                (LAN_DISCOVERY_BROADCAST_HOST, LAN_DISCOVERY_PORT),
            )

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        """Parse one discovery response datagram."""
        if self.response.done():
            return
        try:
            payload = data.decode("utf-8")
            discovered = parse_discovery_response(payload)
        except (UnicodeDecodeError, ValueError):
            return
        self.response.set_result(discovered)

    def error_received(self, exc: Exception) -> None:
        """Surface UDP socket errors to the waiter without payload details."""
        if not self.response.done():
            self.response.set_exception(exc)


@dataclass(slots=True)
class LanDiscoveryMultiProtocol(asyncio.DatagramProtocol):
    """Collect multiple Yeelight Pro discovery responses within a timeout."""

    discovery_messages: tuple[str, ...] = LAN_DISCOVERY_MESSAGES
    responses: list[LanDiscoveryResponse] = field(default_factory=list)
    transport: LanDatagramTransport | None = None

    def connection_made(self, transport: Any) -> None:
        """Keep the UDP transport and send the documented broadcast request."""
        self.transport = transport
        for message in self.discovery_messages:
            transport.sendto(
                message.encode("utf-8"),
                (LAN_DISCOVERY_BROADCAST_HOST, LAN_DISCOVERY_PORT),
            )

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        """Parse and collect one discovery response datagram."""
        try:
            payload = data.decode("utf-8")
            discovered = parse_discovery_response(payload)
        except (UnicodeDecodeError, ValueError):
            return
        # 按 IP 去重
        if not any(r.ip == discovered.ip for r in self.responses):
            self.responses.append(discovered)

    def error_received(self, exc: Exception) -> None:
        """Ignore UDP errors during multi-discovery."""


async def async_discover_lan_gateway(
    *,
    timeout_seconds: float = LAN_DISCOVERY_TIMEOUT_SECONDS,
    open_datagram_endpoint: OpenDatagramEndpoint | None = None,
) -> LanDiscoveryResponse | None:
    """Discover one local gateway via the documented UDP broadcast."""
    loop = asyncio.get_running_loop()
    endpoint = open_datagram_endpoint or loop.create_datagram_endpoint
    protocol = LanDiscoveryProtocol(loop)
    transport: LanDatagramTransport | None = None
    try:
        transport, _ = await endpoint(
            lambda: protocol,
            local_addr=("0.0.0.0", 0),
            allow_broadcast=True,
        )
        return await asyncio.wait_for(protocol.response, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        return None
    finally:
        active_transport = transport or protocol.transport
        if active_transport is not None:
            active_transport.close()


async def async_discover_all_lan_gateways(
    *,
    timeout_seconds: float = LAN_DISCOVERY_TIMEOUT_SECONDS,
    open_datagram_endpoint: OpenDatagramEndpoint | None = None,
) -> list[LanDiscoveryResponse]:
    """Discover all local gateways via the documented UDP broadcast."""
    loop = asyncio.get_running_loop()
    endpoint = open_datagram_endpoint or loop.create_datagram_endpoint
    protocol = LanDiscoveryMultiProtocol()
    transport: LanDatagramTransport | None = None
    try:
        transport, _ = await endpoint(
            lambda: protocol,
            local_addr=("0.0.0.0", 0),
            allow_broadcast=True,
        )
        await asyncio.sleep(timeout_seconds)
        return list(protocol.responses)
    finally:
        active_transport = transport or protocol.transport
        if active_transport is not None:
            active_transport.close()


__all__ = [
    "LAN_DISCOVERY_BROADCAST_HOST",
    "LAN_DISCOVERY_MESSAGES",
    "LAN_DISCOVERY_TIMEOUT_SECONDS",
    "LanDatagramTransport",
    "LanDiscoveryProtocol",
    "OpenDatagramEndpoint",
    "async_discover_all_lan_gateways",
    "async_discover_lan_gateway",
]
