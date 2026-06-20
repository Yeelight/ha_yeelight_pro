"""Runtime reader and heartbeat helpers for the Yeelight Pro push transport."""

from __future__ import annotations

import asyncio
from contextlib import suppress
import logging
from time import time
from typing import TYPE_CHECKING, Any, Protocol, cast

from aiohttp import WSCloseCode, WSMsgType

from .push_transport_frames import (
    control_frame_method,
    control_frame_subscribe_device_count,
    control_frame_subscribe_node_candidate_hash_samples,
    control_frame_subscribe_node_hash_samples,
    control_frame_subscribe_state_device_count,
    control_frame_subscribe_state_key_samples,
    data_frame_node_candidate_hash_samples,
    data_frame_node_hash_samples,
    is_control_frame,
    is_push_data_payload,
    json_payload_from_message,
    payload_type,
    private_status_reason_label,
    private_status_result_label,
    private_subscribe_state_payload,
    raise_for_control_error_frame,
)
from .push_transport_shapes import payload_shape_summary
from .push_transport_types import PushTransportPayloadCallback, PushWebSocket

_LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .push_contract import PushMessageBuilder
    from .push_transport_types import PushSleep, PushTransportHealth


class _RuntimeTransportProtocol(Protocol):
    """Concrete transport methods used across push transport mixins."""

    async def _send_json(
        self,
        websocket: PushWebSocket,
        data: dict[str, Any],
    ) -> None:
        """Send a JSON frame through the active websocket."""

    def _schedule_reconnect(self) -> None:
        """Schedule reconnect after a runtime disconnect."""


