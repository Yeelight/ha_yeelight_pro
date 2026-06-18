"""Private deployment push endpoint options-flow tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from homeassistant.data_entry_flow import FlowResultType

from custom_components.yeelight_pro.config_flow import YeelightProOptionsFlow
from custom_components.yeelight_pro.const import (
    CONF_CONNECTION_MODE,
    CONF_DEBUG_MODE,
    CONF_HIDE_UNKNOWN_ENTITIES,
    CONF_LIVE_UPDATES,
    CONF_PRIVATE_DOMAIN,
    CONF_PRIVATE_PUSH_DOMAIN,
    CONF_SCAN_INTERVAL,
    CONF_TOPOLOGY_CHANGE_REPAIRS,
    CONNECTION_MODE_LAN,
    CONNECTION_MODE_PRIVATE,
)


@pytest.mark.asyncio
async def test_options_flow_private_entry_shows_push_url(mock_config_entry) -> None:
    """Existing private entries can edit their independent WebSocket endpoint."""
    mock_config_entry.data[CONF_CONNECTION_MODE] = CONNECTION_MODE_PRIVATE
    mock_config_entry.data[CONF_PRIVATE_DOMAIN] = "http://api-test.yeedev.com"
    mock_config_entry.data[CONF_PRIVATE_PUSH_DOMAIN] = ""
    mock_config_entry.options = {}
    flow = YeelightProOptionsFlow(mock_config_entry)

    result = await flow.async_step_general()

    assert result["type"] == FlowResultType.FORM
    defaults = {
        marker.schema: marker.default()
        for marker in result["data_schema"].schema
    }
    assert defaults[CONF_PRIVATE_PUSH_DOMAIN] == ""


@pytest.mark.asyncio
async def test_options_flow_private_push_change_updates_entry_data(
    mock_config_entry,
    mock_hass,
) -> None:
    """Saving a private push URL updates config-entry data and asks for reload."""
    mock_config_entry.data.update({
        CONF_CONNECTION_MODE: CONNECTION_MODE_PRIVATE,
        CONF_PRIVATE_DOMAIN: "http://api-test.yeedev.com",
        CONF_PRIVATE_PUSH_DOMAIN: "",
    })
    mock_config_entry.options = {
        CONF_SCAN_INTERVAL: 15,
        CONF_DEBUG_MODE: False,
        CONF_HIDE_UNKNOWN_ENTITIES: True,
        CONF_TOPOLOGY_CHANGE_REPAIRS: True,
        CONF_LIVE_UPDATES: True,
    }
    mock_hass.config_entries.async_update_entry = MagicMock()
    flow = YeelightProOptionsFlow(mock_config_entry)
    flow.hass = mock_hass

    result = await flow.async_step_general({
        **mock_config_entry.options,
        CONF_PRIVATE_PUSH_DOMAIN: "ws://ws-test.yeedev.com",
    })

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "confirm_reload"
    assert result["description_placeholders"] == {"changed_count": "1"}

    result = await flow.async_step_confirm_reload({})

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == mock_config_entry.options
    update = mock_hass.config_entries.async_update_entry.call_args
    assert update.args == (mock_config_entry,)
    assert update.kwargs["data"][CONF_PRIVATE_PUSH_DOMAIN] == (
        "ws://ws-test.yeedev.com/ws"
    )


@pytest.mark.parametrize("mode", ["cloud", CONNECTION_MODE_LAN])
@pytest.mark.asyncio
async def test_options_flow_non_private_entries_hide_push_url(
    mock_config_entry,
    mode: str,
) -> None:
    """Cloud and LAN entries must not expose private deployment push URL fields."""
    mock_config_entry.data[CONF_CONNECTION_MODE] = mode
    mock_config_entry.options = {}
    flow = YeelightProOptionsFlow(mock_config_entry)

    result = await flow.async_step_general()

    defaults = {
        marker.schema: marker.default()
        for marker in result["data_schema"].schema
    }
    assert CONF_PRIVATE_PUSH_DOMAIN not in defaults
