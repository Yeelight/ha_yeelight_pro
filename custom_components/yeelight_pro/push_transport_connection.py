"""Connection helpers for the Yeelight Pro push transport."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aiohttp import WSServerHandshakeError

from .push_transport_types import PushWebSocket, PushWebSocketSession

if TYPE_CHECKING:
    from .push_transport_types import PushTransportHealth


class PushTransportConnectionMixin:
    """Open WebSocket connections and record safe connection diagnostics."""

    _connect_timeout_seconds: float
    _health: "PushTransportHealth"
    _session: PushWebSocketSession

    async def _ws_connect(self, url: str) -> PushWebSocket:
        """Open websocket with a bounded setup timeout."""
        self._health.connect_attempts += 1
        try:
            return await self._ws_connect_direct(url)
        except WSServerHandshakeError as err:
            self._record_handshake_failure(err)
            raise
        except TypeError:
            return await self._ws_connect_legacy(url)
        except Exception:
            self._health.last_handshake_status = None
            self._health.last_disconnect_reason = "connect_failed"
            raise

    async def _ws_connect_direct(self, url: str) -> PushWebSocket:
        """Open websocket directly with a bounded setup timeout."""
        try:
            websocket = await self._session.ws_connect(
                url,
                timeout=self._connect_timeout_seconds,
            )
            self._health.last_handshake_status = None
            self._health.last_disconnect_reason = None
            return websocket
        except WSServerHandshakeError as err:
            self._record_handshake_failure(err)
            raise
        except Exception:
            self._health.last_handshake_status = None
            self._health.last_disconnect_reason = "connect_failed"
            raise

    async def _ws_connect_legacy(self, url: str) -> PushWebSocket:
        """Fallback for lightweight sessions that do not accept kwargs."""
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

    def _record_handshake_failure(self, err: WSServerHandshakeError) -> None:
        """Record diagnostics-safe WebSocket handshake metadata."""
        status = getattr(err, "status", None)
        self._health.last_handshake_status = status if isinstance(status, int) else None
        self._health.last_disconnect_reason = "handshake_failed"


__all__ = ["PushTransportConnectionMixin"]
