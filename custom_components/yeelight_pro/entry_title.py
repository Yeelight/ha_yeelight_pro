"""Config-entry title helpers for Yeelight Pro."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .const import (
    CONF_ACCOUNT_USER_ID,
    CONF_ACCOUNT_USERNAME,
    CONF_CLOUD_REGION,
    CONF_CONNECTION_MODE,
    CONF_LAN_GATEWAY_IP,
    CONF_LAN_GATEWAY_PORT,
    CONF_PRIVATE_DOMAIN,
    CONNECTION_MODE_LAN,
    CONNECTION_MODE_PRIVATE,
)
from .house_metadata import house_name_from_data

REGION_LABELS = {
    "cn": "CN",
    "sg": "SG",
    "us": "US",
    "de": "EU",
}


def config_entry_title(entry_data: Mapping[str, Any]) -> str:
    """Return a concise HA integration hub title without exposing token data."""
    mode = str(entry_data.get(CONF_CONNECTION_MODE) or "").strip()
    if mode == CONNECTION_MODE_PRIVATE:
        return _private_title(entry_data)
    if mode == CONNECTION_MODE_LAN:
        return _lan_title(entry_data)
    return _cloud_title(entry_data)


def _cloud_title(entry_data: Mapping[str, Any]) -> str:
    account = _cloud_account_label(entry_data)
    region = REGION_LABELS.get(
        str(entry_data.get(CONF_CLOUD_REGION) or "").strip().lower(),
        str(entry_data.get(CONF_CLOUD_REGION) or "").strip().upper() or "CN",
    )
    house_name = house_name_from_data(entry_data)
    title_parts = [part for part in (account, region, house_name) if part]
    return f"Yeelight Pro Cloud ({' · '.join(title_parts)})"


def _private_title(entry_data: Mapping[str, Any]) -> str:
    private_domain = _required_text(entry_data.get(CONF_PRIVATE_DOMAIN), "Private")
    house_name = house_name_from_data(entry_data)
    return f"Yeelight Pro Private ({private_domain} · {house_name})"


def _lan_title(entry_data: Mapping[str, Any]) -> str:
    ip = _required_text(entry_data.get(CONF_LAN_GATEWAY_IP), "LAN")
    port = entry_data.get(CONF_LAN_GATEWAY_PORT, 65443)
    return f"Yeelight Pro LAN ({ip}:{port})"


def _cloud_account_label(entry_data: Mapping[str, Any]) -> str:
    username = _optional_text(entry_data.get(CONF_ACCOUNT_USERNAME))
    if username:
        return username
    account_user_id = _optional_text(entry_data.get(CONF_ACCOUNT_USER_ID))
    return f"UID {account_user_id}" if account_user_id else ""


def _required_text(value: Any, fallback: str) -> str:
    text = _optional_text(value)
    return text if text else fallback


def _optional_text(value: Any) -> str:
    return str(value).strip() if value not in (None, "") else ""


__all__ = ["REGION_LABELS", "config_entry_title"]
