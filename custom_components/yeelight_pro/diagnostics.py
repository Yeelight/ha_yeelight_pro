"""Yeelight Pro diagnostics support."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .capabilities.filter import summarize_unknown_capabilities
from .capabilities import iot_registry, validate_iot_registry
from .const import (
    CONF_DEVICE_IMPORT_FILTER,
    CONF_DEBUG_MODE,
    CONF_HIDE_UNKNOWN_ENTITIES,
    CONF_SCAN_INTERVAL,
    CONF_TOPOLOGY_CHANGE_REPAIRS,
    DEFAULT_TOPOLOGY_CHANGE_REPAIRS,
    DOMAIN,
    get_enabled_platforms,
)
from .diagnostic_runtime import (
    client_capabilities,
    client_capabilities_for_entry,
    exception_type_name,
    runtime_health,
    safe_bool_or_none,
)
from .diagnostic_summaries import (
    availability_counts,
    count_with_key,
    counter_known_values,
    entity_candidate_diagnostics,
    entity_import_filter_preview_diagnostics,
    mapping_values,
    safe_len,
    spec_correction_diagnostics,
    spec_runtime_inventory_diagnostics,
    topology_diff_summary,
)
from .diagnostic_options import option_status_diagnostics
from .diagnostic_payloads import (
    TO_REDACT,
    config_data_diagnostics as _config_data_diagnostics,
    options_diagnostics as _options_diagnostics,
)
from .device_filter import preview_device_import_filter
from .entity_lifecycle import (
    entity_registry_cleanup_diagnostics,
    entity_registry_reconcile_diagnostics,
)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a Yeelight Pro config entry."""
    runtime = _runtime_entry(hass, entry)
    diagnostics: dict[str, Any] = {
        "config_entry": {
            "entry_id": entry.entry_id,
            "data": _config_data_diagnostics(entry),
            "options": _options_diagnostics(entry),
        },
        "runtime": _build_runtime_diagnostics(entry, runtime),
    }
    return async_redact_data(diagnostics, TO_REDACT)


def _runtime_entry(hass: HomeAssistant, entry: ConfigEntry) -> Mapping[str, Any]:
    """Return the loaded runtime entry, if present."""
    runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    return runtime if isinstance(runtime, Mapping) else {}


def _build_runtime_diagnostics(
    entry: ConfigEntry,
    runtime: Mapping[str, Any],
) -> dict[str, Any]:
    """Build aggregate runtime diagnostics without raw device payloads."""
    coordinator = runtime.get("coordinator")
    if coordinator is None:
        capabilities = client_capabilities_for_entry(entry)
        capabilities.update(
            {
                "cloud_http_polling": False,
                "private_http_polling": False,
                "lan_direct_control": False,
                "scan_login_runtime": False,
                "websocket_transport_runtime": False,
                "push_connection": False,
                "websocket_subscription": False,
                "websocket_event_notifications": False,
                "local_gateway_control": False,
                "lan_control": False,
            }
        )
        return {
            "loaded": False,
            "client_capabilities": capabilities,
            "options": _options_diagnostics(entry),
            "option_status": option_status_diagnostics(entry, runtime, None),
            "iot_registry": _iot_registry_diagnostics(),
        }

    devices = mapping_values(getattr(coordinator, "devices", {}))
    gateways = mapping_values(getattr(coordinator, "gateways", {}))
    hide_unknown_entities = getattr(coordinator, "hide_unknown_entities", None)
    device_import_filter = _entry_option(runtime, CONF_DEVICE_IMPORT_FILTER, {})
    return {
        "loaded": True,
        "platforms": list(runtime.get("platforms") or []),
        "health": runtime_health(runtime, coordinator),
        "analytics": _analytics_diagnostics(runtime),
        "client_capabilities": client_capabilities(runtime),
        "options": {
            CONF_SCAN_INTERVAL: getattr(coordinator, "scan_interval", None),
            CONF_DEBUG_MODE: getattr(coordinator, "debug_mode", None),
            CONF_HIDE_UNKNOWN_ENTITIES: hide_unknown_entities,
            CONF_TOPOLOGY_CHANGE_REPAIRS: _entry_option(
                runtime,
                CONF_TOPOLOGY_CHANGE_REPAIRS,
                DEFAULT_TOPOLOGY_CHANGE_REPAIRS,
            ),
        },
        "option_status": option_status_diagnostics(entry, runtime, coordinator),
        "topology_generation": getattr(coordinator, "topology_generation", None),
        "topology_diff_summary": topology_diff_summary(coordinator),
        "product_schema_cache_size": getattr(
            coordinator,
            "product_schema_cache_size",
            None,
        ),
        "property_hydration": _property_hydration_diagnostics(coordinator),
        "counts": {
            "devices": len(devices),
            "gateways": len(gateways),
            "areas": safe_len(getattr(coordinator, "areas", [])),
            "rooms": safe_len(getattr(coordinator, "rooms", [])),
            "groups": safe_len(getattr(coordinator, "groups", [])),
            "scenes": safe_len(getattr(coordinator, "scenes", [])),
        },
        "availability": {
            "devices": availability_counts(devices),
            "gateways": availability_counts(gateways),
        },
        "device_categories": counter_known_values(
            devices,
            "category",
            known_values=set(iot_registry().category_map),
        ),
        "device_platforms": counter_known_values(
            devices,
            "type",
            known_values=set(get_enabled_platforms({})),
        ),
        "iot_registry": _iot_registry_diagnostics(),
        "spec_correction": spec_correction_diagnostics(devices),
        "spec_runtime_inventory": spec_runtime_inventory_diagnostics(devices),
        "entity_candidates": entity_candidate_diagnostics(coordinator),
        "entity_registry_reconcile": entity_registry_reconcile_diagnostics(
            coordinator
        ),
        "entity_registry_cleanup_audit": entity_registry_cleanup_diagnostics(
            coordinator
        ),
        "capability_filter": summarize_unknown_capabilities(
            devices,
            hide_unknown_entities=bool(hide_unknown_entities),
        ),
        "device_import_filter_preview": preview_device_import_filter(
            devices,
            device_import_filter,
        ).as_dict(),
        "entity_import_filter_preview": entity_import_filter_preview_diagnostics(
            coordinator,
            device_import_filter,
        ),
        "canonical": {
            "with_product_schema": count_with_key(devices, "product_schema"),
            "with_product_model": count_with_key(devices, "ha_product_model"),
            "with_device_instance": count_with_key(devices, "ha_device_instance"),
        },
    }