class PushTransportRuntimeMixin:
    """Read, dispatch, and clean up one active WebSocket connection."""

    _connection_received_messages: int
    _connection_started_at: float | None
    _health: "PushTransportHealth"
    _heartbeat_interval_seconds: float
    _heartbeat_task: asyncio.Task[None] | None
    _last_runtime_error_type: str | None
    _message_builder: "PushMessageBuilder"
    _next_reconnect_delay: float | None
    _reader_task: asyncio.Task[None] | None
    _sleep: "PushSleep"
    _websocket: PushWebSocket | None

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
                self._record_received_message()
                if message_type not in {WSMsgType.TEXT, WSMsgType.BINARY}:
                    self._health.ignored_messages += 1
                    continue
                payload = json_payload_from_message(message)
                if payload is None:
                    self._health.malformed_messages += 1
                    self._record_ignored("malformed_json", None)
                    continue
                await self._handle_json_payload(callback, payload)
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
            await self._cleanup_after_reader_exit(websocket, close_websocket=reader_failed)
            cast(_RuntimeTransportProtocol, self)._schedule_reconnect()

    async def _receive_message(self, websocket: PushWebSocket) -> Any:
        """Receive one frame, supporting aiohttp and lightweight test doubles."""
        receive = getattr(websocket, "receive", None)
        if callable(receive):
            try:
                return await receive()
            except TypeError:
                return await receive(timeout=None)
        return await websocket.__anext__()

    def _record_received_message(self) -> None:
        """Record aggregate first-frame and frame-count diagnostics."""
        self._health.received_messages += 1
        self._connection_received_messages += 1
        self._health.first_frame_received = True
        self._health.consecutive_pre_first_frame_abnormal_close_count = 0
        self._health.last_message_at = time()

    async def _handle_json_payload(
        self,
        callback: PushTransportPayloadCallback,
        payload: dict[str, Any],
    ) -> None:
        """Classify one decoded JSON payload without logging raw payload data."""
        self._health.decoded_json_messages += 1
        aggregate_payload_type = payload_type(payload)
        control_frame = is_control_frame(payload)
        if control_frame:
            self._health.control_frames += 1
            self._health.last_control_method = control_frame_method(payload)
            private_status = private_status_result_label(payload)
            if private_status is not None:
                self._health.private_status_frames += 1
                self._health.last_private_status_result = private_status
                private_status_reason = private_status_reason_label(payload)
                if private_status_reason is not None:
                    self._health.last_private_status_reason = private_status_reason
                if private_status != "success":
                    self._health.private_status_non_success_frames += 1
            device_count = control_frame_subscribe_device_count(payload)
            if device_count is not None:
                self._health.last_subscribe_device_count = device_count
                self._health.last_subscribe_state_device_count = (
                    control_frame_subscribe_state_device_count(payload)
                )
                self._health.last_subscribe_state_key_samples = tuple(
                    control_frame_subscribe_state_key_samples(payload)
                )
                self._health.last_subscribe_node_hash_samples = tuple(
                    control_frame_subscribe_node_hash_samples(payload)
                )
                self._health.last_subscribe_node_candidate_hash_samples = (
                    _freeze_node_hash_groups(
                        control_frame_subscribe_node_candidate_hash_samples(payload)
                    )
                )
            _LOGGER.debug(
                "Yeelight Pro WebSocket control frame received: type=%s control_frames=%s",
                aggregate_payload_type,
                self._health.control_frames,
            )
            if self._health.last_control_method == "private_status":
                self._health.last_unsupported_payload_shape = payload_shape_summary(
                    payload
                )
        raise_for_control_error_frame(payload)
        snapshot_payload = private_subscribe_state_payload(payload)
        if snapshot_payload is not None:
            await self._dispatch_payload(callback, snapshot_payload, aggregate_payload_type)
            return
        if is_push_data_payload(payload):
            await self._dispatch_payload(callback, payload, aggregate_payload_type)
            return
        self._health.ignored_messages += 1
        reason = "control_frame" if control_frame else "unsupported_payload"
        if not control_frame:
            self._health.unsupported_messages += 1
            self._health.last_unsupported_payload_shape = payload_shape_summary(payload)
        self._record_ignored(reason, aggregate_payload_type)

    async def _dispatch_payload(
        self,
        callback: PushTransportPayloadCallback,
        payload: dict[str, Any],
        aggregate_payload_type: str | None,
    ) -> None:
        """Dispatch one state/event payload and update aggregate diagnostics."""
        await callback(payload)
        self._health.dispatched_payloads += 1
        data_node_samples = tuple(data_frame_node_hash_samples(payload))
        data_node_candidate_samples = _freeze_node_hash_groups(
            data_frame_node_candidate_hash_samples(payload)
        )
        self._health.last_data_node_hash_samples = data_node_samples
        self._health.last_data_node_candidate_hash_samples = data_node_candidate_samples
        if data_node_samples:
            self._health.recent_data_node_hash_samples = data_node_samples
        if data_node_candidate_samples:
            self._health.recent_data_node_candidate_hash_samples = (
                data_node_candidate_samples
            )
        self._health.last_payload_type = aggregate_payload_type or payload_type(payload)
        self._health.last_ignored_reason = None
        self._health.last_ignored_payload_type = None
        self._health.last_dispatched_at = time()

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
                await cast(_RuntimeTransportProtocol, self)._send_json(
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
            cast(_RuntimeTransportProtocol, self)._schedule_reconnect()
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
        if self._connection_was_stable():
            self._next_reconnect_delay = None
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
            if self._connection_was_stable():
                self._next_reconnect_delay = None
            await self._close_reader_websocket(
                websocket,
                close_websocket=close_websocket,
            )
            self._log_connection_closed(websocket)

        heartbeat_task = self._heartbeat_task
        if heartbeat_task is not None:
            self._heartbeat_task = None
            await _cancel_task(heartbeat_task)

    async def _close_reader_websocket(
        self,
        websocket: PushWebSocket,
        *,
        close_websocket: bool,
    ) -> None:
        """Close or detach a websocket when its reader finishes."""
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
            return
        self._websocket = None
        self._health.websocket_open = False
        self._health.disconnected_count += 1
        if self._health.last_disconnect_reason is None:
            self._health.last_disconnect_reason = "reader_ended"

    def _connection_was_stable(self) -> bool:
        """Return true when a connection lived long enough to reset backoff."""
        if self._connection_started_at is None:
            return False
        return time() - self._connection_started_at >= self._heartbeat_interval_seconds

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


def _freeze_node_hash_groups(groups: list[list[str]]) -> tuple[tuple[str, ...], ...]:
    """Return an immutable diagnostics-safe node alias hash matrix."""
    return tuple(tuple(group) for group in groups if group)


__all__ = ["PushTransportRuntimeMixin", "_cancel_task"]
