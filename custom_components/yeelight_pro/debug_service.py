"""Debug services for Yeelight Pro."""
from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import async_register_admin_service

from .const import (
    ATTR_COMPONENT_ID,
    ATTR_EVENT_ATTRIBUTES,
    ATTR_EVENT_TYPE,
    ATTR_SOURCE_DEVICE_ID,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)
ATTR_ENTRY_ID = "entry_id"

SERVICE_DEBUG_EMIT_EVENT_SCHEMA = vol.Schema({
    vol.Optional(ATTR_ENTRY_ID): cv.string,
    vol.Required(ATTR_SOURCE_DEVICE_ID): vol.Any(int, cv.string),
    vol.Required(ATTR_COMPONENT_ID): cv.string,
    vol.Required(ATTR_EVENT_TYPE): cv.string,
    vol.Optional(ATTR_EVENT_ATTRIBUTES, default={}): dict,
})


def async_register_debug_event_service(hass: HomeAssistant) -> None:
    """Register the guarded debug event emit service."""

    async def handle_debug_emit_event(call: ServiceCall) -> None:
        """向 HA 事件总线发射调试 Yeelight Pro 设备事件。"""
        entry_id = call.data.get(ATTR_ENTRY_ID)
        coordinator = _debug_coordinator(hass, entry_id=entry_id)
        if coordinator is None:
            raise HomeAssistantError("Yeelight Pro debug mode is disabled or entry_id is invalid")
        event = await coordinator.async_handle_runtime_event(call.data)
        _LOGGER.info(
            "Emitted debug Yeelight Pro event: event_type=%s",
            event.event_type,
        )

    async_register_admin_service(
        hass,
        DOMAIN,
        "debug_emit_event",
        handle_debug_emit_event,
        schema=SERVICE_DEBUG_EMIT_EVENT_SCHEMA,
    )


def _debug_coordinator(hass: HomeAssistant, *, entry_id: str | None = None) -> Any | None:
    """返回启用调试模式的 coordinator，可按 entry_id 限定."""
    domain_data = hass.data.get(DOMAIN, {})
    if entry_id is not None:
        data = domain_data.get(entry_id)
        return _coordinator_if_debug(data)

    for data in domain_data.values():
        coordinator = _coordinator_if_debug(data)
        if coordinator is not None:
            return coordinator
    return None


def _coordinator_if_debug(data: Any) -> Any | None:
    """返回启用 debug 的 runtime coordinator."""
    if isinstance(data, Mapping):
        coordinator = data.get("coordinator")
        if coordinator is not None and bool(coordinator.debug_mode):
            return coordinator
    return None
