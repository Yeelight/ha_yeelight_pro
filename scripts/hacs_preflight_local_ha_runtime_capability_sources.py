"""Runtime capability source contract tokens for local HA validation."""

from __future__ import annotations

LOCAL_HA_RUNTIME_CAPABILITY_SOURCE_TOKENS = {
    "custom_components/yeelight_pro/capabilities/platform_contract.py": {
        "platform_candidate_projection": "platform candidate projection split import",
        "platform_contract_data": "platform contract data split import",
        "platform_candidates_for_payload": "payload platform candidate facade",
        "PRIMARY_PLATFORM_CONTRACT_ROWS": "platform evidence row source",
    },
    "custom_components/yeelight_pro/capabilities/platform_candidate_projection.py": {
        "log_platform_candidates": "platform candidate debug logging call",
        "has_light_capability_evidence": "light evidence helper use",
        "has_switch_capability_evidence": "switch evidence helper use",
        "READ_ONLY_BOOL_BINARY_PROPS": "binary sensor candidate evidence use",
        "READ_ONLY_SENSOR_PROPS": "sensor candidate evidence use",
        "safe_registry_sensor_property": "registry-backed safe sensor evidence use",
        "documented_writable_enum_property": "select candidate reason coverage",
    },
    "custom_components/yeelight_pro/capabilities/sensor_safety.py": {
        "safe_registry_sensor_property": "registry-backed safe sensor evidence helper",
        "SENSITIVE_SENSOR_TOKENS": "sensor evidence sensitive-field guard",
        "MAIN_ENTITY_SENSOR_EXCLUDED_PROPS": "main entity property exclusion guard",
    },
    "custom_components/yeelight_pro/capabilities/platform_contract_logging.py": {
        "Resolved platform candidates": "platform candidate debug log message",
        "missing_capability_evidence": "platform candidate missing evidence reason",
        "matched_capability_evidence": "platform candidate matched evidence reason",
        "_trace_log_rows": "non-sensitive trace row serializer",
    },
    "custom_components/yeelight_pro/capabilities/platform_contract_evidence.py": {
        "capability_category": "property and component category evidence ordering",
        "has_light_capability_evidence": "explicit light control evidence helper",
        "has_switch_capability_evidence": "explicit switch control evidence helper",
        "has_indexed_switch_control": "indexed switch capability evidence helper",
        "ignored_property_reason": "stable ignored property reason helper",
    },
    "custom_components/yeelight_pro/capabilities/platform_contract_data.py": {
        "PRIMARY_PLATFORM_CONTRACT_ROWS": "platform evidence row registry",
        "PRIMARY_CATEGORY_CANDIDATES": "IoT category candidate registry",
        "READ_ONLY_BOOL_BINARY_PROPS": "binary sensor property candidate registry",
        "READ_ONLY_SENSOR_PROPS": "sensor property candidate registry",
        "CLIMATE_CANDIDATE_PROPS": "climate property candidate registry",
        "LIGHT_CONTROL_PROPS": "light property candidate registry",
    },
    "custom_components/yeelight_pro/capabilities/property_aliases.py": {
        "PROPERTY_ALIASES": "documented property alias registry",
        "localToken": "local token property alias coverage",
    },
    "custom_components/yeelight_pro/capabilities/property_index.py": {
        "enrich_property_component_memberships": (
            "official component-property membership derivation"
        ),
        "_property_memberships": "property to component index builder",
    },
}

