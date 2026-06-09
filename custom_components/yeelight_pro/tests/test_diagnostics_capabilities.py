"""Diagnostics client capability boundary tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.const import CONNECTION_MODE_CLOUD
from custom_components.yeelight_pro.diagnostics import async_get_config_entry_diagnostics

from .diagnostics_helpers import (
    build_aggregate_runtime_coordinator,
    build_diagnostics_entry,
    install_runtime_entry,
)


@pytest.fixture
def diagnostics_entry() -> MagicMock:
    """Build a diagnostics config entry."""
    return build_diagnostics_entry()


@pytest.mark.asyncio
async def test_diagnostics_reports_client_capabilities(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
) -> None:
    """诊断能力边界必须明确区分已验证合同和未启用 live runtime."""
    coordinator = build_aggregate_runtime_coordinator()
    install_runtime_entry(
        hass,
        diagnostics_entry,
        coordinator,
        platforms=["light", "binary_sensor"],
    )

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)

    assert data["runtime"]["client_capabilities"] == {
        "connection_mode": CONNECTION_MODE_CLOUD,
        "supported_connection_modes": ["cloud", "private"],
        "cloud_http_polling": True,
        "private_http_polling": False,
        "oauth_contract": True,
        "oauth_token_runtime": True,
        "manual_oauth_authorization_code_exchange": True,
        "scan_login_contract": True,
        "scan_login_runtime": True,
        "oauth_flow": False,
        "refresh_token_contract": True,
        "refresh_token_runtime": True,
        "push_message_adapter": True,
        "runtime_payload_bridge": True,
        "websocket_message_contract": True,
        "websocket_transport_skeleton": True,
        "push_manager_contract": True,
        "lan_discovery_parser": True,
        "lan_message_contract": True,
        "lan_payload_adapter": True,
        "analytics_contract": True,
        "push_connection": True,
        "websocket_subscription": True,
        "local_gateway_control": True,
        "lan_control": True,
        "mqtt_subscription": False,
        "analytics_runtime": True,
    }
