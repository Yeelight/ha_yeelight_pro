"""Shared helpers for manual refresh service tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.core.coordinator import YeelightProCoordinator


def refresh_entry(entry_id: str) -> MagicMock:
    """Build a config entry test double."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = entry_id
    return entry


def refresh_coordinator(hass: HomeAssistant) -> MagicMock:
    """Build a coordinator test double."""
    coordinator = MagicMock(spec=YeelightProCoordinator)
    coordinator.hass = hass
    coordinator.async_request_refresh = AsyncMock()
    coordinator.async_request_product_schema_refresh = AsyncMock()
    coordinator.topology_generation = 1
    return coordinator
