"""Shared types for Yeelight Pro WebSocket push transport."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol

PushTransportPayloadCallback = Callable[[dict[str, Any]], Awaitable[object]]
PushSleep = Callable[[float], Awaitable[object]]
PushTokenProvider = Callable[[], str]


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
    unsupported_messages: int = 0
    malformed_messages: int = 0
    control_frames: int = 0
    private_status_frames: int = 0
    private_status_non_success_frames: int = 0
    subscribe_sent_count: int = 0
    heartbeat_sent_count: int = 0
    pre_first_frame_abnormal_close_count: int = 0
    consecutive_pre_first_frame_abnormal_close_count: int = 0
    reconnect_pending: bool = False
    next_reconnect_delay: float | None = None
    last_start_error_type: str | None = None
    last_runtime_error_type: str | None = None
    last_handshake_status: int | None = None
    last_disconnect_reason: str | None = None
    last_subscribe_error_type: str | None = None
    last_close_code: int | None = None
    last_close_exception_type: str | None = None
    first_frame_received: bool = False
    last_control_method: str | None = None
    last_private_status_result: str | None = None
    last_private_status_reason: str | None = None
    last_subscribe_device_count: int | None = None
    last_subscribe_state_device_count: int | None = None
    last_subscribe_state_key_samples: tuple[str, ...] = ()
    last_subscribe_node_hash_samples: tuple[str, ...] = ()
    last_subscribe_node_candidate_hash_samples: tuple[tuple[str, ...], ...] = ()
    last_data_node_hash_samples: tuple[str, ...] = ()
    last_data_node_candidate_hash_samples: tuple[tuple[str, ...], ...] = ()
    recent_data_node_hash_samples: tuple[str, ...] = ()
    recent_data_node_candidate_hash_samples: tuple[tuple[str, ...], ...] = ()
    last_payload_type: str | None = None
    last_ignored_reason: str | None = None
    last_ignored_payload_type: str | None = None
    last_unsupported_payload_shape: dict[str, Any] | None = None
    last_subscribe_sent_at: float | None = None
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
            "unsupported_messages": self.unsupported_messages,
            "malformed_messages": self.malformed_messages,
            "control_frames": self.control_frames,
            "private_status_frames": self.private_status_frames,
            "private_status_non_success_frames": (
                self.private_status_non_success_frames
            ),
            "subscribe_sent_count": self.subscribe_sent_count,
            "heartbeat_sent_count": self.heartbeat_sent_count,
            "pre_first_frame_abnormal_close_count": (
                self.pre_first_frame_abnormal_close_count
            ),
            "consecutive_pre_first_frame_abnormal_close_count": (
                self.consecutive_pre_first_frame_abnormal_close_count
            ),
            "reconnect_pending": self.reconnect_pending,
            "next_reconnect_delay": self.next_reconnect_delay,
            "last_start_error_type": self.last_start_error_type,
            "last_runtime_error_type": self.last_runtime_error_type,
            "last_handshake_status": self.last_handshake_status,
            "last_disconnect_reason": self.last_disconnect_reason,
            "last_subscribe_error_type": self.last_subscribe_error_type,
            "last_close_code": self.last_close_code,
            "last_close_exception_type": self.last_close_exception_type,
            "first_frame_received": self.first_frame_received,
            "last_control_method": self.last_control_method,
            "last_private_status_result": self.last_private_status_result,
            "last_private_status_reason": self.last_private_status_reason,
            "last_subscribe_device_count": self.last_subscribe_device_count,
            "last_subscribe_state_device_count": (
                self.last_subscribe_state_device_count
            ),
            "last_subscribe_state_key_samples": list(
                self.last_subscribe_state_key_samples
            ),
            "last_subscribe_node_hash_samples": list(
                self.last_subscribe_node_hash_samples
            ),
            "last_subscribe_node_candidate_hash_samples": [
                list(group)
                for group in self.last_subscribe_node_candidate_hash_samples
            ],
            "last_data_node_hash_samples": list(self.last_data_node_hash_samples),
            "last_data_node_candidate_hash_samples": [
                list(group) for group in self.last_data_node_candidate_hash_samples
            ],
            "recent_data_node_hash_samples": list(
                self.recent_data_node_hash_samples
            ),
            "recent_data_node_candidate_hash_samples": [
                list(group) for group in self.recent_data_node_candidate_hash_samples
            ],
            "last_payload_type": self.last_payload_type,
            "last_ignored_reason": self.last_ignored_reason,
            "last_ignored_payload_type": self.last_ignored_payload_type,
            "last_unsupported_payload_shape": self.last_unsupported_payload_shape,
            "last_subscribe_sent_at": self.last_subscribe_sent_at,
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

    async def __anext__(self) -> Any:
        """Return the next async-iterator message."""

    async def receive(self, timeout: float | None = None) -> Any:
        """Receive one message from the websocket."""


class PushWebSocketSession(Protocol):
    """Small subset of aiohttp ClientSession used by the transport."""

    async def ws_connect(
        self,
        url: str,
        *,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> PushWebSocket:
        """Open a websocket connection."""


__all__ = [
    "PushSleep",
    "PushTokenProvider",
    "PushTransportHealth",
    "PushTransportPayloadCallback",
    "PushWebSocket",
    "PushWebSocketSession",
]
