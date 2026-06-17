"""Runtime diagnostics tests for Yeelight Pro."""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.capabilities import iot_registry
from custom_components.yeelight_pro.const import (
    CONF_DEBUG_MODE,
    CONF_HIDE_UNKNOWN_ENTITIES,
    CONF_SCAN_INTERVAL,
    CONF_TOPOLOGY_CHANGE_REPAIRS,
    CONNECTION_MODE_CLOUD,
    PLATFORMS,
)
from custom_components.yeelight_pro.diagnostics import (
    async_get_config_entry_diagnostics,
)
from .diagnostics_helpers import (
    aggregate_runtime_secret_markers,
    build_aggregate_runtime_coordinator,
    build_diagnostics_entry,
    install_runtime_entry,
)


@pytest.fixture
def diagnostics_entry() -> MagicMock:
    """Build a diagnostics config entry."""
    return build_diagnostics_entry()


@pytest.mark.asyncio
async def test_diagnostics_reports_aggregate_runtime_data(
    hass: HomeAssistant,
    diagnostics_entry: MagicMock,
) -> None:
    """诊断数据只暴露聚合指标，不导出原始设备明细."""
    coordinator = build_aggregate_runtime_coordinator()
    install_runtime_entry(
        hass,
        diagnostics_entry,
        coordinator,
        platforms=["light", "binary_sensor"],
    )

    data = await async_get_config_entry_diagnostics(hass, diagnostics_entry)

    assert data["runtime"]["loaded"] is True
    assert data["runtime"]["platforms"] == ["light", "binary_sensor"]
    assert data["runtime"]["health"] == {
        "last_update_success": True,
        "last_exception_type": None,
        "loaded_platform_count": 2,
        "expected_platform_count": len(PLATFORMS),
        "platforms_match_options": False,
        "live_updates_intended": True,
        "live_updates_active": False,
        "polling_fallback_active": False,
        "polling_fallback_interval_seconds": None,
        "push": None,
        "lan": None,
    }
    assert data["runtime"]["analytics"] == {
        "enabled": False,
        "last_update_success": None,
        "last_exception_type": None,
        "has_snapshot": False,
        "endpoint_count": 0,
        "successful_endpoint_count": 0,
    }
    assert data["runtime"]["client_capabilities"]["connection_mode"] == CONNECTION_MODE_CLOUD
    assert data["runtime"]["options"] == {
        CONF_SCAN_INTERVAL: 15,
        CONF_DEBUG_MODE: True,
        CONF_HIDE_UNKNOWN_ENTITIES: False,
        CONF_TOPOLOGY_CHANGE_REPAIRS: False,
    }
    assert data["runtime"]["option_status"] == {
        "runtime_loaded": True,
        "runtime_reload_required": True,
        "platforms_match_options": False,
        "loaded_platform_count": 2,
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
    assert data["runtime"]["topology_generation"] == 3
    assert data["runtime"]["topology_diff_summary"]["total_added"] == 2
    assert data["runtime"]["topology_diff_summary"]["total_metadata_changed"] == 1
    assert data["runtime"]["topology_diff_summary"]["added"]["devices"] == 1
    assert data["runtime"]["topology_diff_summary"]["added"]["areas"] == 1
    assert data["runtime"]["product_schema_cache_size"] == 2
    assert data["runtime"]["property_hydration"] == {}
    assert data["runtime"]["counts"] == {
        "devices": 2,
        "gateways": 1,
        "areas": 1,
        "rooms": 1,
        "groups": 1,
        "scenes": 1,
    }
    assert data["runtime"]["availability"] == {
        "devices": {"online": 1, "offline": 1, "unknown": 0},
        "gateways": {"online": 0, "offline": 0, "unknown": 1},
    }
    assert data["runtime"]["device_categories"] == {
        "contact_sensor": 1,
        "light": 1,
    }
    assert data["runtime"]["device_platforms"] == {
        "binary_sensor": 1,
        "light": 1,
    }
    registry = iot_registry()
    assert data["runtime"]["iot_registry"] == {
        "valid": True,
        "error_count": 0,
        "categories": len(registry.categories),
        "components": len(registry.components),
        "properties": len(registry.properties),
        "events": len(registry.events),
        "protocols": len(registry.protocols),
    }
    assert data["runtime"]["spec_correction"] == {
        "schemas_seen": 1,
        "components_seen": 2,
        "properties_seen": 3,
        "runtime_filtered_properties": 1,
        "normalized_format_properties": 1,
        "writable_properties": 1,
        "readonly_properties": 1,
    }
    assert data["runtime"]["spec_runtime_inventory"] == {
        "product_models_seen": 2,
        "unique_product_models_seen": 1,
        "components_seen": 2,
        "properties_seen": 3,
        "events_seen": 1,
        "event_params_seen": 1,
        "component_actions_seen": 1,
        "device_actions_seen": 1,
        "action_params_seen": 2,
        "readable_properties": 2,
        "writable_properties": 2,
    }
    assert data["runtime"]["entity_candidates"] == {
        "total": 9,
        "platforms": {
            "button": 1,
            "light": 3,
            "number": 2,
            "select": 3,
        },
        "device_platforms": {},
        "sources": {
            "area": 1,
            "group": 3,
            "house": 3,
            "room": 1,
            "scene": 1,
        },
        "source_classes": {
            "topology": 9,
        },
        "duplicate_key_count": 0,
        "availability": {
            "available": 9,
            "unavailable": 0,
        },
    }
    assert data["runtime"]["entity_registry_reconcile"] == {
        "active": 150,
        "registry_entries": 150,
        "stale": 0,
            "pending_stale": 0,
            "disabled": 0,
            "restored": 0,
            "metadata_updated": 0,
        }
    assert data["runtime"]["entity_registry_cleanup_audit"] == {
        "audit_id": "audit-safe-1",
        "status": "dry_run",
        "stale_entities": 2,
        "stale_devices": 1,
        "disabled_entities": 0,
        "skipped_entities": 0,
        "entity_domains": {
            "light": 1,
            "sensor": 1,
        },
    }
    assert data["runtime"]["capability_filter"] == {
        "hidden_unknown_properties": 0,
        "unsupported_unknown_properties": 1,
    }
    assert data["runtime"]["device_import_filter_preview"] == {
        "enabled": True,
        "rules_count": 2,
        "visible_devices": 1,
        "excluded_devices": 1,
        "matched_devices": 1,
        "total_devices": 2,
        "mode": "or",
        "rules_by_dimension": {
            "devices": 1,
            "rooms": 1,
        },
        "ignored_rule_count": 2,
        "distinct_value_counts_by_dimension": {
            "categories": 2,
            "devices": 2,
            "types": 2,
        },
    }
    assert data["runtime"]["entity_import_filter_preview"] == {
        "total": 9,
        "platforms": {
            "button": 1,
            "light": 3,
            "number": 2,
            "select": 3,
        },
        "device_platforms": {},
        "sources": {
            "area": 1,
            "group": 3,
            "house": 3,
            "room": 1,
            "scene": 1,
        },
        "source_classes": {
            "topology": 9,
        },
        "duplicate_key_count": 0,
        "availability": {
            "available": 9,
            "unavailable": 0,
        },
    }
    assert data["runtime"]["canonical"] == {
        "with_product_schema": 1,
        "with_product_model": 2,
        "with_device_instance": 1,
    }
    assert "devices" not in data["runtime"]

    dumped = json.dumps(data, ensure_ascii=False)
    for secret in aggregate_runtime_secret_markers():
        assert secret not in dumped
