"""Diagnostics payload allowlists for Yeelight Pro."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .const import (
    CONF_ACCESS_TOKEN,
    CONF_ACCOUNT_USER_ID,
    CONF_ACCOUNT_USERNAME,
    CONF_CLOUD_AUTH_METHOD,
    CONF_CLOUD_DOMAIN,
    CONF_CLOUD_REGION,
    CONF_CONNECTION_MODE,
    CONF_DEVICE_IMPORT_FILTER,
    CONF_DEBUG_MODE,
    CONF_EXPERIMENTAL_PLATFORMS,
    CONF_HIDE_UNKNOWN_ENTITIES,
    CONF_LIVE_UPDATES,
    CONF_LOCAL_GATEWAY_CONTROL,
    CONF_LOCAL_GATEWAY_HOST,
    CONF_LOCAL_GATEWAY_PORT,
    CONF_HOUSE_ID,
    CONF_OPEN_API_CLIENT_ID,
    CONF_PRIVATE_DOMAIN,
    CONF_REFRESH_TOKEN,
    CONF_SCAN_INTERVAL,
    CONF_SCAN_LOGIN_DEVICE,
    CONF_TOKEN_EXPIRES_IN,
    CONF_TOKEN_TYPE,
    CONF_TOPOLOGY_CHANGE_REPAIRS,
)
from .device_filter_options import device_filter_form_keys

CONFIG_DATA_KEYS = (
    CONF_ACCESS_TOKEN,
    CONF_REFRESH_TOKEN,
    CONF_CLOUD_AUTH_METHOD,
    CONF_CLOUD_DOMAIN,
    CONF_CLOUD_REGION,
    CONF_HOUSE_ID,
    CONF_OPEN_API_CLIENT_ID,
    CONF_PRIVATE_DOMAIN,
    CONF_TOKEN_EXPIRES_IN,
    CONF_TOKEN_TYPE,
    CONF_ACCOUNT_USER_ID,
    CONF_ACCOUNT_USERNAME,
    CONF_SCAN_LOGIN_DEVICE,
)
OPTION_KEYS = (
    CONF_SCAN_INTERVAL,
    CONF_DEBUG_MODE,
    CONF_HIDE_UNKNOWN_ENTITIES,
    CONF_EXPERIMENTAL_PLATFORMS,
    CONF_TOPOLOGY_CHANGE_REPAIRS,
    CONF_LIVE_UPDATES,
    CONF_LOCAL_GATEWAY_CONTROL,
    CONF_LOCAL_GATEWAY_HOST,
    CONF_LOCAL_GATEWAY_PORT,
    CONF_DEVICE_IMPORT_FILTER,
)
SENSITIVE_PAYLOAD_KEYS = frozenset(
    """
    Authorization authorization accessToken access_token body bssid cloudDomain
    areaId area_id automationId automation_id componentId component_id
    deviceId device_id domain endpoint entry_id groupId group_id host houseId
    house_id id latitude longitude mac message_id nodeId node_id password
    payload privateDomain raw_event response roomId room_id sceneId scene_id
    source_device_id token unique_id url username
    """.split()
)

TO_REDACT = {
    CONF_ACCESS_TOKEN,
    CONF_REFRESH_TOKEN,
    CONF_CLOUD_DOMAIN,
    CONF_DEVICE_IMPORT_FILTER,
    *device_filter_form_keys(),
    CONF_HOUSE_ID,
    CONF_OPEN_API_CLIENT_ID,
    CONF_PRIVATE_DOMAIN,
    CONF_LOCAL_GATEWAY_HOST,
    CONF_ACCOUNT_USER_ID,
    CONF_ACCOUNT_USERNAME,
    CONF_SCAN_LOGIN_DEVICE,
} | set(SENSITIVE_PAYLOAD_KEYS)


def entry_options(entry: Any) -> dict[str, Any]:
    """Return config entry options in a diagnostics-safe shape."""
    options = getattr(entry, "options", None)
    return dict(options) if isinstance(options, Mapping) else {}


def config_data_diagnostics(entry: Any) -> dict[str, Any]:
    """Return an allowlisted config entry data shape for diagnostics."""
    data = getattr(entry, "data", None)
    if not isinstance(data, Mapping):
        return {}
    result: dict[str, Any] = {}
    if isinstance(data.get(CONF_CONNECTION_MODE), str):
        result[CONF_CONNECTION_MODE] = data[CONF_CONNECTION_MODE]
    for key in CONFIG_DATA_KEYS:
        if key in data:
            result[key] = data[key]
    return result


def options_diagnostics(entry: Any) -> dict[str, Any]:
    """Return allowlisted config entry options for diagnostics."""
    options = entry_options(entry)
    return {key: options[key] for key in OPTION_KEYS if key in options}


__all__ = [
    "TO_REDACT",
    "config_data_diagnostics",
    "entry_options",
    "options_diagnostics",
]
