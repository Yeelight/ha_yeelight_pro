"""Shared factories for config entry lifecycle tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.const import (
    CONF_CONNECTION_MODE,
    CONF_HOUSE_ID,
    CONF_OPEN_API_CLIENT_ID,
    CONNECTION_MODE_CLOUD,
    DOMAIN,
)
from custom_components.yeelight_pro.core.client import YeelightProClient
from custom_components.yeelight_pro.core.coordinator import YeelightProCoordinator


def make_config_entry() -> MagicMock:
    """Build a config entry test double."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.domain = DOMAIN
    entry.data = {
        CONF_CONNECTION_MODE: CONNECTION_MODE_CLOUD,
        CONF_ACCESS_TOKEN: "test_token",
        CONF_HOUSE_ID: 12345,
        CONF_OPEN_API_CLIENT_ID: "client-1",
        "cloud_domain": "api.yeelight.com",
    }
    entry.options = {}
    return entry


def make_client() -> AsyncMock:
    """Build a client test double."""
    client = AsyncMock(spec=YeelightProClient)
    client.check_health.return_value = True
    client.validate_auth.return_value = True
    client.get_houses.return_value = [{"id": 12345, "name": "测试家庭"}]
    client.get_devices.return_value = []
    client.get_gateways.return_value = []
    client.get_product_schemas.return_value = {}
    client.control_device.return_value = True
    client.execute_scene.return_value = True
    client.get_scenes.return_value = []
    client.get_automations.return_value = []
    client.get_groups.return_value = []
    client.get_rooms.return_value = []
    client.get_areas.return_value = []
    return client


def make_coordinator(hass: HomeAssistant, client: AsyncMock) -> MagicMock:
    """Build a coordinator test double."""
    coordinator = MagicMock(spec=YeelightProCoordinator)
    coordinator.hass = hass
    coordinator.client = client
    coordinator.data = {}
    coordinator.scenes = []
    coordinator.automations = []
    coordinator.areas = []
    coordinator.rooms = []
    coordinator.groups = []
    coordinator.house_id = 12345
    coordinator.async_config_entry_first_refresh = AsyncMock()
    coordinator.async_execute_scene = AsyncMock()
    coordinator.async_trigger_automation = AsyncMock()
    coordinator.async_control_device = AsyncMock()
    coordinator.async_toggle_device = AsyncMock()
    return coordinator


def make_setup_coordinator() -> MagicMock:
    """Build a setup-ready coordinator test double."""
    coordinator = MagicMock()
    coordinator.async_config_entry_first_refresh = AsyncMock()
    coordinator.data = {}
    coordinator.devices = {}
    coordinator.gateways = {}
    coordinator.areas = []
    coordinator.rooms = []
    coordinator.groups = []
    coordinator.scenes = []
    coordinator.automations = []
    coordinator.get_gateway_devices = MagicMock(return_value={})
    coordinator.topology_generation = 0
    coordinator.async_add_listener = MagicMock(return_value=MagicMock())
    return coordinator
