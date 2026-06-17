"""WebSocket transport for Yeelight Pro push payloads."""

from __future__ import annotations

import asyncio
from contextlib import suppress
import logging
from time import time
from typing import Any

from aiohttp import WSCloseCode, WSServerHandshakeError, WSMsgType

from .const import DEFAULT_REQUEST_TIMEOUT
from .push_contract import (
    PUSH_HEARTBEAT_INTERVAL_SECONDS,
    PUSH_HEARTBEAT_TIMEOUT_SECONDS,
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
    PushTokenRefreshHandler,
    PushTokenProvider,
    PushTransportHealth,
    PushTransportPayloadCallback,
    PushWebSocket,
    PushWebSocketSession,
)

_LOGGER = logging.getLogger(__name__)


class YeelightPushWebSocketTransport:
    """Start a Yeelight push websocket and dispatch JSON object frames."""

    def __init__(
        self,
        *,
        session: PushWebSocketSession,
        token: str,
        token_provider: PushTokenProvider | None = None,
        token_refresh_handler: PushTokenRefreshHandler | None = None,
        base_url: str | None = None,
        message_builder: PushMessageBuilder | None = None,
        heartbeat_interval_seconds: float = PUSH_HEARTBEAT_INTERVAL_SECONDS,
        sleep: PushSleep = asyncio.sleep,
        reconnect_sleep: PushSleep | None = None,
        reconnect_policy: PushReconnectPolicy | None = None,
        auto_reconnect: bool = True,
        connect_timeout_seconds: float = DEFAULT_REQUEST_TIMEOUT,
        proxy: str | None = None,
    ) -> None:
        """Initialize a transport without opening a network connection."""
        self._session = session
        self._token = token
        self._token_provider = token_provider
        self._token_refresh_handler = token_refresh_handler
        self._base_url = base_url
        self._message_builder = message_builder or PushMessageBuilder()
        self._heartbeat_interval_seconds = heartbeat_interval_seconds
        self._sleep = sleep
        self._reconnect_sleep = reconnect_sleep or sleep
        self._reconnect_policy = reconnect_policy or PushReconnectPolicy()
        self._auto_reconnect = auto_reconnect
        self._connect_timeout_seconds = connect_timeout_seconds
        self._proxy = proxy.strip() if isinstance(proxy, str) and proxy.strip() else None
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
        self._health.proxy_configured = self._proxy is not None
        self._connection_received_messages = 0
        self._connection_started_at: float | None = None
        self._early_close_streak_refreshed_token = False

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
        self._health.reconnect_suspended = False
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
        except Exception:
            self._last_failure_was_connect = True
            self._websocket = None
            self._health.websocket_open = False
            self._health.last_disconnect_reason = "subscribe_failed"
            with suppress(Exception):
                await websocket.close()
            raise
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

    async def _ws_connect(self, url: str) -> PushWebSocket:
        """Open websocket with a bounded setup timeout."""
        self._health.connect_attempts += 1
        try:
            websocket = await self._session.ws_connect(
                url,
                timeout=self._connect_timeout_seconds,
                proxy=self._proxy,
            )
            self._health.last_handshake_status = None
            self._health.last_disconnect_reason = None
            return websocket
        except WSServerHandshakeError as err:
            self._record_handshake_failure(err)
            raise
        except TypeError:
            try:
                websocket = await self._session.ws_connect(url)
            except WSServerHandshakeError as err:
                self._record_handshake_failure(err)
                raise
            except Exception:
                self._health.last_handshake_status = None
                self._health.last_disconnect_reason = "connect_failed"
                raise
            self._health.last_handshake_status = None
            self._health.last_disconnect_reason = None
            return websocket
        except Exception:
            self._health.last_handshake_status = None
            self._health.last_disconnect_reason = "connect_failed"
            raise

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
        self._health.reconnect_suspended = False
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

    async def _read_messages(self, callback: PushTransportPayloadCallback) -> None:
        """Read websocket messages and dispatch JSON object payloads."""
        websocket = self._websocket
        if websocket is None:
            return
        reader_failed = False
        try:
            while True:
                message = await self._receive_message(websocket)
                message_type = getattr(message, "type", None)
                if message_type in {WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.ERROR}:
                    self._health.ignored_messages += 1
                    self._record_close_frame(websocket, message_type)
                    break
                self._health.received_messages += 1
                self._connection_received_messages += 1
                self._health.first_frame_received = True
                self._health.consecutive_pre_first_frame_abnormal_close_count = 0
                self._early_close_streak_refreshed_token = False
                self._health.last_message_at = time()
                if message_type not in {WSMsgType.TEXT, WSMsgType.BINARY}:
                    self._health.ignored_messages += 1
                    continue
                payload = json_payload_from_message(message)
                if payload is None:
                    self._health.malformed_messages += 1
                    self._record_ignored("malformed_json", None)
                    continue
                self._health.decoded_json_messages += 1
                aggregate_payload_type = payload_type(payload)
                if is_control_frame(payload):
                    self._health.control_frames += 1
                    _LOGGER.debug(
                        "Yeelight Pro WebSocket control frame received: type=%s control_frames=%s",
                        aggregate_payload_type,
                        self._health.control_frames,
                    )
                raise_for_control_error_frame(payload)
                if is_push_data_payload(payload):
                    await callback(payload)
                    self._health.dispatched_payloads += 1
                    self._health.last_payload_type = aggregate_payload_type
                    self._health.last_ignored_reason = None
                    self._health.last_ignored_payload_type = None
                    self._health.last_dispatched_at = time()
                else:
                    self._health.ignored_messages += 1
                    self._record_ignored(
                        "unsupported_payload",
                        aggregate_payload_type,
                    )
        except Exception as err:
            reader_failed = True
            self._last_runtime_error_type = type(err).__name__
            self._health.last_runtime_error_type = self._last_runtime_error_type
            self._health.last_disconnect_reason = "reader_exception"
            _LOGGER.warning(
                "Yeelight Pro WebSocket reader failed: error_type=%s received_messages=%s "
                "decoded_json_messages=%s dispatched_payloads=%s",
                self._last_runtime_error_type,
                self._connection_received_messages,
                self._health.decoded_json_messages,
                self._health.dispatched_payloads,
            )
        finally:
            await self._cleanup_after_reader_exit(
                websocket, close_websocket=reader_failed
            )
            self._schedule_reconnect()

    async def _receive_message(self, websocket: PushWebSocket) -> Any:
        """Receive one frame, supporting aiohttp and lightweight test doubles."""
        receive = getattr(websocket, "receive", None)
        if callable(receive):
            try:
                return await receive()
            except TypeError:
                return await receive(timeout=None)
        return await websocket.__anext__()

    def _record_close_frame(self, websocket: PushWebSocket, message_type: Any) -> None:
        """Record aggregate close-frame metadata without exposing frame data."""
        close_code = getattr(websocket, "close_code", None)
        self._health.last_close_code = close_code if isinstance(close_code, int) else None
        exception = getattr(websocket, "exception", None)
        if callable(exception):
            with suppress(Exception):
                exception = exception()
        self._health.last_close_exception_type = (
            type(exception).__name__ if exception is not None else None
        )
        if self._connection_received_messages == 0:
            if (
                self._health.last_close_code == WSCloseCode.ABNORMAL_CLOSURE
                or exception is not None
            ):
                self._health.last_disconnect_reason = (
                    "abnormal_close_before_first_frame"
                )
                self._health.pre_first_frame_abnormal_close_count += 1
                self._health.consecutive_pre_first_frame_abnormal_close_count += 1
            else:
                self._health.last_disconnect_reason = "closed_before_first_frame"
        elif message_type in {WSMsgType.CLOSE, WSMsgType.CLOSED}:
            self._health.last_disconnect_reason = "server_closed"
        else:
            self._health.last_disconnect_reason = "websocket_error_frame"

    def _record_ignored(self, reason: str, payload_type_value: str | None) -> None:
        """Record aggregate diagnostics for the most recent ignored frame."""
        self._health.last_ignored_reason = reason
        self._health.last_ignored_payload_type = payload_type_value

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
            self._health.last_disconnect_reason = "background_failure"

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
            if self._connection_received_messages > 0:
                self._next_reconnect_delay = None
            if close_websocket:
                closed = False
                with suppress(Exception):
                    await websocket.close()
                    closed = True
                if closed and self._websocket is websocket:
                    self._websocket = None
                    self._health.websocket_open = False
                    self._health.disconnected_count += 1
                    self._health.last_disconnect_reason = "reader_exception"
            else:
                self._websocket = None
                self._health.websocket_open = False
                self._health.disconnected_count += 1
                if self._health.last_disconnect_reason is None:
                    self._health.last_disconnect_reason = "reader_ended"
            self._log_connection_closed(websocket)

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
        planned_delay = self._planned_reconnect_delay()
        self._health.reconnect_pending = True
        self._health.next_reconnect_delay = planned_delay
        self._health.reconnect_suspended = False
        self._reconnect_task = asyncio.create_task(
            self._reconnect_until_connected(self._callback)
        )
        _LOGGER.info(
            "Yeelight Pro WebSocket reconnect scheduled: last_disconnect_reason=%s "
            "next_delay=%s reconnect_suspended=%s reconnect_attempts=%s",
            self._health.last_disconnect_reason,
            planned_delay,
            self._health.reconnect_suspended,
            self._health.reconnect_attempts,
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
                delay = self._planned_reconnect_delay()
                self._next_reconnect_delay = delay
                self._health.reconnect_pending = True
                self._health.next_reconnect_delay = delay
                self._health.reconnect_suspended = False
                await self._reconnect_sleep(delay)
                if not self._running or self._websocket is not None:
                    return
                try:
                    await self._maybe_refresh_after_early_abnormal_close()
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

    def _planned_reconnect_delay(self) -> float:
        """Return the next bounded reconnect delay."""
        delay = self._reconnect_policy.next_delay(self._next_reconnect_delay)
        if (
            self._health.last_disconnect_reason == "abnormal_close_before_first_frame"
            and self._health.last_token_refresh_error_type is not None
        ):
            return max(delay, float(PUSH_HEARTBEAT_TIMEOUT_SECONDS))
        return delay

    async def _maybe_refresh_after_early_abnormal_close(self) -> None:
        """Refresh the token once after a subscribe-stage abnormal close."""
        if self._health.last_disconnect_reason != "abnormal_close_before_first_frame":
            return
        if self._early_close_streak_refreshed_token:
            return
        handler = self._token_refresh_handler
        if handler is None:
            return
        self._early_close_streak_refreshed_token = True
        self._health.token_refresh_attempts += 1
        try:
            token = await handler()
        except Exception as err:
            self._health.last_token_refresh_error_type = type(err).__name__
            _LOGGER.warning(
                "Yeelight Pro WebSocket token refresh failed after early close: "
                "error_type=%s",
                self._health.last_token_refresh_error_type,
            )
            return
        if isinstance(token, str) and token.strip():
            self._token = token.strip()
        self._health.token_refresh_successes += 1
        self._health.last_token_refresh_error_type = None
        self._next_reconnect_delay = None
        _LOGGER.info(
            "Yeelight Pro WebSocket token refreshed after early close: "
            "token_refresh_successes=%s",
            self._health.token_refresh_successes,
        )

    def _record_handshake_failure(self, err: WSServerHandshakeError) -> None:
        """Record diagnostics-safe WebSocket handshake metadata."""
        status = getattr(err, "status", None)
        if isinstance(status, int):
            self._health.last_handshake_status = status
        else:
            self._health.last_handshake_status = None
        self._health.last_disconnect_reason = "handshake_failed"

    def _log_connection_closed(self, websocket: PushWebSocket) -> None:
        """Log aggregate-only close metadata for runtime troubleshooting."""
        started_at = self._connection_started_at
        lifetime = None if started_at is None else max(0.0, time() - started_at)
        close_code = getattr(websocket, "close_code", None)
        exception = getattr(websocket, "exception", None)
        if callable(exception):
            with suppress(Exception):
                exception = exception()
        exception_type = type(exception).__name__ if exception is not None else None
        log = _LOGGER.warning if self._connection_received_messages == 0 else _LOGGER.info
        log(
            "Yeelight Pro WebSocket closed: reason=%s close_code=%s exception_type=%s "
            "lifetime_seconds=%.3f received_messages=%s decoded_json_messages=%s "
            "control_frames=%s dispatched_payloads=%s",
            self._health.last_disconnect_reason,
            close_code,
            exception_type,
            lifetime if lifetime is not None else -1.0,
            self._connection_received_messages,
            self._health.decoded_json_messages,
            self._health.control_frames,
            self._health.dispatched_payloads,
        )
        self._connection_started_at = None


async def _cancel_task(task: asyncio.Task[None] | None) -> None:
    """Cancel and await a background task."""
    if task is not None and not task.done():
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

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
