"""Connection helpers for the Yeelight Pro push transport."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from aiohttp import WSServerHandshakeError

from .push_transport_dns import WebSocketIpFallback, websocket_ip_fallback
from .push_transport_types import PushWebSocket, PushWebSocketSession

if TYPE_CHECKING:
    from .push_transport_types import PushTransportHealth


class PushTransportConnectionMixin:
    """Open WebSocket connections and record safe connection diagnostics."""

    _connect_timeout_seconds: float
    _enable_ip_fallback: bool
    _health: "PushTransportHealth"
    _proxy: str | None
    _session: PushWebSocketSession

    async def _ws_connect(self, url: str) -> PushWebSocket:
        """Open websocket with a bounded setup timeout."""
        self._health.connect_attempts += 1
        try:
            return await self._ws_connect_with_proxy(url, proxy=self._proxy)
        except WSServerHandshakeError as err:
            self._record_handshake_failure(err)
            raise
        except TypeError:
            if self._proxy is None:
                return await self._ws_connect_legacy(url)
            raise
        except Exception:
            self._health.last_handshake_status = None
            self._health.last_disconnect_reason = "connect_failed"
            raise

    async def _ws_connect_with_proxy(
        self,
        url: str,
        *,
        proxy: str | None,
    ) -> PushWebSocket:
        """Open websocket with aiohttp ws_connect proxy support."""
        fallback = await self._ip_fallback_for_url(url, proxy=proxy)
        connect_url = fallback.url if fallback is not None else url
        kwargs: dict[str, Any] = {
            "timeout": self._connect_timeout_seconds,
            "proxy": proxy,
        }
        if fallback is not None:
            kwargs["headers"] = fallback.headers
            if fallback.server_hostname is not None:
                kwargs["server_hostname"] = fallback.server_hostname
        try:
            websocket = await self._session.ws_connect(connect_url, **kwargs)
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

    async def _ip_fallback_for_url(
        self,
        url: str,
        *,
        proxy: str | None,
    ) -> WebSocketIpFallback | None:
        """Return direct-IP fallback only for non-proxied connects."""
        if proxy is not None:
            return None
        if not self._enable_ip_fallback:
            return None
        return await websocket_ip_fallback(url)

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
