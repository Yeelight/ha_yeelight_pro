"""Legacy config entry options setup fallback tests."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.const import (
    CONF_CONNECTION_MODE,
    CONF_DEBUG_MODE,
    CONF_HIDE_UNKNOWN_ENTITIES,
    CONF_HOUSE_ID,
    CONF_SCAN_INTERVAL,
    CONF_TOPOLOGY_CHANGE_REPAIRS,
    CONNECTION_MODE_CLOUD,
    DOMAIN,
    MAX_SCAN_INTERVAL,
)
from custom_components.yeelight_pro.core.client import YeelightProClient

from .config_entry_lifecycle_helpers import register_config_entry


def _config_entry_with_legacy_options() -> MagicMock:
    """Build a config entry with stringly typed legacy options."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "legacy_options_entry"
    entry.domain = DOMAIN
    entry.data = {
        CONF_CONNECTION_MODE: CONNECTION_MODE_CLOUD,
        CONF_ACCESS_TOKEN: "test_token",
        CONF_HOUSE_ID: 12345,
        "cloud_domain": "api.yeelight.com",
    }
    entry.options = {
        CONF_SCAN_INTERVAL: "999",
        CONF_DEBUG_MODE: "0",
        "future_option": "keep",
        "experimental_platforms": "false",
        CONF_HIDE_UNKNOWN_ENTITIES: "false",
        CONF_TOPOLOGY_CHANGE_REPAIRS: "off",
    }
    return entry


def _client() -> AsyncMock:
    """Build a client test double."""
    client = AsyncMock(spec=YeelightProClient)
    client.check_health.return_value = True
    return client


def _coordinator_for_setup() -> MagicMock:
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
    coordinator.get_gateway_devices = MagicMock(return_value={})
    coordinator.topology_generation = 1
    return coordinator


@pytest.mark.asyncio
async def test_setup_entry_normalizes_legacy_options(
    hass: HomeAssistant,
) -> None:
    """Setup fallback should normalize legacy string options before use."""
    hass.data.setdefault(DOMAIN, {})
    entry = _config_entry_with_legacy_options()
    register_config_entry(hass, entry)

    with patch(
        "custom_components.yeelight_pro.YeelightProClient",
        return_value=_client(),
    ), patch(
        "custom_components.yeelight_pro.YeelightProCoordinator",
    ) as coordinator_class, patch(
        "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
        new_callable=AsyncMock,
    ) as forward_setups, patch(
        "custom_components.yeelight_pro.entry_setup.async_create_topology_changed_issue",
    ) as create_issue:
        coordinator = _coordinator_for_setup()
        listener_holder = {}

        def _add_listener(listener):
            listener_holder["listener"] = listener
            return MagicMock()

        coordinator.async_add_listener = MagicMock(side_effect=_add_listener)
        coordinator_class.return_value = coordinator

        from custom_components.yeelight_pro import async_setup_entry

        assert await async_setup_entry(hass, entry) is True
        coordinator.topology_generation = 2
        listener_holder["listener"]()

    coordinator_options = coordinator_class.call_args.kwargs["options"]
    assert coordinator_options[CONF_SCAN_INTERVAL] == MAX_SCAN_INTERVAL
    assert coordinator_options[CONF_DEBUG_MODE] is False
    assert coordinator_options["future_option"] == "keep"
    assert "experimental_platforms" not in coordinator_options
    assert coordinator_options[CONF_HIDE_UNKNOWN_ENTITIES] is False
    assert coordinator_options[CONF_TOPOLOGY_CHANGE_REPAIRS] is False
    assert forward_setups.await_args is not None
    create_issue.assert_not_called()
