"""Explicit registry cleanup service for Yeelight Pro."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ServiceValidationError, Unauthorized, UnknownUser
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .entity_lifecycle import (
    EntityRegistryCleanupAudit,
    EntityRegistryCleanupPreview,
    async_disable_stale_registry_entities,
    async_preview_stale_registry_cleanup,
)

_LOGGER = logging.getLogger(__name__)

SERVICE_CLEANUP_REGISTRY = "cleanup_registry"
ATTR_ENTRY_ID = "entry_id"
ATTR_CONFIRM = "confirm"
ATTR_AUDIT_ID = "audit_id"

ERROR_ENTRY_NOT_LOADED = "Requested Yeelight Pro config entry is not loaded"
ERROR_CONFIRM_REQUIRES_ENTRY = "Registry cleanup confirmation requires entry_id"
ERROR_CONFIRM_REQUIRES_AUDIT = "Registry cleanup confirmation requires audit_id"
ERROR_AUDIT_MISMATCH = "Registry cleanup audit_id does not match current dry-run result"
ERROR_NO_CLEANUP_TARGETS = "No loaded Yeelight Pro config entries can be cleaned up"

SERVICE_CLEANUP_REGISTRY_SCHEMA = vol.Schema({
    vol.Optional(ATTR_ENTRY_ID): cv.string,
    vol.Optional(ATTR_CONFIRM, default=False): cv.boolean,
    vol.Optional(ATTR_AUDIT_ID): cv.string,
})


def async_register_registry_cleanup_service(hass: HomeAssistant) -> None:
    """Register the explicit stale registry cleanup response service."""

    async def handle_cleanup_registry(call: ServiceCall) -> dict[str, Any]:
        """Dry-run or confirm stale entity cleanup."""
        await _async_require_admin(hass, call)
        requested_entry_id = call.data.get(ATTR_ENTRY_ID)
        confirm = bool(call.data.get(ATTR_CONFIRM))
        audit_id = call.data.get(ATTR_AUDIT_ID)
        targets = _loaded_cleanup_targets(hass, requested_entry_id)
        if requested_entry_id is not None and not targets:
            raise ServiceValidationError(ERROR_ENTRY_NOT_LOADED)

        if confirm:
            return await _async_confirm_cleanup(targets, requested_entry_id, audit_id)
        return await _async_dry_run_cleanup(targets)

    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEANUP_REGISTRY,
        handle_cleanup_registry,
        schema=SERVICE_CLEANUP_REGISTRY_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )


async def _async_require_admin(hass: HomeAssistant, call: ServiceCall) -> None:
    """Apply the same admin boundary as HA admin service helpers."""
    if call.context.user_id is None:
        return
    user = await hass.auth.async_get_user(call.context.user_id)
    if user is None:
        raise UnknownUser(context=call.context)
    if not user.is_admin:
        raise Unauthorized(context=call.context)


async def _async_dry_run_cleanup(
    targets: list[tuple[str, Any, Any]],
) -> dict[str, Any]:
    """Return aggregate dry-run cleanup results for loaded entries."""
    previews: list[tuple[str, EntityRegistryCleanupPreview]] = []
    for entry_id, entry, coordinator in targets:
        previews.append((
            entry_id,
            await async_preview_stale_registry_cleanup(
                coordinator.hass,
                entry,
                coordinator,
            ),
        ))
    if not previews:
        raise ServiceValidationError(ERROR_NO_CLEANUP_TARGETS)

    entries = [
        {
            "entry_id": entry_id,
            **preview.as_service_response(),
        }
        for entry_id, preview in previews
    ]
    return {
        "action": "dry_run",
        "entries": entries,
        "total_stale_entities": sum(item.stale_entity_count for _id, item in previews),
        "total_stale_devices": sum(item.stale_device_count for _id, item in previews),
    }


async def _async_confirm_cleanup(
    targets: list[tuple[str, Any, Any]],
    requested_entry_id: str | None,
    audit_id: str | None,
) -> dict[str, Any]:
    """Disable stale entities only when entry_id and audit_id match."""
    if requested_entry_id is None:
        raise ServiceValidationError(ERROR_CONFIRM_REQUIRES_ENTRY)
    if not audit_id:
        raise ServiceValidationError(ERROR_CONFIRM_REQUIRES_AUDIT)
    if not targets:
        raise ServiceValidationError(ERROR_ENTRY_NOT_LOADED)

    entry_id, entry, coordinator = targets[0]
    try:
        audit = await async_disable_stale_registry_entities(
            coordinator.hass,
            entry,
            coordinator,
            audit_id=audit_id,
        )
    except ValueError as err:
        raise ServiceValidationError(ERROR_AUDIT_MISMATCH) from err
    _LOGGER.info(
        "Confirmed Yeelight Pro stale registry cleanup for entry %s: disabled=%s",
        entry_id,
        audit.disabled_entities,
    )
    return _audit_service_response(entry_id, audit)


def _audit_service_response(
    entry_id: str,
    audit: EntityRegistryCleanupAudit,
) -> dict[str, Any]:
    """Return an aggregate confirm response without registry identifiers."""
    payload = audit.as_diagnostics()
    payload["entry_id"] = entry_id
    payload["action"] = "confirm"
    return payload


def _loaded_cleanup_targets(
    hass: HomeAssistant,
    requested_entry_id: str | None,
) -> list[tuple[str, Any, Any]]:
    """Return loaded config entries that can run cleanup."""
    domain_data = hass.data.get(DOMAIN, {})
    if not isinstance(domain_data, dict):
        return []

    targets: list[tuple[str, Any, Any]] = []
    for entry_id, entry_data in domain_data.items():
        if requested_entry_id is not None and entry_id != requested_entry_id:
            continue
        if not isinstance(entry_data, dict):
            continue
        entry = entry_data.get("entry")
        coordinator = entry_data.get("coordinator")
        if getattr(entry, "entry_id", None) == entry_id and getattr(
            coordinator,
            "hass",
            None,
        ) is hass:
            targets.append((entry_id, entry, coordinator))
    return targets
