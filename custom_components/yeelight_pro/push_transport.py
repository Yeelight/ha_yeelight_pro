"""WebSocket transport for Yeelight Pro push payloads."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import Any, Protocol

from aiohttp import WSMsgType

from .push_contract import (
    PUSH_CONTROL_METHODS,
    PUSH_DATA_TYPES,
    PUSH_HEARTBEAT_INTERVAL_SECONDS,
    PushMessageBuilder,
    PushReconnectPolicy,
    build_push_url,
)

PushTransportPayloadCallback = Callable[[dict[str, Any]], Awaitable[object]]
PushSleep = Callable[[float], Awaitable[object]]


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

    async def ws_connect(self, url: str) -> PushWebSocket:
        """Open a websocket connection."""


class YeelightPushWebSocketTransport:
    """Start a Yeelight push websocket and dispatch JSON object frames."""

    def __init__(
        self,
        *,
        session: PushWebSocketSession,
        token: str,
        message_builder: PushMessageBuilder | None = None,
        heartbeat_interval_seconds: float = PUSH_HEARTBEAT_INTERVAL_SECONDS,
        sleep: PushSleep = asyncio.sleep,
        reconnect_sleep: PushSleep | None = None,
        reconnect_policy: PushReconnectPolicy | None = None,
        auto_reconnect: bool = True,
    ) -> None:
        """Initialize a transport without opening a network connection."""
        self._session = session
        self._token = token
        self._message_builder = message_builder or PushMessageBuilder()
        self._heartbeat_interval_seconds = heartbeat_interval_seconds
        self._sleep = sleep
        self._reconnect_sleep = reconnect_sleep or sleep
        self._reconnect_policy = reconnect_policy or PushReconnectPolicy()
        self._auto_reconnect = auto_reconnect
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

    @property
    def last_start_error_type(self) -> str | None:
        """Return the aggregate error type from a recoverable start failure."""
        return self._last_start_error_type

    @property
    def last_runtime_error_type(self) -> str | None:
        """Return the aggregate error type from a background runtime failure."""
        return self._last_runtime_error_type

    async def async_start(self, callback: PushTransportPayloadCallback) -> None:
        """Open the websocket, subscribe, and start a reader task."""
        if self._running or self._websocket is not None:
            return
        self._running = True
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
            self._callback = None
            raise

    async def _connect_once(self, callback: PushTransportPayloadCallback) -> None:
        """Open one websocket session and start its background tasks."""
        try:
            websocket = await self._session.ws_connect(build_push_url(self._token))
        except Exception:
            self._last_failure_was_connect = True
            raise
        self._last_failure_was_connect = False
        self._websocket = websocket
        try:
            await websocket.send_json(self._message_builder.next_subscribe())
        except Exception:
            self._websocket = None
            with suppress(Exception):
                await websocket.close()
            raise
        self._reader_task = asyncio.create_task(self._read_messages(callback))
        self._heartbeat_task = asyncio.create_task(self._send_heartbeats())
        self._next_reconnect_delay = None
        self._last_start_error_type = None

    async def async_stop(self) -> None:
        """Stop background tasks and close the active websocket."""
        self._running = False
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

    async def _read_messages(self, callback: PushTransportPayloadCallback) -> None:
        """Read websocket messages and dispatch JSON object payloads."""
        websocket = self._websocket
        if websocket is None:
            return
        reader_failed = False
        try:
            async for message in websocket:
                payload = _json_payload_from_message(message)
                if payload is None:
                    continue
                _raise_for_control_error_frame(payload)
                if _is_push_data_payload(payload):
                    await callback(payload)
        except Exception as err:
            reader_failed = True
            self._last_runtime_error_type = type(err).__name__
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
                await websocket.send_json(self._message_builder.next_heartbeat())
        except Exception as err:
            self._last_runtime_error_type = type(err).__name__
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
            else:
                self._websocket = None

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
                    await self._connect_once(callback)
                except asyncio.CancelledError:
                    cancelled = True
                    raise
                except Exception as err:
                    self._last_runtime_error_type = type(err).__name__
                    continue
        except (asyncio.CancelledError, GeneratorExit):
            cancelled = True
            raise
        finally:
            if self._reconnect_task is current_task:
                self._reconnect_task = None
                if not cancelled and self._running and self._websocket is None:
                    self._schedule_reconnect()


def _json_payload_from_message(message: Any) -> dict[str, Any] | None:
    """Return a JSON object payload for text/json websocket messages."""
    message_type = getattr(message, "type", None)
    if message_type not in {WSMsgType.TEXT, WSMsgType.BINARY}:
        return None

    data = getattr(message, "data", None)
    if isinstance(data, bytes):
        try:
            data = data.decode()
        except UnicodeDecodeError:
            return None
    if not isinstance(data, str):
        return None

    try:
        payload = json.loads(data)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _is_push_data_payload(payload: dict[str, Any]) -> bool:
    """Return whether a WebSocket object is a documented prop/event payload."""
    return payload.get("type") in PUSH_DATA_TYPES


def _raise_for_control_error_frame(payload: dict[str, Any]) -> None:
    """Reject subscribe/heartbeat control errors without exposing vendor text."""
    method = payload.get("method")
    if method not in PUSH_CONTROL_METHODS:
        return

    success = payload.get("success")
    code = str(payload.get("code", "")).strip()
    if success is False or code not in ("", "200"):
        raise PushControlFrameError


async def _cancel_task(task: asyncio.Task[None] | None) -> None:
    """Cancel and await a background task."""
    if task is not None and not task.done():
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


class PushControlFrameError(Exception):
    """Aggregate-only error for failed WebSocket control frames."""


__all__ = [
    "PushControlFrameError",
    "PushSleep",
    "PushTransportPayloadCallback",
    "PushWebSocket",
    "PushWebSocketSession",
    "YeelightPushWebSocketTransport",
]
