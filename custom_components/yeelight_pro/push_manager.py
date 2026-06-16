"""No-network lifecycle manager for Yeelight Pro push transports."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
import logging
from time import time
from typing import Any, Protocol

PushPayloadCallback = Callable[[Mapping[str, Any]], Awaitable[object]]
_LOGGER = logging.getLogger(__name__)


class PushTransport(Protocol):
    """Transport contract used by future push implementations."""

    @property
    def last_start_error_type(self) -> str | None:
        """Return the aggregate error type from a recoverable start failure."""

    @property
    def last_runtime_error_type(self) -> str | None:
        """Return the aggregate error type from a background runtime failure."""

    async def async_start(self, callback: PushPayloadCallback) -> None:
        """Start receiving push payloads and forward them to callback."""

    async def async_stop(self) -> None:
        """Stop receiving push payloads."""


@dataclass(slots=True)
class PushHealth:
    """Diagnostics-safe aggregate health for the push manager."""

    running: bool = False
    started_count: int = 0
    stopped_count: int = 0
    handled_payloads: int = 0
    last_error_type: str | None = None
    last_payload_type: str | None = None
    last_payload_at: float | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return an aggregate-only diagnostics payload."""
        return {
            "running": self.running,
            "started_count": self.started_count,
            "stopped_count": self.stopped_count,
            "handled_payloads": self.handled_payloads,
            "last_error_type": self.last_error_type,
            "last_payload_type": self.last_payload_type,
            "last_payload_at": self.last_payload_at,
        }


class PushManager:
    """Manage an injected push transport without opening network connections."""

    def __init__(self, coordinator: Any, transport: PushTransport) -> None:
        """Initialize the manager with a coordinator and injected transport."""
        self._coordinator = coordinator
        self._transport = transport
        self._health = PushHealth()
        self._transport_started = False

    @property
    def health(self) -> PushHealth:
        """Return diagnostics-safe aggregate push health."""
        self._sync_transport_runtime_error()
        return self._health

    async def async_start(self) -> None:
        """Start the injected transport once."""
        if self._health.running or self._transport_started:
            return
        self._health.running = True
        self._health.last_error_type = None
        try:
            await self._transport.async_start(self._handle_payload)
        except Exception as err:
            self._health.running = False
            self._health.last_error_type = type(err).__name__
            raise
        self._transport_started = True
        self._health.started_count += 1
        transport_start_error = getattr(self._transport, "last_start_error_type", None)
        if transport_start_error is not None:
            self._health.last_error_type = transport_start_error
        self._sync_transport_runtime_error()
        _LOGGER.info(
            "Started Yeelight Pro WebSocket push runtime: recoverable_start_error=%s",
            self._health.last_error_type,
        )

    async def async_stop(self) -> None:
        """Stop the injected transport once."""
        if not self._health.running and not self._transport_started:
            return
        self._health.running = False
        if not self._transport_started:
            return
        had_error = False
        try:
            await self._transport.async_stop()
        except Exception as err:
            self._health.last_error_type = type(err).__name__
            had_error = True
            raise
        finally:
            if not had_error:
                self._transport_started = False
                self._health.last_error_type = None
                self._health.stopped_count += 1

    async def _handle_payload(self, payload: Mapping[str, Any]) -> object | None:
        """Forward payloads to the coordinator while the manager is running."""
        if not self._health.running:
            return None
        try:
            result = await self._coordinator.async_handle_push_payload(payload)
        except Exception as err:
            self._health.last_error_type = type(err).__name__
            return None
        self._health.handled_payloads += 1
        self._health.last_payload_type = _payload_type(payload)
        self._health.last_payload_at = time()
        self._health.last_error_type = None
        _LOGGER.debug(
            "Handled Yeelight Pro WebSocket push payload: type=%s count=%s",
            self._health.last_payload_type,
            self._health.handled_payloads,
        )
        return result

    def _sync_transport_runtime_error(self) -> None:
        """Copy transport runtime error type into aggregate health."""
        transport_error = getattr(self._transport, "last_runtime_error_type", None)
        if isinstance(transport_error, str) and transport_error:
            self._health.last_error_type = transport_error


def _payload_type(payload: Mapping[str, Any]) -> str | None:
    """Return a documented aggregate payload type without raw payload data."""
    value = payload.get("type")
    if isinstance(value, str) and value:
        return value
    data = payload.get("data")
    if isinstance(data, Mapping):
        nested = data.get("type")
        if isinstance(nested, str) and nested:
            return nested
    return None


__all__ = [
    "PushHealth",
    "PushManager",
    "PushPayloadCallback",
    "PushTransport",
]
