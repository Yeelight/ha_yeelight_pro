"""Runtime health and capability helpers for Yeelight Pro diagnostics."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .const import (
    CONF_CONNECTION_MODE,
    CONF_LIVE_UPDATES,
    CONNECTION_MODE_CLOUD,
    CONNECTION_MODE_LAN,
    CONNECTION_MODE_PRIVATE,
    DEFAULT_LIVE_UPDATES,
    get_enabled_platforms,
)


def client_capabilities(runtime: Mapping[str, Any]) -> dict[str, Any]:
    """Return safe connection capability flags without endpoint or token data."""
    entry = runtime.get("entry")
    capabilities = client_capabilities_for_entry(entry)
    connection_mode = capabilities["connection_mode"]
    has_cloud_client = runtime.get("client") is not None
    has_push_runtime = push_runtime_available(runtime.get("push_manager"))
    has_lan_runtime = runtime_manager_available(runtime.get("lan_runtime"))
    capabilities.update(
        {
            "cloud_http_polling": (
                connection_mode == CONNECTION_MODE_CLOUD and has_cloud_client
            ),
            "private_http_polling": (
                connection_mode == CONNECTION_MODE_PRIVATE and has_cloud_client
            ),
            "lan_direct_control": has_lan_runtime,
            "scan_login_runtime": has_cloud_client,
            "websocket_transport_runtime": has_push_runtime,
            "push_connection": has_push_runtime,
            "websocket_subscription": has_push_runtime,
            "websocket_event_notifications": has_push_runtime,
            "local_gateway_control": has_lan_runtime,
            "lan_control": has_lan_runtime,
        }
    )
    return capabilities


def client_capabilities_for_entry(entry: Any) -> dict[str, Any]:
    """Return safe connection capability flags from a config entry-like object."""
    data = getattr(entry, "data", None)
    connection_mode = None
    if isinstance(data, Mapping):
        raw_mode = data.get(CONF_CONNECTION_MODE)
        connection_mode = raw_mode if isinstance(raw_mode, str) else None
    supported_modes = (CONNECTION_MODE_CLOUD, CONNECTION_MODE_PRIVATE, CONNECTION_MODE_LAN)
    return {
        "connection_mode": (
            connection_mode if connection_mode in supported_modes else "unknown"
        ),
        "supported_connection_modes": list(supported_modes),
        "cloud_http_polling": connection_mode == CONNECTION_MODE_CLOUD,
        "private_http_polling": connection_mode == CONNECTION_MODE_PRIVATE,
        "lan_direct_control": connection_mode == CONNECTION_MODE_LAN,
        "scan_login_contract": True,
        "scan_login_runtime": True,
        "push_message_adapter": True,
        "runtime_payload_bridge": True,
        "websocket_message_contract": True,
        "websocket_transport_runtime": True,
        "push_manager_contract": True,
        "lan_discovery_parser": True,
        "lan_message_contract": True,
        "lan_payload_adapter": True,
        "push_connection": True,
        "websocket_subscription": True,
        "websocket_event_notifications": True,
        "local_gateway_control": True,
        "lan_control": True,
        "mqtt_subscription": False,
    }


def runtime_health(
    runtime: Mapping[str, Any],
    coordinator: Any,
) -> dict[str, Any]:
    """Return safe runtime health details without raw exception messages."""
    loaded_platforms = sorted(
        str(platform)
        for platform in (runtime.get("platforms") or [])
        if isinstance(platform, str)
    )
    expected_platforms = sorted(get_enabled_platforms(_runtime_entry_options(runtime)))
    live_updates_intended = _live_updates_intended(runtime)
    live_updates_active = push_runtime_available(runtime.get("push_manager"))
    polling_fallback_active = (
        live_updates_intended
        and not live_updates_active
        and runtime.get("client") is not None
    )
    return {
        "last_update_success": safe_bool_or_none(
            getattr(coordinator, "last_update_success", None),
        ),
        "last_exception_type": exception_type_name(
            getattr(coordinator, "last_exception", None),
        ),
        "loaded_platform_count": len(loaded_platforms),
        "expected_platform_count": len(expected_platforms),
        "platforms_match_options": loaded_platforms == expected_platforms,
        "live_updates_intended": live_updates_intended,
        "live_updates_active": live_updates_active,
        "polling_fallback_active": polling_fallback_active,
        "polling_fallback_interval_seconds": (
            int(getattr(coordinator, "scan_interval", 0) or 0)
            if polling_fallback_active
            else None
        ),
        "push": push_manager_health(runtime.get("push_manager")),
        "lan": manager_health(runtime.get("lan_runtime")),
    }


def manager_health(manager: Any) -> dict[str, Any] | None:
    """Return diagnostics-safe manager health when present."""
    health = getattr(manager, "health", None)
    as_dict = getattr(health, "as_dict", None)
    if callable(as_dict):
        return as_dict() # type: ignore
    return None


def push_manager_health(manager: Any) -> dict[str, Any] | None:
    """Return push manager and transport health without raw endpoint details."""
    health = manager_health(manager)
    if health is None:
        return None
    transport_health = getattr(manager, "transport_health", None)
    if isinstance(transport_health, Mapping):
        return {**health, "transport": dict(transport_health)}
    return health


def push_runtime_available(manager: Any) -> bool:
    """Return whether the push manager has an active WebSocket connection."""
    if not runtime_manager_available(manager):
        return False
    transport_health = getattr(manager, "transport_health", None)
    if not isinstance(transport_health, Mapping):
        return True
    running = transport_health.get("running")
    websocket_open = transport_health.get("websocket_open")
    connected = transport_health.get("connected")
    if running is False or websocket_open is False or connected is False:
        return False
    return True


def runtime_manager_available(manager: Any) -> bool:
    """Return whether a runtime manager is loaded and not a startup failure."""
    if manager is None:
        return False
    health = manager_health(manager)
    if health is None:
        return True
    running = health.get("running")
    connected = health.get("connected")
    if running is False:
        return False
    if connected is False:
        return False
    return True


def safe_bool_or_none(value: Any) -> bool | None:
    """Return a boolean diagnostic value, preserving unknown as None."""
    if isinstance(value, bool):
        return value
    return None


def exception_type_name(value: Any) -> str | None:
    """Return a safe exception class name without exposing the message."""
    if isinstance(value, BaseException):
        return type(value).__name__
    return None


def _runtime_entry_options(runtime: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return loaded config entry options from runtime data."""
    entry = runtime.get("entry")
    options = getattr(entry, "options", None)
    return options if isinstance(options, Mapping) else {}


def _live_updates_intended(runtime: Mapping[str, Any]) -> bool:
    """Return whether this entry intends to use cloud/private live updates."""
    entry = runtime.get("entry")
    data = getattr(entry, "data", None)
    mode = data.get(CONF_CONNECTION_MODE) if isinstance(data, Mapping) else None
    if mode not in {CONNECTION_MODE_CLOUD, CONNECTION_MODE_PRIVATE}:
        return False
    return bool(_runtime_entry_options(runtime).get(CONF_LIVE_UPDATES, DEFAULT_LIVE_UPDATES))


__all__ = [
    "client_capabilities",
    "client_capabilities_for_entry",
    "exception_type_name",
    "manager_health",
    "push_manager_health",
    "push_runtime_available",
    "runtime_health",
    "runtime_manager_available",
    "safe_bool_or_none",
]
