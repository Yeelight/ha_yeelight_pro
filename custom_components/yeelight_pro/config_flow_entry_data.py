"""Config-flow entry data builders for Yeelight Pro."""

from __future__ import annotations

from typing import Any

from .const import (
    CONF_ACCESS_TOKEN,
    CONF_ACCOUNT_USER_ID,
    CONF_ACCOUNT_USERNAME,
    CONF_CLOUD_DOMAIN,
    CONF_CLOUD_REGION,
    CONF_CONNECTION_MODE,
    CONF_HOUSE_ID,
    CONF_HOUSE_NAME,
    CONF_OPEN_API_CLIENT_ID,
    CONF_OPEN_API_CLIENT_SECRET,
    CONF_PRIVATE_DOMAIN,
    CONF_PRIVATE_PUSH_DOMAIN,
    CONF_REFRESH_TOKEN,
    CONF_SCAN_LOGIN_DEVICE,
    CONF_TOKEN_EXPIRES_IN,
    CONF_TOKEN_TYPE,
    CONNECTION_MODE_CLOUD,
    CONNECTION_MODE_PRIVATE,
)


def build_cloud_entry_data(flow: Any) -> dict[str, Any]:
    """Build config-entry data from the current config-flow state."""
    return {
        CONF_CONNECTION_MODE: flow._connection_mode,
        CONF_CLOUD_DOMAIN: (
            flow._domain if flow._connection_mode == CONNECTION_MODE_CLOUD else ""
        ),
        CONF_CLOUD_REGION: (
            flow._cloud_region if flow._connection_mode == CONNECTION_MODE_CLOUD else ""
        ),
        CONF_PRIVATE_DOMAIN: (
            flow._domain if flow._connection_mode == CONNECTION_MODE_PRIVATE else ""
        ),
        CONF_PRIVATE_PUSH_DOMAIN: (
            flow._private_push_domain
            if flow._connection_mode == CONNECTION_MODE_PRIVATE
            else ""
        ),
        CONF_ACCESS_TOKEN: flow._access_token,
        CONF_REFRESH_TOKEN: flow._refresh_token,
        CONF_TOKEN_EXPIRES_IN: flow._token_expires_in,
        CONF_TOKEN_TYPE: flow._token_type,
        CONF_HOUSE_ID: flow._house_id,
        CONF_HOUSE_NAME: flow._house_name,
        CONF_OPEN_API_CLIENT_ID: flow._open_api_client_id,
        CONF_OPEN_API_CLIENT_SECRET: flow._open_api_client_secret,
        CONF_ACCOUNT_USER_ID: flow._account_user_id,
        CONF_ACCOUNT_USERNAME: flow._account_username,
        CONF_SCAN_LOGIN_DEVICE: flow._scan_login_device,
    }


__all__ = ["build_cloud_entry_data"]
