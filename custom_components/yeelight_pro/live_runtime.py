"""Runtime wiring for Yeelight cloud WebSocket push updates."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_ACCESS_TOKEN,
    CONF_CLOUD_REGION,
    CONF_CONNECTION_MODE,
    CONF_LIVE_UPDATES,
    CONF_PRIVATE_DOMAIN,
    CONF_PRIVATE_PUSH_DOMAIN,
    CLOUD_REGION_PUSH_BASE_URLS,
    DEFAULT_CLOUD_REGION,
    CONNECTION_MODE_CLOUD,
    CONNECTION_MODE_PRIVATE,
    DEFAULT_LIVE_UPDATES,
)
from .deployment_urls import deployment_push_base_url
from .entry_migration import normalize_entry_data
from .push_manager import PushManager
from .push_transport import YeelightPushWebSocketTransport


def live_updates_enabled(entry: ConfigEntry) -> bool:
    """Return whether cloud WebSocket live updates are enabled for this entry."""
    data = getattr(entry, "data", None)
    mode = data.get(CONF_CONNECTION_MODE) if isinstance(data, Mapping) else None
    if mode not in {CONNECTION_MODE_CLOUD, CONNECTION_MODE_PRIVATE}:
        return False
    options = getattr(entry, "options", None)
    if not isinstance(options, Mapping):
        return DEFAULT_LIVE_UPDATES
    return bool(options.get(CONF_LIVE_UPDATES, DEFAULT_LIVE_UPDATES))


async def async_start_live_runtime(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: Any,
) -> PushManager | None:
    """Start the Yeelight WebSocket push runtime when explicitly enabled."""
    if not live_updates_enabled(entry):
        return None
    runtime_data = _runtime_entry_data(entry, coordinator)
    access_token = _push_access_token(runtime_data, coordinator)
    push_base_url = _push_base_url_for_data(runtime_data)
    transport = YeelightPushWebSocketTransport(
        session=async_get_clientsession(hass),
        token=access_token,
        token_provider=lambda: _push_access_token(
            _runtime_entry_data(entry, coordinator),
            coordinator,
        ),
        base_url=push_base_url,
        enable_ip_fallback=_push_ip_fallback_enabled(runtime_data),
    )
    manager = PushManager(coordinator, transport)
    await manager.async_start()
    return manager


def _runtime_entry_data(entry: ConfigEntry, coordinator: Any) -> dict[str, Any]:
    """Return the freshest normalized entry data available to live runtime."""
    entry_data = getattr(entry, "data", None)
    data = dict(entry_data) if isinstance(entry_data, Mapping) else {}
    coordinator_data = getattr(coordinator, "entry_data", None)
    if isinstance(coordinator_data, Mapping):
        data.update(coordinator_data)
    return normalize_entry_data(data)


def _push_access_token(data: Mapping[str, Any], coordinator: Any) -> str:
    """Return the current access token used by WebSocket push auth."""
    client = getattr(coordinator, "client", None)
    token = getattr(client, "access_token", None)
    if isinstance(token, str) and token.strip():
        return token.strip()
    return str(data.get(CONF_ACCESS_TOKEN, "")).strip()


def _push_base_url_for_entry(entry: ConfigEntry) -> str | None:
    """Return a private deployment push base URL override when needed."""
    data = getattr(entry, "data", None)
    if not isinstance(data, Mapping):
        return None
    return _push_base_url_for_data(data)


def _push_base_url_for_data(data: Mapping[str, Any]) -> str | None:
    """Return a push base URL from normalized config-entry data."""
    mode = data.get(CONF_CONNECTION_MODE)
    if mode == CONNECTION_MODE_CLOUD:
        region = str(data.get(CONF_CLOUD_REGION) or DEFAULT_CLOUD_REGION)
        return CLOUD_REGION_PUSH_BASE_URLS.get(
            region,
            CLOUD_REGION_PUSH_BASE_URLS[DEFAULT_CLOUD_REGION],
        )
    if mode != CONNECTION_MODE_PRIVATE:
        return None
    private_push_domain = data.get(CONF_PRIVATE_PUSH_DOMAIN)
    if isinstance(private_push_domain, str) and private_push_domain.strip():
        return deployment_push_base_url(private_push_domain)
    private_domain = data.get(CONF_PRIVATE_DOMAIN)
    if not isinstance(private_domain, str) or not private_domain.strip():
        return None
    return deployment_push_base_url(private_domain)


def _push_ip_fallback_enabled(data: Mapping[str, Any]) -> bool:
    """Return whether private runtime should bypass fake-ip DNS automatically."""
    return data.get(CONF_CONNECTION_MODE) == CONNECTION_MODE_PRIVATE


__all__ = ["async_start_live_runtime", "live_updates_enabled"]
