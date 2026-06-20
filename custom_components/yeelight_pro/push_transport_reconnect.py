"""Reconnect helpers for the Yeelight Pro push transport."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Protocol, cast

from .push_transport_types import PushTransportPayloadCallback

if TYPE_CHECKING:
    from .push_contract import PushReconnectPolicy
    from .push_transport_types import PushSleep, PushTransportHealth, PushWebSocket

_LOGGER = logging.getLogger(__name__)


class _ReconnectTransportProtocol(Protocol):
    """Concrete transport method used by the reconnect mixin."""

    async def _connect_once(self, callback: PushTransportPayloadCallback) -> None:
        """Open one websocket session and start its background tasks."""


class PushTransportReconnectMixin:
    """Schedule and run bounded WebSocket reconnect attempts."""

    _auto_reconnect: bool
    _callback: PushTransportPayloadCallback | None
    _health: "PushTransportHealth"
    _last_runtime_error_type: str | None
    _next_reconnect_delay: float | None
    _reconnect_policy: "PushReconnectPolicy"
    _reconnect_sleep: "PushSleep"
    _reconnect_task: asyncio.Task[None] | None
    _running: bool
    _websocket: "PushWebSocket | None"

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
        self._reconnect_task = asyncio.create_task(
            self._reconnect_until_connected(self._callback)
        )
        _LOGGER.info(
            "Yeelight Pro WebSocket reconnect scheduled: last_disconnect_reason=%s "
            "next_delay=%s reconnect_attempts=%s",
            self._health.last_disconnect_reason,
            planned_delay,
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
                await self._reconnect_sleep(delay)
                if not self._running or self._websocket is not None:
                    return
                try:
                    self._health.reconnect_attempts += 1
                    await cast(_ReconnectTransportProtocol, self)._connect_once(
                        callback
                    )
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
        return self._reconnect_policy.next_delay(self._next_reconnect_delay)


__all__ = ["PushTransportReconnectMixin"]
