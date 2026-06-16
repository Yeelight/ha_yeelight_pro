"""Basic diagnostics tests for Yeelight Pro."""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.capabilities import iot_registry
from custom_components.yeelight_pro.const import (
    CONF_CLOUD_AUTH_METHOD,
    CONF_CLOUD_DOMAIN,
    CONF_CONNECTION_MODE,
    CONF_DEBUG_MODE,
    CONF_DEVICE_IMPORT_FILTER,
    CONF_HIDE_UNKNOWN_ENTITIES,
    CONF_HOUSE_ID,
    CONF_OPEN_API_CLIENT_ID,
    CONF_OPEN_API_CLIENT_SECRET,
    CONF_SCAN_INTERVAL,
    CONF_TOPOLOGY_CHANGE_REPAIRS,
    CONNECTION_MODE_CLOUD,
    DOMAIN,
    PLATFORMS,
)
from custom_components.yeelight_pro.diagnostics import (
    async_get_config_entry_diagnostics,
)

from .diagnostics_helpers import build_diagnostics_entry


@pytest.fixture
def diagnostics_entry() -> MagicMock:
    """Build a diagnostics config entry."""
    return build_diagnostics_entry()


@pytest.mark.asyncio
async def test_diagnostics_returns_sane_unloaded_entry(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
) -> None:
    """未加载配置条目仍应返回可下载的脱敏诊断数据."""
    hass.data[DOMAIN] = {}

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)

    assert data["runtime"]["loaded"] is False
    assert data["runtime"]["client_capabilities"] == {
        "connection_mode": CONNECTION_MODE_CLOUD,
        "supported_connection_modes": ["cloud", "private", "lan"],
        "cloud_http_polling": False,
        "private_http_polling": False,
        "lan_direct_control": False,
        "scan_login_contract": True,
        "scan_login_runtime": False,
        "push_message_adapter": True,
        "runtime_payload_bridge": True,
        "websocket_message_contract": True,
        "websocket_transport_runtime": False,
        "push_manager_contract": True,
        "lan_discovery_parser": True,
        "lan_message_contract": True,
        "lan_payload_adapter": True,
        "push_connection": False,
        "websocket_subscription": False,
        "websocket_event_notifications": False,
        "local_gateway_control": False,
        "lan_control": False,
        "mqtt_subscription": False,
    }
    assert data["runtime"]["iot_registry"]["valid"] is True
    assert data["runtime"]["iot_registry"]["categories"] == len(
        iot_registry().categories
    )
    assert data["runtime"]["options"][CONF_SCAN_INTERVAL] == 15
    assert data["runtime"]["options"][CONF_DEVICE_IMPORT_FILTER] == "**REDACTED**"
    assert data["runtime"]["option_status"] == {
        "runtime_loaded": False,
        "runtime_reload_required": True,
        "platforms_match_options": False,
        "loaded_platform_count": 0,
        "expected_platform_count": len(PLATFORMS),
        "debug_mode_enabled": True,
        "scan_interval_seconds": 15,
        "hide_unknown_entities": False,
        "topology_change_repairs": False,
        "live_updates_enabled": True,
        "local_gateway_control_enabled": False,
        "import_filter_active": True,
        "import_filter_rule_count": 2,
        "import_filter_ignored_rule_count": 2,
    }
    assert data["config_entry"]["data"][CONF_ACCESS_TOKEN] == "**REDACTED**"
    assert data["config_entry"]["data"][CONF_HOUSE_ID] == "**REDACTED**"
    assert data["config_entry"]["options"][CONF_DEVICE_IMPORT_FILTER] == "**REDACTED**"


@pytest.mark.asyncio
async def test_diagnostics_allowlists_config_entry_data_and_options(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
) -> None:
    """诊断数据不能因未来未知字段带出 raw payload/error/url."""
    diagnostics_entry.data["raw_error"] = (
        "token-secret https://api.yeelight.com/apis/iot/house/429392"
    )
    diagnostics_entry.data["authorization"] = "Bearer token-secret"
    diagnostics_entry.data[CONF_CLOUD_AUTH_METHOD] = "scan_login"
    diagnostics_entry.data[CONF_OPEN_API_CLIENT_ID] = "client-secret-id"
    diagnostics_entry.data[CONF_OPEN_API_CLIENT_SECRET] = "client-secret-value"
    diagnostics_entry.options["payload"] = {
        "body": "device-secret-1",
        "url": "https://api.yeelight.com/apis/iot",
    }
    diagnostics_entry.options["scene_id"] = "scene-secret"
    hass.data[DOMAIN] = {}

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)

    assert set(data["config_entry"]["data"]) == {
        CONF_CONNECTION_MODE,
        CONF_ACCESS_TOKEN,
        CONF_CLOUD_AUTH_METHOD,
        CONF_HOUSE_ID,
        CONF_CLOUD_DOMAIN,
        CONF_OPEN_API_CLIENT_ID,
        CONF_OPEN_API_CLIENT_SECRET,
    }
    assert data["config_entry"]["data"][CONF_OPEN_API_CLIENT_ID] == "**REDACTED**"
    assert data["config_entry"]["data"][CONF_OPEN_API_CLIENT_SECRET] == "**REDACTED**"
    assert set(data["config_entry"]["options"]) == {
        CONF_SCAN_INTERVAL,
        CONF_DEBUG_MODE,
        CONF_HIDE_UNKNOWN_ENTITIES,
        CONF_TOPOLOGY_CHANGE_REPAIRS,
        CONF_DEVICE_IMPORT_FILTER,
    }
    dumped = json.dumps(data, ensure_ascii=False)
    assert "raw_error" not in dumped
    assert '"authorization"' not in dumped
    assert "client-secret-id" not in dumped
    assert "client-secret-value" not in dumped
    assert '"payload"' not in dumped
    assert "scene_id" not in dumped
    assert "device-secret-1" not in dumped
    assert "scene-secret" not in dumped
    assert "api.yeelight.com" not in dumped
