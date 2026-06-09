"""Device removal hook tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro import async_remove_config_entry_device
from custom_components.yeelight_pro.const import DOMAIN
from custom_components.yeelight_pro.core.coordinator import YeelightProCoordinator


def _entry(entry_id: str = "entry-1") -> MagicMock:
    """Build a config entry test double."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = entry_id
    return entry


def _device_entry(*identifiers: tuple[str, str]) -> SimpleNamespace:
    """Build a device registry entry test double."""
    return SimpleNamespace(
        id="device-registry-id",
        identifiers=set(identifiers),
    )


def _device_payload(identifier: str) -> dict:
    """Build a normalized device payload with one HA identifier."""
    return {
        "ha_device_instance": {
            "device_info": {
                "identifiers": [[DOMAIN, identifier]],
            },
        },
    }


def _coordinator(hass: HomeAssistant) -> MagicMock:
    """Build a coordinator test double."""
    coordinator = MagicMock(spec=YeelightProCoordinator)
    coordinator.house_id = 12345
    coordinator.data = {}
    coordinator.get_gateway_devices.return_value = {}
    hass.data[DOMAIN] = {
        "entry-1": {"coordinator": coordinator},
    }
    return coordinator


@pytest.mark.asyncio
async def test_remove_config_entry_device_rejects_active_source_device(
    hass: HomeAssistant,
) -> None:
    """Active source devices should not be removable from the config entry."""
    coordinator = _coordinator(hass)
    coordinator.data = {"device-1": _device_payload("device:1")}

    allowed = await async_remove_config_entry_device(
        hass,
        _entry(),
        _device_entry((DOMAIN, "device:1")),
    )

    assert allowed is False


@pytest.mark.asyncio
async def test_remove_config_entry_device_rejects_active_gateway_device(
    hass: HomeAssistant,
) -> None:
    """Active gateway devices should not be removable from the config entry."""
    coordinator = _coordinator(hass)
    coordinator.get_gateway_devices.return_value = {
        "gateway-1": _device_payload("gateway:1")
    }

    allowed = await async_remove_config_entry_device(
        hass,
        _entry(),
        _device_entry((DOMAIN, "gateway:1")),
    )

    assert allowed is False


@pytest.mark.asyncio
async def test_remove_config_entry_device_rejects_active_house_device(
    hass: HomeAssistant,
) -> None:
    """House-level helper devices are active while the coordinator is loaded."""
    _coordinator(hass)

    allowed = await async_remove_config_entry_device(
        hass,
        _entry(),
        _device_entry((DOMAIN, "12345")),
    )

    assert allowed is False


@pytest.mark.asyncio
async def test_remove_config_entry_device_allows_stale_yeelight_device(
    hass: HomeAssistant,
) -> None:
    """A Yeelight Pro device no longer in topology can be removed locally."""
    coordinator = _coordinator(hass)
    coordinator.data = {"device-1": _device_payload("device:1")}

    allowed = await async_remove_config_entry_device(
        hass,
        _entry(),
        _device_entry((DOMAIN, "device:stale")),
    )

    assert allowed is True


@pytest.mark.asyncio
async def test_remove_config_entry_device_rejects_non_yeelight_device(
    hass: HomeAssistant,
) -> None:
    """The hook must not approve removing devices owned by another domain."""
    _coordinator(hass)

    allowed = await async_remove_config_entry_device(
        hass,
        _entry(),
        _device_entry(("other_domain", "device:1")),
    )

    assert allowed is False


@pytest.mark.asyncio
async def test_remove_config_entry_device_rejects_when_runtime_missing(
    hass: HomeAssistant,
) -> None:
    """Missing runtime data should fail closed to avoid accidental removal."""
    hass.data[DOMAIN] = {}

    allowed = await async_remove_config_entry_device(
        hass,
        _entry(),
        _device_entry((DOMAIN, "device:stale")),
    )

    assert allowed is False