def _entry_option(runtime: Mapping[str, Any], key: str, default: Any) -> Any:
    """Return an option value from the loaded config entry."""
    entry = runtime.get("entry")
    options = getattr(entry, "options", None)
    return options.get(key, default) if isinstance(options, Mapping) else default


def _analytics_diagnostics(runtime: Mapping[str, Any]) -> dict[str, Any]:
    """Return analytics coordinator availability without raw API details."""
    coordinator = runtime.get("analytics_coordinator")
    if coordinator is None:
        return {
            "enabled": False,
            "last_update_success": None,
            "last_exception_type": None,
            "has_snapshot": False,
            "endpoint_count": 0,
            "successful_endpoint_count": 0,
        }
    snapshot = getattr(coordinator, "data", None)
    endpoint_errors = getattr(snapshot, "endpoint_errors", None)
    return {
        "enabled": True,
        "last_update_success": safe_bool_or_none(
            getattr(coordinator, "last_update_success", None),
        ),
        "last_exception_type": exception_type_name(
            getattr(coordinator, "last_exception", None),
        ),
        "has_snapshot": snapshot is not None,
        "endpoint_count": getattr(snapshot, "endpoint_count", 0)
        if snapshot is not None
        else 0,
        "successful_endpoint_count": getattr(
            snapshot,
            "successful_endpoint_count",
            0,
        )
        if snapshot is not None
        else 0,
        "endpoint_errors": {
            key: value
            for key, value in (endpoint_errors or {}).items()
            if isinstance(key, str) and isinstance(value, str)
        },
    }


def _property_hydration_diagnostics(coordinator: Any) -> dict[str, int]:
    """Return safe aggregate read-side hydration diagnostics."""
    diagnostics = getattr(coordinator, "property_hydration_diagnostics", None)
    if not isinstance(diagnostics, Mapping):
        return {}
    return {
        str(key): value
        for key, value in diagnostics.items()
        if isinstance(key, str) and isinstance(value, int)
    }


def _iot_registry_diagnostics() -> dict[str, Any]:
    """Return safe static IoT registry health diagnostics."""
    registry = iot_registry()
    errors = validate_iot_registry(registry)
    return {
        "valid": not errors,
        "error_count": len(errors),
        "categories": len(registry.categories),
        "components": len(registry.components),
        "properties": len(registry.properties),
        "events": len(registry.events),
        "protocols": len(registry.protocols),
    }
