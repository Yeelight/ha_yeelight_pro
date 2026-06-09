"""Runtime wiring for Yeelight cloud WebSocket push updates."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_ACCESS_TOKEN, CONF_LIVE_UPDATES
from .push_manager import PushManager
from .push_transport import YeelightPushWebSocketTransport


def live_updates_enabled(entry: ConfigEntry) -> bool:
    """Return whether cloud WebSocket live updates are enabled for this entry."""
    options = getattr(entry, "options", None)
    return bool(options.get(CONF_LIVE_UPDATES, False)) if isinstance(options, Mapping) else False


async def async_start_live_runtime(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: Any,
) -> PushManager | None:
    """Start the Yeelight WebSocket push runtime when explicitly enabled."""
    if not live_updates_enabled(entry):
        return None
    access_token = str(entry.data.get(CONF_ACCESS_TOKEN, "")).strip()
    transport = YeelightPushWebSocketTransport(
        session=async_get_clientsession(hass),
        token=access_token,
    )
    manager = PushManager(coordinator, transport)
    await manager.async_start()
    return manager


__all__ = ["async_start_live_runtime", "live_updates_enabled"]
