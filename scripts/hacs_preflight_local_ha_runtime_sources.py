"""Runtime component source contract tokens for local HA validation."""

from __future__ import annotations

LOCAL_HA_RUNTIME_SOURCE_TOKENS = {
    "scripts/hacs_preflight_local_ha_runtime_sources.py": {
        "LOCAL_HA_RUNTIME_SOURCE_TOKENS": "runtime component source token registry",
        "custom_components/yeelight_pro/core/schema_cache.py": (
            "schema cache source token coverage"
        ),
        "custom_components/yeelight_pro/core/lan_control.py": (
            "LAN source token coverage"
        ),
        "custom_components/yeelight_pro/projector/event_helpers.py": (
            "event projector source token coverage"
        ),
    },
    "custom_components/yeelight_pro/core/schema_cache.py": {
        "_json_safe_schema": "schema cache JSON-safe object guard",
        "_json_safe_value": "schema cache JSON-safe value guard",
        "_SENSITIVE_SCHEMA_STORAGE_KEYS": "schema cache sensitive-key denylist",
        "_SENSITIVE_SCHEMA_STORAGE_VALUE_PATTERNS": (
            "schema cache sensitive-value denylist"
        ),
        "_is_sensitive_schema_storage_key": "schema cache sensitive-key helper",
        "_is_sensitive_schema_storage_text": "schema cache sensitive-text helper",
        "as_storage_data": "schema cache storage serializer",
    },
    "custom_components/yeelight_pro/core/lan_control.py": {
        "async_try_lan_control_device": "LAN device write routing helper",
        "async_try_lan_toggle_device": "LAN device toggle routing helper",
        "async_try_lan_control_group": "LAN group write routing helper",
        "async_try_lan_execute_scene": "LAN scene execution routing helper",
        "async_set_properties": "LAN runtime property write call",
        "\"nt\": 2": "LAN node type for documented device writes",
        "\"nt\": 4": "LAN node type for documented group writes",
        "\"set\": dict(params)": "LAN gateway_set.prop set-payload boundary",
        "\"toggle\": list(properties)": "LAN gateway_set.prop toggle boundary",
        "scenes=[{\"id\": node_id, \"duration\": duration}]": (
            "LAN scene execution payload boundary"
        ),
        "_lan_uint_id": "LAN numeric id fallback guard",
        "safe_error_summary": "LAN control error redaction helper",
    },
    "custom_components/yeelight_pro/core/coordinator_controls.py": {
        "CoordinatorControlMixin": "split coordinator control facade",
        "async_try_lan_control_device": "LAN-first device set route",
        "async_try_lan_toggle_device": "LAN-first device toggle route",
        "async_try_lan_control_group": "LAN-first group route",
        "async_try_lan_execute_scene": "LAN-first scene route",
        "async_execute_control_device": "cloud fallback device set route",
        "async_execute_toggle_device": "cloud fallback device toggle route",
        "async_execute_control_group": "cloud fallback group route",
        "async_execute_scene_command": "cloud fallback scene route",
        "async_request_refresh": "toggle post-write refresh boundary",
    },
    "custom_components/yeelight_pro/core/device_metadata.py": {
        "build_device_info": "HA device metadata builder",
        "enrich_payload_metadata": "runtime payload metadata enrichment",
        "_device_identifiers": "legacy and fallback device identifier guard",
        "_room_name": "room and area suggested_area resolver",
        "_area_name_by_room_id": "area roomIds fallback resolver",
    },
    "custom_components/yeelight_pro/__init__.py": {
        "_async_start_optional_lan_runtime": "optional LAN runtime startup boundary",
        "_OptionalRuntimeStartupFailure": "optional LAN startup failure diagnostics",
        "coordinator.set_lan_runtime(None)": (
            "failed optional LAN runtime not attached for writes"
        ),
        "safe_error_summary(err)": "optional LAN startup log redaction",
    },
    "custom_components/yeelight_pro/entry_migration.py": {
        "stored_device_import_filter_options": "stored import filter migration",
        "device_filter_form_keys": "form-only filter key cleanup",
        "CONF_DEVICE_IMPORT_FILTER": "canonical filter option writeback",
    },
    "custom_components/yeelight_pro/config_flow_helpers.py": {
        "config_flow_options": "options-flow helper facade import",
        "options_schema": "options-flow schema facade export",
        "merge_options": "options-flow merge facade export",
    },
    "custom_components/yeelight_pro/config_flow_options.py": {
        "options_schema": "options-flow schema helper",
        "merge_options": "options-flow merge helper",
        "visible_option_change_count": "options visible-change helper",
        "device_filter_schema_fields": "device filter form schema integration",
        "merge_device_import_filter": "device filter form merge integration",
    },
    "custom_components/yeelight_pro/device_filter.py": {
        "canonical_device_import_filter": "canonical filter storage helper",
        "matches_device_import_filter": "runtime filter matching helper",
        "rules_with_ignored": "normalized filter rule parser use",
        "stored_rules": "stable filter rule serialization use",
        "matches_rules": "runtime include/exclude matching helper use",
    },
    "custom_components/yeelight_pro/device_filter_rules.py": {
        "FILTER_DIMENSION_ALIASES": "filter dimension alias registry",
        "rules_with_ignored": "normalized filter rule parser",
        "stored_rules": "stable filter rule serialization",
        "matches_rules": "runtime include/exclude matching helper",
        "distinct_value_counts": "diagnostics-safe preview counts",
    },
    "custom_components/yeelight_pro/projector/event_helpers.py": {
        "EVENT_COMPONENT_TOKENS": "event input component token registry",
        "event_components": "event component projection helper",
        "event_types": "normalized schema event type helper",
        "event_device_class": "event device class inference helper",
        "event_icon": "event icon inference helper",
        "_registry_component_keys": "registry component alias matching helper",
    },
    "custom_components/yeelight_pro/projector/sensor_helpers.py": {
        "SensorSpec": "sensor projection spec model",
        "sensor_specs": "sensor spec derivation helper",
        "should_project_registry_sensor": "sensor registry boundary helper",
        "runtime_state": "sensor runtime state merge helper",
        "is_event_style_device": "sensor event-input filter helper",
    },
    "custom_components/yeelight_pro/converter/runtime_inference_helpers.py": {
        "infer_runtime_components": "runtime component inference helper",
        "infer_indexed_switch_components": "indexed switch inference helper",
        "build_runtime_property_model": "runtime template property builder",
        "infer_runtime_capabilities": "runtime capability inference helper",
        "RUNTIME_PROPERTY_TEMPLATES": "runtime inference template registry use",
    },
}
