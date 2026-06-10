"""Manual opt-in analytics refresh service for Yeelight Pro."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError, Unauthorized, UnknownUser
from homeassistant.helpers import config_validation as cv

from .analytics_contract import ANALYTICS_ENDPOINTS
from .const import DOMAIN
from .core.exceptions import AuthenticationError, CommandError, ConnectionError

SERVICE_REFRESH_ANALYTICS = "refresh_analytics"
ATTR_ENTRY_ID = "entry_id"
ATTR_ENDPOINT = "endpoint"
ATTR_DATE_CODE = "date_code"
ATTR_START_DATE = "start_date"
ATTR_END_DATE = "end_date"
ATTR_AREA_ID = "area_id"

ERROR_ENTRY_NOT_LOADED = "Requested Yeelight Pro config entry is not loaded"
ERROR_ANALYTICS_DISABLED = "Yeelight Pro analytics runtime is disabled"
ERROR_INVALID_ANALYTICS_REQUEST = "Invalid Yeelight Pro analytics request"
ERROR_NO_ANALYTICS_TARGETS = "No loaded Yeelight Pro analytics runtime can refresh"
ERROR_ANALYTICS_AUTH = "Yeelight Pro analytics authentication failed"
ERROR_ANALYTICS_REFRESH = "Yeelight Pro analytics refresh failed"
ERROR_ADMIN_CONTEXT_REQUIRED = "Yeelight Pro analytics refresh requires an admin user context"

SERVICE_REFRESH_ANALYTICS_SCHEMA = vol.Schema({
    vol.Optional(ATTR_ENTRY_ID): cv.string,
    vol.Required(ATTR_ENDPOINT): vol.In(tuple(ANALYTICS_ENDPOINTS)),
    vol.Optional(ATTR_DATE_CODE): cv.string,
    vol.Optional(ATTR_START_DATE): cv.string,
    vol.Optional(ATTR_END_DATE): cv.string,
    vol.Optional(ATTR_AREA_ID): vol.Any(int, cv.string),
})


def async_register_analytics_service(hass: HomeAssistant) -> None:
    """Register the aggregate analytics refresh response service."""

    async def handle_refresh_analytics(call: ServiceCall) -> dict[str, Any]:
        """Refresh one documented analytics endpoint for loaded entries."""
        await _async_require_admin(hass, call)
        requested_entry_id = call.data.get(ATTR_ENTRY_ID)
        targets = _loaded_analytics_targets(hass, requested_entry_id)
        if requested_entry_id is not None and not targets:
            raise ServiceValidationError(ERROR_ENTRY_NOT_LOADED)
        if not targets:
            raise ServiceValidationError(ERROR_NO_ANALYTICS_TARGETS)

        entries = []
        for entry_id, coordinator in targets:
            try:
                snapshot = await coordinator.async_refresh_analytics(
                    endpoint_key=call.data[ATTR_ENDPOINT],
                    date_code=call.data.get(ATTR_DATE_CODE),
                    start_date=call.data.get(ATTR_START_DATE),
                    end_date=call.data.get(ATTR_END_DATE),
                    area_id=call.data.get(ATTR_AREA_ID),
                )
            except CommandError:
                raise ServiceValidationError(ERROR_INVALID_ANALYTICS_REQUEST) from None
            except AuthenticationError:
                raise HomeAssistantError(ERROR_ANALYTICS_AUTH) from None
            except ConnectionError:
                raise HomeAssistantError(ERROR_ANALYTICS_REFRESH) from None
            entries.append({"entry_id": entry_id, **snapshot.as_dict()})

        return {
            "action": "refresh_analytics",
            "refreshed_entries": len(entries),
            "entries": entries,
        }

    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH_ANALYTICS,
        handle_refresh_analytics,
        schema=SERVICE_REFRESH_ANALYTICS_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )


async def _async_require_admin(hass: HomeAssistant, call: ServiceCall) -> None:
    """Apply Home Assistant's admin-only service boundary."""
    if call.context.user_id is None:
        raise Unauthorized(
            context=call.context,
            perm_category=DOMAIN,
            permission=ERROR_ADMIN_CONTEXT_REQUIRED,
        )
    user = await hass.auth.async_get_user(call.context.user_id)
    if user is None:
        raise UnknownUser(context=call.context)
    if not user.is_admin:
        raise Unauthorized(context=call.context)


def _loaded_analytics_targets(
    hass: HomeAssistant,
    requested_entry_id: str | None,
) -> list[tuple[str, Any]]:
    """Return loaded coordinators with analytics runtime enabled."""
    domain_data = hass.data.get(DOMAIN, {})
    if not isinstance(domain_data, dict):
        return []
    targets: list[tuple[str, Any]] = []
    for entry_id, entry_data in domain_data.items():
        if requested_entry_id is not None and entry_id != requested_entry_id:
            continue
        if not isinstance(entry_data, dict):
            continue
        coordinator = entry_data.get("coordinator")
        if coordinator is None:
            continue
        if not bool(getattr(coordinator, "analytics_runtime_enabled", False)):
            if requested_entry_id is not None:
                raise ServiceValidationError(ERROR_ANALYTICS_DISABLED)
            continue
        if not callable(getattr(coordinator, "async_refresh_analytics", None)):
            continue
        targets.append((entry_id, coordinator))
    return targets
