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
    access_token = str(entry.data.get(CONF_ACCESS_TOKEN, "")).strip()
    push_base_url = _push_base_url_for_entry(entry)
    transport = YeelightPushWebSocketTransport(
        session=async_get_clientsession(hass),
        token=access_token,
        base_url=push_base_url,
    )
    manager = PushManager(coordinator, transport)
    await manager.async_start()
    return manager


def _push_base_url_for_entry(entry: ConfigEntry) -> str | None:
    """Return a private deployment push base URL override when needed."""
    data = getattr(entry, "data", None)
    if not isinstance(data, Mapping):
        return None
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


__all__ = ["async_start_live_runtime", "live_updates_enabled"]
