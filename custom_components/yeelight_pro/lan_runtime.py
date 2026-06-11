"""Runtime TCP client for Yeelight Pro local gateway control."""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Mapping
from contextlib import suppress
from dataclasses import dataclass, field
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import HomeAssistantError

from .const import (
    CONF_LOCAL_GATEWAY_CONTROL,
    CONF_LOCAL_GATEWAY_HOST,
    CONF_LOCAL_GATEWAY_PORT,
    DEFAULT_LOCAL_GATEWAY_PORT,
)
from .lan_contract import (
    LAN_FRAME_SEPARATOR,
    LanMessageBuilder,
    decode_lan_frames,
    encode_lan_frame,
    is_lan_ack_response,
)
from .lan_discovery import async_discover_lan_gateway

_LOGGER = logging.getLogger(__name__)

LanPayloadCallback = Callable[[Mapping[str, Any]], Awaitable[object]]

# 连接与读取超时
_LAN_CONNECT_TIMEOUT = 10.0
_LAN_READ_TIMEOUT = 660.0  # 11分钟（协议规定网关每10分钟全量同步一次）
_LAN_ACK_TIMEOUT = 5.0

# 重连退避参数（秒）
_LAN_RECONNECT_DELAY_MIN = 2.0
_LAN_RECONNECT_DELAY_MAX = 60.0


