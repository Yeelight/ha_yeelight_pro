"""WebSocket transport for Yeelight Pro push payloads."""

from __future__ import annotations

import asyncio
from contextlib import suppress
import logging
from time import time
from typing import Any

from .const import DEFAULT_REQUEST_TIMEOUT
from .push_contract import (
    PUSH_HEARTBEAT_INTERVAL_SECONDS,
    PushMessageBuilder,
    PushReconnectPolicy,
    build_push_url,
)
from .push_transport_connection import PushTransportConnectionMixin
from .push_transport_frames import PushControlFrameError
from .push_transport_reconnect import PushTransportReconnectMixin
from .push_transport_runtime import PushTransportRuntimeMixin, _cancel_task
from .push_transport_types import (
    PushSleep,
    PushTokenProvider,
    PushTransportHealth,
    PushTransportPayloadCallback,
    PushWebSocket,
    PushWebSocketSession,
)

_LOGGER = logging.getLogger(__name__)


class YeelightPushWebSocketTransport(
    PushTransportConnectionMixin,
    PushTransportRuntimeMixin,
    PushTransportReconnectMixin,
):
    """Start a Yeelight push websocket and dispatch JSON object frames."""

    def __init__(
        self,
        *,
        session: PushWebSocketSession,
        token: str,
        token_provider: PushTokenProvider | None = None,
        base_url: str | None = None,
        message_builder: PushMessageBuilder | None = None,
        heartbeat_interval_seconds: float = PUSH_HEARTBEAT_INTERVAL_SECONDS,
        sleep: PushSleep = asyncio.sleep,
        reconnect_sleep: PushSleep | None = None,
        reconnect_policy: PushReconnectPolicy | None = None,
        auto_reconnect: bool = True,
        connect_timeout_seconds: float = DEFAULT_REQUEST_TIMEOUT,
    ) -> None:
        """Initialize a transport without opening a network connection."""
        self._session = session
        self._token = token
        self._token_provider = token_provider
        self._base_url = base_url
        self._message_builder = message_builder or PushMessageBuilder()
        self._heartbeat_interval_seconds = heartbeat_interval_seconds
        self._sleep = sleep
        self._reconnect_sleep = reconnect_sleep or sleep
        self._reconnect_policy = reconnect_policy or PushReconnectPolicy()
        self._auto_reconnect = auto_reconnect
        self._connect_timeout_seconds = connect_timeout_seconds
        self._websocket: PushWebSocket | None = None
        self._reader_task: asyncio.Task[None] | None = None
        self._heartbeat_task: asyncio.Task[None] | None = None
        self._reconnect_task: asyncio.Task[None] | None = None
        self._running = False
        self._callback: PushTransportPayloadCallback | None = None
        self._next_reconnect_delay: float | None = None
        self._last_start_error_type: str | None = None
        self._last_runtime_error_type: str | None = None
        self._last_failure_was_connect = False
        self._health = PushTransportHealth()
        self._connection_received_messages = 0
        self._connection_started_at: float | None = None

    @property
    def last_start_error_type(self) -> str | None:
        """Return the aggregate error type from a recoverable start failure."""
        return self._last_start_error_type

    @property
    def last_runtime_error_type(self) -> str | None:
        """Return the aggregate error type from a background runtime failure."""
        return self._last_runtime_error_type

    @property
    def health(self) -> PushTransportHealth:
        """Return diagnostics-safe aggregate transport health."""
        self._health.running = self._running
        self._health.websocket_open = self._websocket is not None
        self._health.last_start_error_type = self._last_start_error_type
        self._health.last_runtime_error_type = self._last_runtime_error_type
        return self._health

    async def async_start(self, callback: PushTransportPayloadCallback) -> None:
        """Open the websocket, subscribe, and start a reader task."""
        if self._running or self._websocket is not None:
            return
        self._running = True
        self._health.running = True
        self._callback = callback
        self._next_reconnect_delay = None
        self._last_start_error_type = None
        self._last_runtime_error_type = None
        try:
            await self._connect_once(callback)
        except Exception as err:
            if (
                self._auto_reconnect
                and not isinstance(err, ValueError)
                and self._last_failure_was_connect
            ):
                self._last_start_error_type = type(err).__name__
                self._schedule_reconnect()
                return
            self._running = False
            self._health.running = False
            self._callback = None
            raise

    async def _connect_once(self, callback: PushTransportPayloadCallback) -> None:
        """Open one websocket session and start its background tasks."""
        try:
            websocket = await self._ws_connect(
                build_push_url(
                    self._current_token(),
                    **({"base_url": self._base_url} if self._base_url else {}),
                )
            )
        except Exception:
            self._last_failure_was_connect = True
            raise
        self._websocket = websocket
        self._connection_received_messages = 0
        self._connection_started_at = time()
        self._health.first_frame_received = False
        self._health.reconnect_pending = False
        self._health.next_reconnect_delay = None
        self._health.last_close_code = None
        self._health.last_close_exception_type = None
        self._health.websocket_open = True
        self._health.connected_count += 1
        _LOGGER.info(
            "Yeelight Pro WebSocket connected: connect_attempts=%s connected_count=%s",
            self._health.connect_attempts,
            self._health.connected_count,
        )
        try:
            await self._send_json(websocket, self._message_builder.next_subscribe())
        except Exception as err:
            self._last_failure_was_connect = True
            self._websocket = None
            self._health.websocket_open = False
            self._health.last_subscribe_error_type = type(err).__name__
            self._health.last_disconnect_reason = "subscribe_failed"
            with suppress(Exception):
                await websocket.close()
            raise
        self._health.subscribe_sent_count += 1
        self._health.last_subscribe_sent_at = time()
        self._health.last_subscribe_error_type = None
        _LOGGER.info(
            "Yeelight Pro WebSocket subscribe frame sent: connected_count=%s",
            self._health.connected_count,
        )
        self._last_failure_was_connect = False
        self._reader_task = asyncio.create_task(self._read_messages(callback))
        self._heartbeat_task = asyncio.create_task(self._send_heartbeats())
        if self._last_runtime_error_type is not None:
            self._last_runtime_error_type = None
            self._health.last_runtime_error_type = None
        self._last_start_error_type = None

    def _current_token(self) -> str:
        """Return the freshest push token available for a new connection."""
        if self._token_provider is None:
            return self._token
        token = self._token_provider()
        return token if isinstance(token, str) and token.strip() else self._token

    async def _send_json(
        self,
        websocket: PushWebSocket,
        data: dict[str, Any],
    ) -> None:
        """Send a JSON frame with the same bounded setup/runtime timeout."""
        await asyncio.wait_for(
            websocket.send_json(data),
            timeout=self._connect_timeout_seconds,
        )

    async def async_stop(self) -> None:
        """Stop background tasks and close the active websocket."""
        self._running = False
        self._health.running = False
        self._health.reconnect_pending = False
        self._health.next_reconnect_delay = None
        self._callback = None
        reconnect_task = self._reconnect_task
        self._reconnect_task = None
        heartbeat_task = self._heartbeat_task
        reader_task = self._reader_task
        self._heartbeat_task = None
        self._reader_task = None
        await _cancel_task(reconnect_task)
        await _cancel_task(heartbeat_task)
        await _cancel_task(reader_task)

        websocket = self._websocket
        if websocket is not None:
            await websocket.close()
            self._websocket = None
            self._health.websocket_open = False
            self._health.disconnected_count += 1
            self._health.last_disconnect_reason = "stop_requested"

__all__ = [
    "PushControlFrameError",
    "PushSleep",
    "PushTokenProvider",
    "PushTransportPayloadCallback",
    "PushTransportHealth",
    "PushWebSocket",
    "PushWebSocketSession",
    "YeelightPushWebSocketTransport",
]
