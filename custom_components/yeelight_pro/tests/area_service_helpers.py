"""Shared helpers for Yeelight Pro area service tests."""
from __future__ import annotations

import traceback

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.yeelight_pro import async_setup
from custom_components.yeelight_pro.const import DOMAIN

CONFIG_ENTRY_ID = "entry-1"
SENSITIVE_REFERENCE = "secret-token https://api.yeelight.com device 12345"


async def async_setup_area_services(hass: HomeAssistant) -> None:
    """Register Yeelight Pro area services for a focused HA test instance."""
    MockConfigEntry(domain=DOMAIN, entry_id=CONFIG_ENTRY_ID).add_to_hass(hass)
    assert await async_setup(hass, {}) is True


def create_area(hass: HomeAssistant, name: str) -> str:
    """Create a Home Assistant area and return its registry id."""
    return ar.async_get(hass).async_create(name).id


def create_yeelight_device(
    hass: HomeAssistant,
    *,
    identifier: str,
    name: str,
    via_device_id: str | None = None,
) -> str:
    """Create a Yeelight Pro device registry entry and return its HA device id."""
    device_registry = dr.async_get(hass)
    device = device_registry.async_get_or_create(
        config_entry_id=CONFIG_ENTRY_ID,
        identifiers={(DOMAIN, identifier)},
        manufacturer="Yeelight",
        name=name,
    )
    if via_device_id is not None:
        updated = device_registry.async_update_device(
            device.id,
            via_device_id=via_device_id,
        )
        if updated is not None:
            device = updated
    return device.id


def create_non_yeelight_device(
    hass: HomeAssistant,
    *,
    identifier: str,
    name: str,
) -> str:
    """Create a non-Yeelight device registry entry and return its HA device id."""
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=CONFIG_ENTRY_ID,
        identifiers={("other_domain", identifier)},
        manufacturer="Other",
        name=name,
    )
    return device.id


def create_entity_for_device(
    hass: HomeAssistant,
    *,
    device_id: str,
    entity_id: str,
    unique_id: str,
) -> None:
    """Create an entity registry entry bound to a HA device."""
    entity_registry = er.async_get(hass)
    entity_registry.async_get_or_create(
        "light",
        DOMAIN,
        unique_id,
        suggested_object_id=entity_id.split(".", 1)[1],
        device_id=device_id,
    )


def assert_error_does_not_echo(
    error: HomeAssistantError,
    *,
    expected: str,
    sensitive: str,
) -> None:
    """Assert service validation errors do not echo user-supplied references."""
    message = str(error)
    formatted = "".join(
        traceback.format_exception(type(error), error, error.__traceback__)
    )

    assert expected in message
    assert sensitive not in message
    assert sensitive not in formatted