@dataclass(slots=True)
class LanRuntimeHealth:
    """Diagnostics-safe aggregate health for the LAN runtime."""

    running: bool = False
    connected: bool = False
    sent_count: int = 0
    received_count: int = 0
    ack_count: int = 0
    ack_timeout_count: int = 0
    reconnect_attempts: int = 0
    last_error_type: str | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return aggregate LAN runtime health."""
        return {
            "running": self.running,
            "connected": self.connected,
            "sent_count": self.sent_count,
            "received_count": self.received_count,
            "ack_count": self.ack_count,
            "ack_timeout_count": self.ack_timeout_count,
            "reconnect_attempts": self.reconnect_attempts,
            "last_error_type": self.last_error_type,
        }


@dataclass(slots=True)
class LanGatewayRuntime:
    """Manage one TCP connection to a Yeelight Pro LAN gateway."""

    host: str
    port: int = DEFAULT_LOCAL_GATEWAY_PORT
    open_connection: Callable[..., Awaitable[tuple[Any, Any]]] = asyncio.open_connection
    _builder: LanMessageBuilder = field(default_factory=LanMessageBuilder)
    _reader: Any | None = None
    _writer: Any | None = None
    _reader_task: asyncio.Task[None] | None = None
    _reconnect_task: asyncio.Task[None] | None = None
    _callback: LanPayloadCallback | None = field(default=None, repr=False)
    _health: LanRuntimeHealth = field(default_factory=LanRuntimeHealth)
    _reconnect_delay: float = _LAN_RECONNECT_DELAY_MIN
    # ACK 响应关联：消息 ID → asyncio.Future
    _pending_acks: dict[int, asyncio.Future[dict[str, Any]]] = field(
        default_factory=dict, repr=False
    )

    @property
    def health(self) -> LanRuntimeHealth:
        """Return diagnostics-safe runtime health."""
        return self._health

    async def async_start(self, callback: LanPayloadCallback) -> None:
        """Open TCP connection and start dispatching received frames."""
        if self._health.running:
            return
        self._health.running = True
        self._callback = callback
        try:
            await self._connect()
        except Exception as err:
            self._health.running = False
            self._callback = None
            self._health.last_error_type = type(err).__name__
            raise
        self._reader_task = asyncio.create_task(self._read_loop())

    async def async_stop(self) -> None:
        """Stop reader/reconnect tasks and close the TCP connection."""
        self._health.running = False
        self._callback = None
        self._flush_pending_acks("LAN runtime stopped")
        # 取消重连任务
        reconnect = self._reconnect_task
        self._reconnect_task = None
        if reconnect is not None and not reconnect.done():
            reconnect.cancel()
            with suppress(asyncio.CancelledError):
                await reconnect
        # 取消读取任务
        task = self._reader_task
        self._reader_task = None
        if task is not None and not task.done():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        # 关闭 writer
        await self._close_writer()

    async def async_get_topology(self) -> None:
        """Send a documented topology request over the active connection."""
        await self.async_send(self._builder.get_topology())

    async def async_set_properties(
        self,
        nodes: list[Mapping[str, Any]],
        *,
        scenes: list[Mapping[str, Any]] | None = None,
    ) -> dict[str, Any] | None:
        """Send LAN property control frame and wait for ACK response.

        返回网关 ACK 数据（含 result 字段），超时返回 None。
        """
        message = self._builder.set_properties(nodes, scenes=scenes)
        return await self.async_send_and_wait(message)

    async def async_send(self, message: Mapping[str, Any]) -> None:
        """Write one CRLF-delimited JSON frame without waiting for response."""
        writer = self._writer
        if writer is None:
            raise HomeAssistantError("Yeelight Pro LAN gateway is not connected")
        writer.write(encode_lan_frame(message))
        await writer.drain()
        self._health.sent_count += 1

    async def async_send_and_wait(
        self,
        message: Mapping[str, Any],
        timeout: float = _LAN_ACK_TIMEOUT,
    ) -> dict[str, Any] | None:
        """Write a frame and wait for the gateway ACK response.

        使用消息 ID 关联请求和响应。超时返回 None 但不抛异常。
        """
        message_id = message.get("id")
        if not isinstance(message_id, int):
            # 无法关联 ACK，退化为 fire-and-forget
            await self.async_send(message)
            return None

        future: asyncio.Future[dict[str, Any]] = asyncio.get_event_loop().create_future()
        self._pending_acks[message_id] = future
        try:
            await self.async_send(message)
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self._health.ack_timeout_count += 1
            _LOGGER.warning(
                "LAN ACK timeout for message %d (%s)",
                message_id,
                message.get("method", "?"),
            )
            return None
        finally:
            self._pending_acks.pop(message_id, None)

    # ------------------------------------------------------------------
    # 内部：连接与关闭
    # ------------------------------------------------------------------

    async def _connect(self) -> None:
        """Establish TCP connection with timeout."""
        self._reader, self._writer = await asyncio.wait_for(
            self.open_connection(self.host, self.port),
            timeout=_LAN_CONNECT_TIMEOUT,
        )
        self._health.connected = True
        self._reconnect_delay = _LAN_RECONNECT_DELAY_MIN
        _LOGGER.info("LAN gateway connected: %s:%s", self.host, self.port)

    async def _close_writer(self) -> None:
        """Close the TCP writer if present."""
        writer = self._writer
        self._writer = None
        self._reader = None
        self._health.connected = False
        if writer is None:
            return
        writer.close()
        wait_closed = getattr(writer, "wait_closed", None)
        if callable(wait_closed):
            await wait_closed() # pyright: ignore[reportGeneralTypeIssues]

    def _flush_pending_acks(self, reason: str) -> None:
        """Cancel all pending ACK futures on disconnect."""
        for msg_id, future in self._pending_acks.items():
            if not future.done():
                future.cancel()
                _LOGGER.debug("Flushed pending ACK %d: %s", msg_id, reason)
        self._pending_acks.clear()

    # ------------------------------------------------------------------
    # 内部：读取循环（带超时 + ACK 匹配 + callback 隔离）
    # ------------------------------------------------------------------

    async def _read_loop(self) -> None:
        """Read CRLF-delimited frames from the gateway."""
        buffer = ""
        try:
            while self._health.running and self._reader is not None:
                try:
                    data = await asyncio.wait_for(
                        self._reader.read(4096),
                        timeout=_LAN_READ_TIMEOUT,
                    )
                except asyncio.TimeoutError:
                    _LOGGER.warning("LAN gateway read timeout, triggering reconnect")
                    break
                if not data:
                    _LOGGER.debug("LAN gateway connection closed by peer")
                    break
                buffer += data.decode("utf-8")
                if LAN_FRAME_SEPARATOR not in buffer:
                    continue
                parts = buffer.split(LAN_FRAME_SEPARATOR)
                buffer = parts.pop()
                for payload in decode_lan_frames(LAN_FRAME_SEPARATOR.join(parts)):
                    self._health.received_count += 1
                    self._try_resolve_ack(payload)
                    # callback 异常隔离：不退出读取循环
                    try:
                        await self._callback(payload) if self._callback else None
                    except Exception as err:
                        _LOGGER.warning(
                            "LAN callback error (frame ignored): %s",
                            type(err).__name__,
                        )
        except asyncio.CancelledError:
            raise
        except Exception as err:
            self._health.last_error_type = type(err).__name__
            _LOGGER.warning("LAN read loop error: %s", err)
        finally:
            self._health.connected = False
            self._flush_pending_acks("read loop exited")
            if self._health.running:
                self._schedule_reconnect()

    def _try_resolve_ack(self, payload: Mapping[str, Any]) -> None:
        """Match incoming ACK response to a pending future."""
        if not is_lan_ack_response(payload):
            return
        message_id = payload.get("id")
        if not isinstance(message_id, int):
            return
        future = self._pending_acks.get(message_id)
        if future is not None and not future.done():
            future.set_result(dict(payload))
            self._health.ack_count += 1
            result = payload.get("result", "?")
            _LOGGER.debug("LAN ACK resolved: id=%d result=%s", message_id, result)

    # ------------------------------------------------------------------
    # 内部：自动重连（指数退避）
    # ------------------------------------------------------------------

    def _schedule_reconnect(self) -> None:
        """Schedule an async reconnection loop if not already running."""
        if not self._health.running:
            return
        if self._reconnect_task is not None and not self._reconnect_task.done():
            return
        self._reconnect_task = asyncio.create_task(self._reconnect_loop())

    async def _reconnect_loop(self) -> None:
        """Reconnect with bounded exponential backoff until stopped."""
        current_task = asyncio.current_task()
        try:
            while self._health.running:
                delay = self._reconnect_delay
                self._reconnect_delay = min(
                    self._reconnect_delay * 2, _LAN_RECONNECT_DELAY_MAX
                )
                self._health.reconnect_attempts += 1
                _LOGGER.info(
                    "LAN gateway reconnecting in %.1fs (attempt %d)...",
                    delay,
                    self._health.reconnect_attempts,
                )
                await asyncio.sleep(delay)
                if not self._health.running:
                    return
                await self._close_writer()
                try:
                    await self._connect()
                    _LOGGER.info("LAN gateway reconnected successfully")
                    self._reader_task = asyncio.create_task(self._read_loop())
                    return
                except asyncio.CancelledError:
                    raise
                except Exception as err:
                    self._health.last_error_type = type(err).__name__
                    _LOGGER.warning(
                        "LAN gateway reconnect failed: %s", type(err).__name__
                    )
                    continue
        except (asyncio.CancelledError, GeneratorExit):
            raise
        finally:
            if self._reconnect_task is current_task:
                self._reconnect_task = None


def lan_runtime_options(entry: ConfigEntry) -> tuple[bool, str, int]:
    """Return normalized LAN runtime option values."""
    options = getattr(entry, "options", None)
    if not isinstance(options, Mapping):
        return False, "", DEFAULT_LOCAL_GATEWAY_PORT
    enabled = bool(options.get(CONF_LOCAL_GATEWAY_CONTROL, False))
    host = str(options.get(CONF_LOCAL_GATEWAY_HOST, "")).strip()
    port = int(options.get(CONF_LOCAL_GATEWAY_PORT, DEFAULT_LOCAL_GATEWAY_PORT))
    return enabled, host, port


async def async_start_lan_runtime(
    entry: ConfigEntry,
    coordinator: Any,
) -> LanGatewayRuntime | None:
    """Start LAN gateway runtime when explicitly configured."""
    enabled, host, port = lan_runtime_options(entry)
    if not enabled:
        return None
    if not host:
        discovered = await async_discover_lan_gateway()
        if discovered is None:
            raise HomeAssistantError("Yeelight Pro LAN gateway host is required")
        host = discovered.ip
    runtime = LanGatewayRuntime(host=host, port=port)
    await runtime.async_start(coordinator.async_handle_lan_payload)
    await runtime.async_get_topology()
    return runtime


__all__ = [
    "LanGatewayRuntime",
    "LanPayloadCallback",
    "LanRuntimeHealth",
    "async_start_lan_runtime",
    "lan_runtime_options",
]
