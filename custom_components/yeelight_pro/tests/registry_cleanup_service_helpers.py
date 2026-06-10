"""Shared helpers for registry cleanup service tests."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from homeassistant.auth.const import GROUP_ID_ADMIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Context, HomeAssistant

from custom_components.yeelight_pro.const import DOMAIN
from custom_components.yeelight_pro.registry_cleanup_service import (
    SERVICE_CLEANUP_REGISTRY,
)

from .entity_lifecycle_helpers import lifecycle_coordinator


def install_cleanup_runtime(
    hass: HomeAssistant,
    *,
    data: dict[int, dict[str, object]] | None = None,
    options: dict[str, object] | None = None,
) -> SimpleNamespace:
    """Install a focused runtime entry for cleanup service tests."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "entry-1"
    coordinator = lifecycle_coordinator(data=data, options=options)
    coordinator.hass = hass
    coordinator.get_gateway_devices = lambda: {}
    hass.data[DOMAIN] = {
        "entry-1": {
            "entry": entry,
            "coordinator": coordinator,
        }
    }
    return coordinator


async def admin_context(hass: HomeAssistant) -> Context:
    """Create an explicit admin context for registry cleanup service calls."""
    user = await hass.auth.async_create_system_user(
        "registry-cleanup-admin",
        group_ids=[GROUP_ID_ADMIN],
    )
    return Context(user_id=user.id)


async def call_cleanup_registry(
    hass: HomeAssistant,
    data: dict[str, Any] | None = None,
    *,
    context: Context | None = None,
) -> dict[str, Any]:
    """Call the cleanup service and return its response."""
    return await hass.services.async_call(
        DOMAIN,
        SERVICE_CLEANUP_REGISTRY,
        data,
        blocking=True,
        context=context,
        return_response=True,
    )


def patch_device_registry(
    monkeypatch: pytest.MonkeyPatch,
    *,
    stale_device_count: int,
    identifiers: list[str] | None = None,
) -> None:
    """Patch HA device registry helpers with aggregate stale device fixtures."""
    identifier_values = identifiers or [
        f"stale-device-{index}" for index in range(stale_device_count)
    ]
    entries = [
        SimpleNamespace(
            id=f"device-{index}",
            identifiers={(DOMAIN, identifier)},
        )
        for index, identifier in enumerate(identifier_values)
    ]
    fake_registry = SimpleNamespace(entries=entries)
    monkeypatch.setattr(
        "custom_components.yeelight_pro.entity_lifecycle_cleanup.dr.async_get",
        lambda hass: fake_registry,
    )
    monkeypatch.setattr(
        "custom_components.yeelight_pro.entity_lifecycle_cleanup."
        "dr.async_entries_for_config_entry",
        lambda device_registry, entry_id: device_registry.entries,
    )
