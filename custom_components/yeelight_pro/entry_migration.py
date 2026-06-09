"""Config entry migration helpers for Yeelight Pro."""
from __future__ import annotations

from typing import Any, Mapping

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_ACCESS_TOKEN,
    CONF_ACCOUNT_USER_ID,
    CONF_ACCOUNT_USERNAME,
    CONF_ANALYTICS_RETENTION_DAYS,
    CONF_ANALYTICS_RUNTIME,
    CONF_CLOUD_DOMAIN,
    CONF_CLOUD_REGION,
    CONF_CONNECTION_MODE,
    CONF_DEBUG_MODE,
    CONF_DEVICE_IMPORT_FILTER,
    CONF_EXPERIMENTAL_PLATFORMS,
    CONF_HIDE_UNKNOWN_ENTITIES,
    CONF_HOUSE_ID,
    CONF_LIVE_UPDATES,
    CONF_LOCAL_GATEWAY_CONTROL,
    CONF_LOCAL_GATEWAY_HOST,
    CONF_LOCAL_GATEWAY_PORT,
    CONF_OAUTH_CLIENT_ID,
    CONF_PRIVATE_DOMAIN,
    CONF_REFRESH_TOKEN,
    CONF_SCAN_INTERVAL,
    CONF_SCAN_LOGIN_DEVICE,
    CONF_TOKEN_EXPIRES_IN,
    CONF_TOKEN_TYPE,
    CONF_TOPOLOGY_CHANGE_REPAIRS,
    CONNECTION_MODE_CLOUD,
    CONNECTION_MODE_PRIVATE,
    DEFAULT_CLOUD_DOMAIN,
    DEFAULT_CLOUD_REGION,
    DEFAULT_ANALYTICS_RETENTION_DAYS,
    DEFAULT_ANALYTICS_RUNTIME,
    DEFAULT_DEBUG_MODE,
    DEFAULT_EXPERIMENTAL_PLATFORMS,
    DEFAULT_HIDE_UNKNOWN_ENTITIES,
    DEFAULT_LIVE_UPDATES,
    DEFAULT_LOCAL_GATEWAY_CONTROL,
    DEFAULT_LOCAL_GATEWAY_HOST,
    DEFAULT_LOCAL_GATEWAY_PORT,
    DEFAULT_PRIVATE_DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TOPOLOGY_CHANGE_REPAIRS,
    MAX_ANALYTICS_RETENTION_DAYS,
    MAX_SCAN_INTERVAL,
    MIN_ANALYTICS_RETENTION_DAYS,
    MIN_SCAN_INTERVAL,
)
from .device_filter_options import (
    device_filter_form_keys,
    stored_device_import_filter_options,
)

ENTRY_VERSION = 1
ENTRY_MINOR_VERSION = 3


