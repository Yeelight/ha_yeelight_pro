"""Send-side contract helpers for Yeelight Pro push WebSocket frames."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote

DEFAULT_PUSH_BASE_URL = "wss://push.yeelight.com/ws"
PUSH_HEARTBEAT_INTERVAL_SECONDS = 20
PUSH_HEARTBEAT_TIMEOUT_SECONDS = 60
PUSH_RECONNECT_MIN_DELAY_SECONDS = 1.0
PUSH_RECONNECT_MAX_DELAY_SECONDS = float(PUSH_HEARTBEAT_TIMEOUT_SECONDS)
PUSH_RECONNECT_MULTIPLIER = 2.0
PUSH_PROTOCOL_VERSION = "1.0"
PUSH_SUBSCRIBE_TYPE = 2
PUSH_EVENT_NOTIFICATION_TRANSPORT = "WebSocket"
PUSH_CONTROL_METHOD_SUBSCRIBE = "subscribe"
PUSH_CONTROL_METHOD_HEARTBEAT = "heartbeat"
PUSH_CONTROL_METHODS = frozenset(
    {PUSH_CONTROL_METHOD_SUBSCRIBE, PUSH_CONTROL_METHOD_HEARTBEAT}
)
PUSH_DATA_TYPE_PROP = "prop"
PUSH_DATA_TYPE_EVENT = "event"
PUSH_DATA_TYPES = frozenset({PUSH_DATA_TYPE_PROP, PUSH_DATA_TYPE_EVENT})


def build_push_url(
    token: str,
    *,
    base_url: str = DEFAULT_PUSH_BASE_URL,
) -> str:
    """Build the Yeelight push WebSocket URL without logging token material."""
    normalized_token = _normalize_push_token(token)
    normalized_base_url = _normalize_push_base_url(base_url)
    return f"{normalized_base_url}/{quote(normalized_token, safe='')}"


def build_subscribe_message(
    message_id: int,
    *,
    timestamp: int | None = None,
) -> dict[str, Any]:
    """Build a Yeelight push subscription frame."""
    return {
        "id": message_id,
        "method": PUSH_CONTROL_METHOD_SUBSCRIBE,
        "params": {"type": PUSH_SUBSCRIBE_TYPE},
        "timestamp": _timestamp_or_now(timestamp),
        "version": PUSH_PROTOCOL_VERSION,
    }


def build_heartbeat_message(
    message_id: int,
    *,
    timestamp: int | None = None,
) -> dict[str, Any]:
    """Build a Yeelight push heartbeat frame."""
    return {
        "id": message_id,
        "method": PUSH_CONTROL_METHOD_HEARTBEAT,
        "timestamp": _timestamp_or_now(timestamp),
        "version": PUSH_PROTOCOL_VERSION,
    }


def heartbeat_is_stale(
    *,
    last_heartbeat_at: int | float | None,
    now: int | float | None = None,
    timeout_seconds: int = PUSH_HEARTBEAT_TIMEOUT_SECONDS,
) -> bool:
    """Return whether a push heartbeat is stale by the documented timeout."""
    if last_heartbeat_at is None:
        return True
    current_time = time.time() if now is None else float(now)
    return current_time - float(last_heartbeat_at) >= timeout_seconds


@dataclass(frozen=True, slots=True)
class PushReconnectPolicy:
    """Pure reconnect backoff policy for future push transports."""

    min_delay_seconds: float = PUSH_RECONNECT_MIN_DELAY_SECONDS
    max_delay_seconds: float = PUSH_RECONNECT_MAX_DELAY_SECONDS
    multiplier: float = PUSH_RECONNECT_MULTIPLIER

    def __post_init__(self) -> None:
        """Validate policy values without creating runtime side effects."""
        if self.min_delay_seconds <= 0:
            raise ValueError("min reconnect delay must be positive")
        if self.max_delay_seconds < self.min_delay_seconds:
            raise ValueError("max reconnect delay must not be below min delay")
        if self.multiplier <= 1:
            raise ValueError("reconnect multiplier must be greater than 1")

    def delay_for_attempt(self, attempt: int) -> float:
        """Return bounded exponential delay for a one-based reconnect attempt."""
        if attempt < 1:
            raise ValueError("reconnect attempt must be one-based")
        delay = self.min_delay_seconds * (self.multiplier ** (attempt - 1))
        return min(delay, self.max_delay_seconds)

    def next_delay(self, previous_delay_seconds: float | None = None) -> float:
        """Return the next bounded delay after the previous reconnect delay."""
        if previous_delay_seconds is None or previous_delay_seconds <= 0:
            return self.min_delay_seconds
        return min(previous_delay_seconds * self.multiplier, self.max_delay_seconds)


@dataclass(slots=True)
class PushMessageBuilder:
    """Build push WebSocket frames with monotonically increasing message ids."""

    _next_id: int = field(default=1)

    def next_subscribe(self, *, timestamp: int | None = None) -> dict[str, Any]:
        """Return the next subscribe frame."""
        return build_subscribe_message(self._claim_id(), timestamp=timestamp)

    def next_heartbeat(self, *, timestamp: int | None = None) -> dict[str, Any]:
        """Return the next heartbeat frame."""
        return build_heartbeat_message(self._claim_id(), timestamp=timestamp)

    def _claim_id(self) -> int:
        """Return current id and advance the internal counter."""
        message_id = self._next_id
        self._next_id += 1
        return message_id


def _normalize_push_token(token: str) -> str:
    """Remove a case-insensitive Bearer prefix and reject empty token values."""
    raw_token = str(token).strip()
    prefix = "bearer"
    if raw_token[: len(prefix)].casefold() == prefix and (
        len(raw_token) == len(prefix) or raw_token[len(prefix)].isspace()
    ):
        raw_token = raw_token[len(prefix) :].strip()
    if not raw_token:
        raise ValueError("Yeelight Pro push token is required")
    return raw_token


def _normalize_push_base_url(base_url: str) -> str:
    """Reject non-WebSocket endpoints for Yeelight event notifications."""
    raw_base_url = str(base_url).strip().rstrip("/")
    if not raw_base_url.casefold().startswith("wss://"):
        raise ValueError("Yeelight Pro event notifications require a wss:// URL")
    return raw_base_url


def _timestamp_or_now(timestamp: int | None) -> int:
    """Return a seconds-level timestamp."""
    return int(time.time()) if timestamp is None else int(timestamp)


__all__ = [
    "DEFAULT_PUSH_BASE_URL",
    "PUSH_CONTROL_METHODS",
    "PUSH_CONTROL_METHOD_HEARTBEAT",
    "PUSH_CONTROL_METHOD_SUBSCRIBE",
    "PUSH_DATA_TYPES",
    "PUSH_DATA_TYPE_EVENT",
    "PUSH_DATA_TYPE_PROP",
    "PUSH_EVENT_NOTIFICATION_TRANSPORT",
    "PUSH_HEARTBEAT_INTERVAL_SECONDS",
    "PUSH_HEARTBEAT_TIMEOUT_SECONDS",
    "PUSH_RECONNECT_MAX_DELAY_SECONDS",
    "PUSH_RECONNECT_MIN_DELAY_SECONDS",
    "PUSH_RECONNECT_MULTIPLIER",
    "PushMessageBuilder",
    "PushReconnectPolicy",
    "build_heartbeat_message",
    "build_push_url",
    "build_subscribe_message",
    "heartbeat_is_stale",
]
