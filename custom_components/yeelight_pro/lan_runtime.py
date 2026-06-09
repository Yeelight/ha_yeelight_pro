"""Runtime TCP client for Yeelight Pro local gateway control."""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
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
)
from .lan_discovery import async_discover_lan_gateway

LanPayloadCallback = Callable[[Mapping[str, Any]], Awaitable[object]]


@dataclass(slots=True)
class LanRuntimeHealth:
    """Diagnostics-safe aggregate health for the LAN runtime."""

    running: bool = False
    connected: bool = False
    sent_count: int = 0
    received_count: int = 0
    last_error_type: str | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return aggregate LAN runtime health."""
        return {
            "running": self.running,
            "connected": self.connected,
            "sent_count": self.sent_count,
            "received_count": self.received_count,
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
    _health: LanRuntimeHealth = field(default_factory=LanRuntimeHealth)

    @property
    def health(self) -> LanRuntimeHealth:
        """Return diagnostics-safe runtime health."""
        return self._health

    async def async_start(self, callback: LanPayloadCallback) -> None:
        """Open TCP connection and start dispatching received frames."""
        if self._health.running:
            return
        self._health.running = True
        self._health.last_error_type = None
        try:
            self._reader, self._writer = await self.open_connection(
                self.host,
                self.port,
            )
        except Exception as err:
            self._health.running = False
            self._health.last_error_type = type(err).__name__
            raise
        self._health.connected = True
        self._reader_task = asyncio.create_task(self._read_loop(callback))

    async def async_stop(self) -> None:
        """Stop the reader task and close the TCP connection."""
        self._health.running = False
        task = self._reader_task
        self._reader_task = None
        if task is not None and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        writer = self._writer
        self._writer = None
        self._reader = None
        self._health.connected = False
        if writer is None:
            return
        writer.close()
        wait_closed = getattr(writer, "wait_closed", None)
        if callable(wait_closed):
            await wait_closed()

    async def async_get_topology(self) -> None:
        """Send a documented topology request over the active connection."""
        await self.async_send(self._builder.get_topology())

    async def async_set_properties(
        self,
        nodes: list[Mapping[str, Any]],
        *,
        scenes: list[Mapping[str, Any]] | None = None,
    ) -> None:
        """Send documented LAN property control frame."""
        await self.async_send(self._builder.set_properties(nodes, scenes=scenes))

    async def async_send(self, message: Mapping[str, Any]) -> None:
        """Write one CRLF-delimited JSON frame."""
        writer = self._writer
        if writer is None:
            raise HomeAssistantError("Yeelight Pro LAN gateway is not connected")
        writer.write(encode_lan_frame(message))
        await writer.drain()
        self._health.sent_count += 1

    async def _read_loop(self, callback: LanPayloadCallback) -> None:
        """Read CRLF-delimited frames from the gateway."""
        buffer = ""
        try:
            while self._health.running and self._reader is not None:
                data = await self._reader.read(4096)
                if not data:
                    break
                buffer += data.decode("utf-8")
                if LAN_FRAME_SEPARATOR not in buffer:
                    continue
                parts = buffer.split(LAN_FRAME_SEPARATOR)
                buffer = parts.pop()
                for payload in decode_lan_frames(LAN_FRAME_SEPARATOR.join(parts)):
                    self._health.received_count += 1
                    await callback(payload)
        except asyncio.CancelledError:
            raise
        except Exception as err:
            self._health.last_error_type = type(err).__name__
        finally:
            self._health.connected = False


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