async def async_migrate_config_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Migrate legacy Yeelight Pro config entry data and options."""
    data = normalize_entry_data(entry.data)
    options = normalize_entry_options(getattr(entry, "options", None))
    if (
        data == dict(entry.data)
        and options == _mapping_or_empty(getattr(entry, "options", None))
        and entry.version == ENTRY_VERSION
        and entry.minor_version == ENTRY_MINOR_VERSION
    ):
        return True

    hass.config_entries.async_update_entry(
        entry,
        data=data,
        options=options,
        version=ENTRY_VERSION,
        minor_version=ENTRY_MINOR_VERSION,
    )
    return True


def normalize_entry_data(value: Mapping[str, Any]) -> dict[str, Any]:
    """Return config entry data with current required keys."""
    source = dict(value)
    connection_mode = _connection_mode(source)
    cloud_domain = _string(
        _first_value(source, CONF_CLOUD_DOMAIN, "cloudDomain", "domain")
    )
    private_domain = _string(
        _first_value(source, CONF_PRIVATE_DOMAIN, "privateDomain", "server")
    )
    domain = private_domain if connection_mode == CONNECTION_MODE_PRIVATE else cloud_domain

    return {
        **source,
        CONF_CONNECTION_MODE: connection_mode,
        CONF_CLOUD_DOMAIN: (
            ""
            if connection_mode == CONNECTION_MODE_PRIVATE
            else domain or DEFAULT_CLOUD_DOMAIN
        ),
        CONF_PRIVATE_DOMAIN: (
            domain or DEFAULT_PRIVATE_DOMAIN
            if connection_mode == CONNECTION_MODE_PRIVATE
            else private_domain or ""
        ),
        CONF_ACCESS_TOKEN: _string(
            _first_value(source, CONF_ACCESS_TOKEN, "accessToken", "token")
        ),
        CONF_REFRESH_TOKEN: _string(
            _first_value(source, CONF_REFRESH_TOKEN, "refreshToken", "refresh_token")
        ),
        CONF_TOKEN_EXPIRES_IN: _optional_int(
            _first_value(source, CONF_TOKEN_EXPIRES_IN, "expiresIn", "expires_in")
        ),
        CONF_TOKEN_TYPE: _string(
            _first_value(source, CONF_TOKEN_TYPE, "tokenType", "token_type")
        ),
        CONF_HOUSE_ID: _coerce_house_id(
            _first_value(source, CONF_HOUSE_ID, "houseId", "house_id", "home_id")
        ),
        CONF_CLOUD_REGION: _cloud_region(source, cloud_domain),
        CONF_OAUTH_CLIENT_ID: _string(
            _first_value(source, CONF_OAUTH_CLIENT_ID, "clientId", "client_id")
        ),
        CONF_ACCOUNT_USER_ID: _optional_int(
            _first_value(source, CONF_ACCOUNT_USER_ID, "id", "user_id")
        ),
        CONF_ACCOUNT_USERNAME: _string(
            _first_value(source, CONF_ACCOUNT_USERNAME, "username")
        ),
        CONF_SCAN_LOGIN_DEVICE: _string(
            _first_value(source, CONF_SCAN_LOGIN_DEVICE, "device")
        ),
    }


def normalize_entry_options(value: Any) -> dict[str, Any]:
    """Return options with current defaults while preserving advanced keys."""
    options = _mapping_or_empty(value)
    data = {
        **options,
        CONF_SCAN_INTERVAL: _coerce_int(
            options.get(CONF_SCAN_INTERVAL),
            default=DEFAULT_SCAN_INTERVAL,
            minimum=MIN_SCAN_INTERVAL,
            maximum=MAX_SCAN_INTERVAL,
        ),
        CONF_DEBUG_MODE: _coerce_bool(
            options.get(CONF_DEBUG_MODE),
            default=DEFAULT_DEBUG_MODE,
        ),
        CONF_EXPERIMENTAL_PLATFORMS: _coerce_bool(
            options.get(CONF_EXPERIMENTAL_PLATFORMS),
            default=DEFAULT_EXPERIMENTAL_PLATFORMS,
        ),
        CONF_HIDE_UNKNOWN_ENTITIES: _coerce_bool(
            options.get(CONF_HIDE_UNKNOWN_ENTITIES),
            default=DEFAULT_HIDE_UNKNOWN_ENTITIES,
        ),
        CONF_TOPOLOGY_CHANGE_REPAIRS: _coerce_bool(
            options.get(CONF_TOPOLOGY_CHANGE_REPAIRS),
            default=DEFAULT_TOPOLOGY_CHANGE_REPAIRS,
        ),
        CONF_LIVE_UPDATES: _coerce_bool(
            options.get(CONF_LIVE_UPDATES),
            default=DEFAULT_LIVE_UPDATES,
        ),
        CONF_LOCAL_GATEWAY_CONTROL: _coerce_bool(
            options.get(CONF_LOCAL_GATEWAY_CONTROL),
            default=DEFAULT_LOCAL_GATEWAY_CONTROL,
        ),
        CONF_LOCAL_GATEWAY_HOST: _string(
            options.get(CONF_LOCAL_GATEWAY_HOST) or DEFAULT_LOCAL_GATEWAY_HOST
        ).strip(),
        CONF_LOCAL_GATEWAY_PORT: _coerce_int(
            options.get(CONF_LOCAL_GATEWAY_PORT),
            default=DEFAULT_LOCAL_GATEWAY_PORT,
            minimum=1,
            maximum=65535,
        ),
        CONF_ANALYTICS_RUNTIME: _coerce_bool(
            options.get(CONF_ANALYTICS_RUNTIME),
            default=DEFAULT_ANALYTICS_RUNTIME,
        ),
        CONF_ANALYTICS_RETENTION_DAYS: _coerce_int(
            options.get(CONF_ANALYTICS_RETENTION_DAYS),
            default=DEFAULT_ANALYTICS_RETENTION_DAYS,
            minimum=MIN_ANALYTICS_RETENTION_DAYS,
            maximum=MAX_ANALYTICS_RETENTION_DAYS,
        ),
    }
    filter_config = stored_device_import_filter_options(options)
    for key in device_filter_form_keys():
        data.pop(key, None)
    if filter_config is not None:
        data[CONF_DEVICE_IMPORT_FILTER] = filter_config
    return data


def _connection_mode(value: Mapping[str, Any]) -> str:
    mode = _string(value.get(CONF_CONNECTION_MODE)).lower()
    if mode in {CONNECTION_MODE_CLOUD, CONNECTION_MODE_PRIVATE}:
        return mode
    if _string(_first_value(value, CONF_PRIVATE_DOMAIN, "privateDomain", "server")):
        return CONNECTION_MODE_PRIVATE
    return CONNECTION_MODE_CLOUD


def _cloud_region(value: Mapping[str, Any], cloud_domain: str) -> str:
    """Return the stored Yeelight region key, preserving current CN fallback."""
    raw_region = _string(
        _first_value(value, CONF_CLOUD_REGION, "region", "cloudRegion")
    ).strip().lower()
    if raw_region in {"cn", "sg", "us", "de"}:
        return raw_region
    if raw_region in {"eu", "europe"}:
        return "de"
    domain = cloud_domain.lower()
    if "api-sg.yeelight.com" in domain:
        return "sg"
    if "api-us.yeelight.com" in domain:
        return "us"
    if "api-de.yeelight.com" in domain:
        return "de"
    return DEFAULT_CLOUD_REGION


def _mapping_or_empty(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _first_value(value: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        candidate = value.get(key)
        if candidate not in (None, ""):
            return candidate
    return None


def _coerce_house_id(value: Any) -> int | str:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return _string(value)


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_int(
    value: Any,
    *,
    default: int,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    if isinstance(value, bool):
        return default
    try:
        result = int(value)
    except (TypeError, ValueError):
        return default
    if minimum is not None:
        result = max(minimum, result)
    if maximum is not None:
        result = min(maximum, result)
    return result


def _coerce_bool(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off", ""}:
            return False
    return bool(value)


def _string(value: Any) -> str:
    return "" if value is None else str(value)
