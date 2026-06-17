"""Shared types for Yeelight Pro WebSocket push transport."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol

PushTransportPayloadCallback = Callable[[dict[str, Any]], Awaitable[object]]
PushSleep = Callable[[float], Awaitable[object]]
PushTokenProvider = Callable[[], str]
PushTokenRefreshHandler = Callable[[], Awaitable[str | None]]


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
    token_refresh_attempts: int = 0
    token_refresh_successes: int = 0
    pre_first_frame_abnormal_close_count: int = 0
    consecutive_pre_first_frame_abnormal_close_count: int = 0
    reconnect_pending: bool = False
    reconnect_suspended: bool = False
    next_reconnect_delay: float | None = None
    last_start_error_type: str | None = None
    last_runtime_error_type: str | None = None
    last_handshake_status: int | None = None
    last_disconnect_reason: str | None = None
    last_close_code: int | None = None
    last_close_exception_type: str | None = None
    last_token_refresh_error_type: str | None = None
    first_frame_received: bool = False
    proxy_configured: bool = False
    last_payload_type: str | None = None
    last_ignored_reason: str | None = None
    last_ignored_payload_type: str | None = None
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
            "token_refresh_attempts": self.token_refresh_attempts,
            "token_refresh_successes": self.token_refresh_successes,
            "pre_first_frame_abnormal_close_count": (
                self.pre_first_frame_abnormal_close_count
            ),
            "consecutive_pre_first_frame_abnormal_close_count": (
                self.consecutive_pre_first_frame_abnormal_close_count
            ),
            "reconnect_pending": self.reconnect_pending,
            "reconnect_suspended": self.reconnect_suspended,
            "next_reconnect_delay": self.next_reconnect_delay,
            "last_start_error_type": self.last_start_error_type,
            "last_runtime_error_type": self.last_runtime_error_type,
            "last_handshake_status": self.last_handshake_status,
            "last_disconnect_reason": self.last_disconnect_reason,
            "last_close_code": self.last_close_code,
            "last_close_exception_type": self.last_close_exception_type,
            "last_token_refresh_error_type": self.last_token_refresh_error_type,
            "first_frame_received": self.first_frame_received,
            "proxy_configured": self.proxy_configured,
            "last_payload_type": self.last_payload_type,
            "last_ignored_reason": self.last_ignored_reason,
            "last_ignored_payload_type": self.last_ignored_payload_type,
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

    async def receive(self, timeout: float | None = None) -> Any:
        """Receive one message from the websocket."""


class PushWebSocketSession(Protocol):
    """Small subset of aiohttp ClientSession used by the transport."""

    async def ws_connect(
        self,
        url: str,
        *,
        timeout: float | None = None,
        proxy: str | None = None,
        **kwargs: Any,
    ) -> PushWebSocket:
        """Open a websocket connection."""


__all__ = [
    "PushSleep",
    "PushTokenRefreshHandler",
    "PushTokenProvider",
    "PushTransportHealth",
    "PushTransportPayloadCallback",
    "PushWebSocket",
    "PushWebSocketSession",
]
