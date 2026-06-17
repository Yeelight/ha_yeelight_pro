"""Shared types for Yeelight Pro WebSocket push transport."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol

PushTransportPayloadCallback = Callable[[dict[str, Any]], Awaitable[object]]
PushSleep = Callable[[float], Awaitable[object]]


@dataclass(slots=True)
class PushTransportHealth:
    """Diagnostics-safe aggregate health for the WebSocket transport."""

    running: bool = False
    websocket_open: bool = False
    connect_attempts: int = 0
    connected_count: int = 0
    disconnected_count: int = 0
    reconnect_attempts: int = 0
    received_messages: int = 0
    decoded_json_messages: int = 0
    dispatched_payloads: int = 0
    ignored_messages: int = 0
    malformed_messages: int = 0
    control_frames: int = 0
    heartbeat_sent_count: int = 0
    last_start_error_type: str | None = None
    last_runtime_error_type: str | None = None
    last_payload_type: str | None = None
    last_message_at: float | None = None
    last_dispatched_at: float | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return an aggregate-only diagnostics payload."""
        return {
            "running": self.running,
            "websocket_open": self.websocket_open,
            "connect_attempts": self.connect_attempts,
            "connected_count": self.connected_count,
            "disconnected_count": self.disconnected_count,
            "reconnect_attempts": self.reconnect_attempts,
            "received_messages": self.received_messages,
            "decoded_json_messages": self.decoded_json_messages,
            "dispatched_payloads": self.dispatched_payloads,
            "ignored_messages": self.ignored_messages,
            "malformed_messages": self.malformed_messages,
            "control_frames": self.control_frames,
            "heartbeat_sent_count": self.heartbeat_sent_count,
            "last_start_error_type": self.last_start_error_type,
            "last_runtime_error_type": self.last_runtime_error_type,
            "last_payload_type": self.last_payload_type,
            "last_message_at": self.last_message_at,
            "last_dispatched_at": self.last_dispatched_at,
        }


class PushWebSocket(Protocol):
    """Small subset of aiohttp websocket behavior used by the transport."""

    async def send_json(self, data: dict[str, Any]) -> None:
        """Send a JSON frame."""

    async def close(self) -> None:
        """Close the websocket."""

    def __aiter__(self) -> Any:
        """Return the async iterator for incoming messages."""


class PushWebSocketSession(Protocol):
    """Small subset of aiohttp ClientSession used by the transport."""

    async def ws_connect(
        self,
        url: str,
        *,
        timeout: float | None = None,
    ) -> PushWebSocket:
        """Open a websocket connection."""


__all__ = [
    "PushSleep",
    "PushTransportHealth",
    "PushTransportPayloadCallback",
    "PushWebSocket",
    "PushWebSocketSession",
]
