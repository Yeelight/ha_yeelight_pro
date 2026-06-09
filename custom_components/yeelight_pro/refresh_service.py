"""Manual refresh service for Yeelight Pro."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import async_register_admin_service

from .const import DOMAIN
from .core.coordinator import YeelightProCoordinator

_LOGGER = logging.getLogger(__name__)

SERVICE_REFRESH = "refresh"
ATTR_ENTRY_ID = "entry_id"
ATTR_REFRESH_PRODUCT_SCHEMAS = "refresh_product_schemas"
ERROR_ENTRY_NOT_LOADED = "Requested Yeelight Pro config entry is not loaded"
ERROR_NO_REFRESHABLE_ENTRIES = "No loaded Yeelight Pro config entries could be refreshed"

SERVICE_REFRESH_SCHEMA = vol.Schema({
    vol.Optional(ATTR_ENTRY_ID): cv.string,
    vol.Optional(ATTR_REFRESH_PRODUCT_SCHEMAS, default=False): cv.boolean,
})

PostRefreshHook = Callable[[ConfigEntry, YeelightProCoordinator], Awaitable[None]]


def async_register_refresh_service(
    hass: HomeAssistant,
    post_refresh: PostRefreshHook,
) -> None:
    """Register an admin-only manual refresh service."""

    async def handle_refresh(call: ServiceCall) -> None:
        """Refresh loaded coordinators and run registry reconciliation."""
        requested_entry_id = call.data.get(ATTR_ENTRY_ID)
        refresh_product_schemas = bool(call.data.get(ATTR_REFRESH_PRODUCT_SCHEMAS))
        entries = _loaded_entries(hass, requested_entry_id)
        if requested_entry_id is not None and not entries:
            raise ServiceValidationError(ERROR_ENTRY_NOT_LOADED)

        refreshed = 0
        for entry_id, entry_data in entries.items():
            coordinator = entry_data.get("coordinator")
            entry = entry_data.get("entry")
            if not isinstance(coordinator, YeelightProCoordinator):
                continue
            if not isinstance(entry, ConfigEntry):
                _LOGGER.warning(
                    "Manual refresh skipped registry maintenance for missing entry %s",
                    entry_id,
                )
                continue
            if refresh_product_schemas:
                await coordinator.async_request_product_schema_refresh()
            else:
                await coordinator.async_request_refresh()
            await post_refresh(entry, coordinator)
            refreshed += 1

        if not refreshed:
            raise ServiceValidationError(ERROR_NO_REFRESHABLE_ENTRIES)
        _LOGGER.info(
            "Manual Yeelight Pro refresh completed for %s config entries",
            refreshed,
        )

    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_REFRESH,
        handle_refresh,
        schema=SERVICE_REFRESH_SCHEMA,
    )


def _loaded_entries(
    hass: HomeAssistant,
    requested_entry_id: str | None,
) -> dict[str, dict[str, Any]]:
    """Return loaded Yeelight Pro entry data filtered by optional entry ID."""
    domain_data = hass.data.get(DOMAIN, {})
    if not isinstance(domain_data, dict):
        return {}

    entries: dict[str, dict[str, Any]] = {}
    for entry_id, entry_data in domain_data.items():
        if requested_entry_id is not None and entry_id != requested_entry_id:
            continue
        if isinstance(entry_data, dict):
            entries[entry_id] = entry_data
    return entries
