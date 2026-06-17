"""WebSocket transport for Yeelight Pro push payloads."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from time import time
from typing import Any

from aiohttp import WSMsgType

from .const import DEFAULT_REQUEST_TIMEOUT
from .push_contract import (
    PUSH_HEARTBEAT_INTERVAL_SECONDS,
    PushMessageBuilder,
    PushReconnectPolicy,
    build_push_url,
)
from .push_transport_frames import (
    PushControlFrameError,
    is_control_frame,
    is_push_data_payload,
    json_payload_from_message,
    payload_type,
    raise_for_control_error_frame,
)
from .push_transport_types import (
    PushSleep,
    PushTransportHealth,
    PushTransportPayloadCallback,
    PushWebSocket,
    PushWebSocketSession,
)


class YeelightPushWebSocketTransport:
    """Start a Yeelight push websocket and dispatch JSON object frames."""

    def __init__(
        self,
        *,
        session: PushWebSocketSession,
        token: str,
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
                    self._token,
                    **({"base_url": self._base_url} if self._base_url else {}),
                )
            )
        except Exception:
            self._last_failure_was_connect = True
            raise
        self._websocket = websocket
        self._health.websocket_open = True
        self._health.connected_count += 1
        try:
            await self._send_json(websocket, self._message_builder.next_subscribe())
        except Exception:
            self._last_failure_was_connect = True
            self._websocket = None
            self._health.websocket_open = False
            with suppress(Exception):
                await websocket.close()
            raise
        self._last_failure_was_connect = False
        self._reader_task = asyncio.create_task(self._read_messages(callback))
        self._heartbeat_task = asyncio.create_task(self._send_heartbeats())
        self._next_reconnect_delay = None
        self._last_start_error_type = None

    async def _ws_connect(self, url: str) -> PushWebSocket:
        """Open websocket with a bounded setup timeout."""
        self._health.connect_attempts += 1
        try:
            return await self._session.ws_connect(
                url,
                timeout=self._connect_timeout_seconds,
            )
        except TypeError:
            return await self._session.ws_connect(url)

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

    async def _read_messages(self, callback: PushTransportPayloadCallback) -> None:
        """Read websocket messages and dispatch JSON object payloads."""
        websocket = self._websocket
        if websocket is None:
            return
        reader_failed = False
        try:
            async for message in websocket:
                self._health.received_messages += 1
                self._health.last_message_at = time()
                message_type = getattr(message, "type", None)
                if message_type not in {WSMsgType.TEXT, WSMsgType.BINARY}:
                    self._health.ignored_messages += 1
                    continue
                payload = json_payload_from_message(message)
                if payload is None:
                    self._health.malformed_messages += 1
                    continue
                self._health.decoded_json_messages += 1
                if is_control_frame(payload):
                    self._health.control_frames += 1
                raise_for_control_error_frame(payload)
                if is_push_data_payload(payload):
                    await callback(payload)
                    self._health.dispatched_payloads += 1
                    self._health.last_payload_type = payload_type(payload)
                    self._health.last_dispatched_at = time()
                else:
                    self._health.ignored_messages += 1
        except Exception as err:
            reader_failed = True
            self._last_runtime_error_type = type(err).__name__
            self._health.last_runtime_error_type = self._last_runtime_error_type
        finally:
            await self._cleanup_after_reader_exit(
                websocket, close_websocket=reader_failed
            )
            self._schedule_reconnect()

    async def _send_heartbeats(self) -> None:
        """Send documented heartbeat frames until the transport is stopped."""
        current_task = asyncio.current_task()
        try:
            while True:
                await self._sleep(self._heartbeat_interval_seconds)
                websocket = self._websocket
                if websocket is None:
                    return
                await self._send_json(
                    websocket,
                    self._message_builder.next_heartbeat(),
                )
                self._health.heartbeat_sent_count += 1
        except Exception as err:
            self._last_runtime_error_type = type(err).__name__
            self._health.last_runtime_error_type = self._last_runtime_error_type
            if self._heartbeat_task is current_task:
                self._heartbeat_task = None
            await self._close_after_background_failure()
            self._schedule_reconnect()
        finally:
            if self._heartbeat_task is current_task:
                self._heartbeat_task = None

    async def _close_after_background_failure(self) -> None:
        """Close the websocket after a background task failure."""
        reader_task = self._reader_task
        self._reader_task = None
        await _cancel_task(reader_task)

        websocket = self._websocket
        if websocket is None:
            return
        closed = False
        with suppress(Exception):
            await websocket.close()
            closed = True
        if closed and self._websocket is websocket:
            self._websocket = None
            self._health.websocket_open = False
            self._health.disconnected_count += 1

    async def _cleanup_after_reader_exit(
        self,
        websocket: PushWebSocket,
        *,
        close_websocket: bool,
    ) -> None:
        """Clean heartbeat and connection state after the reader exits by itself."""
        current_task = asyncio.current_task()
        if self._reader_task is not current_task:
            return

        self._reader_task = None
        if self._websocket is websocket:
            if close_websocket:
                closed = False
                with suppress(Exception):
                    await websocket.close()
                    closed = True
                if closed and self._websocket is websocket:
                    self._websocket = None
                    self._health.websocket_open = False
                    self._health.disconnected_count += 1
            else:
                self._websocket = None
                self._health.websocket_open = False
                self._health.disconnected_count += 1

        heartbeat_task = self._heartbeat_task
        if heartbeat_task is not None:
            self._heartbeat_task = None
            await _cancel_task(heartbeat_task)

    def _schedule_reconnect(self) -> None:
        """Schedule a bounded reconnect loop while the transport is running."""
        if not self._auto_reconnect or not self._running or self._callback is None:
            return
        reconnect_task = self._reconnect_task
        if reconnect_task is not None and not reconnect_task.done():
            return
        self._reconnect_task = asyncio.create_task(
            self._reconnect_until_connected(self._callback)
        )

    async def _reconnect_until_connected(
        self,
        callback: PushTransportPayloadCallback,
    ) -> None:
        """Reconnect with bounded backoff until stopped or connected."""
        current_task = asyncio.current_task()
        cancelled = False
        try:
            while self._running and self._websocket is None:
                delay = self._reconnect_policy.next_delay(
                    self._next_reconnect_delay
                )
                self._next_reconnect_delay = delay
                await self._reconnect_sleep(delay)
                if not self._running or self._websocket is not None:
                    return
                try:
                    self._health.reconnect_attempts += 1
                    await self._connect_once(callback)
                except asyncio.CancelledError:
                    cancelled = True
                    raise
                except Exception as err:
                    self._last_runtime_error_type = type(err).__name__
                    self._health.last_runtime_error_type = self._last_runtime_error_type
                    continue
        except (asyncio.CancelledError, GeneratorExit):
            cancelled = True
            raise
        finally:
            if self._reconnect_task is current_task:
                self._reconnect_task = None
                if not cancelled and self._running and self._websocket is None:
                    self._schedule_reconnect()


async def _cancel_task(task: asyncio.Task[None] | None) -> None:
    """Cancel and await a background task."""
    if task is not None and not task.done():
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

__all__ = [
    "PushControlFrameError",
    "PushSleep",
    "PushTransportPayloadCallback",
    "PushTransportHealth",
    "PushWebSocket",
    "PushWebSocketSession",
    "YeelightPushWebSocketTransport",
]
