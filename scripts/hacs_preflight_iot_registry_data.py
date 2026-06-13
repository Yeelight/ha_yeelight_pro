"""IoT registry release-preflight contract tokens."""

from __future__ import annotations

from scripts.hacs_preflight_platform_mapping_data import (
    PLATFORM_MAPPING_CONTRACT_TEST_TOKENS,
)
from scripts.hacs_preflight_projector_data import PROJECTOR_CONTRACT_TEST_TOKENS
from scripts.hacs_preflight_iot_registry_projection_data import (
    IOT_PROJECTION_CONTRACT_TEST_TOKENS,
)

IOT_REGISTRY_CONTRACT_TEST_TOKENS: dict[str, dict[str, str]] = {
    "test_iot_registry.py": {
        "platform_for_category": "category-to-platform mapping facade",
        "component_platform_hint": "component platform hints",
        "property_capability": "core property capability lookup",
    },
    "test_openapi_broad_category_projection.py": {
        "test_documented_light_sensor_component_with_motion_stays_light_sensor": (
            "CSV light-sensor component with mv category guard"
        ),
        "test_documented_light_sensor_property_bundle_overrides_broad_light": (
            "documented light-sensor property bundle guard"
        ),
        "zonalShieldIlluminanceRadarSensor": (
            "documented light-sensor radar component guard"
        ),
        "test_openapi_light_payload_still_projects_light": (
            "documented light property projection guard"
        ),
        "test_openapi_light_named_smoke_without_capabilities_is_device_only": (
            "name-only capability rejection guard"
        ),
    },
    "test_device_payload_iot_capabilities.py": {
        "test_runtime_payload_light_sensor_bundle_ignores_user_device_name": (
            "device name cannot override documented IoT capabilities"
        ),
        "sens_range": "documented light-sensor configuration property guard",
    },
    "test_device_payload_runtime_capabilities.py": {
        "test_build_runtime_payloads_infers_real_category_from_properties": (
            "runtime payload capability-first category inference coverage"
        ),
        "test_runtime_payloads_project_entities_from_each_supported_property": (
            "runtime payload property-level entity projection coverage"
        ),
        "test_runtime_payloads_do_not_infer_capabilities_from_safety_name": (
            "runtime payload no device-name type inference coverage"
        ),
    },
    "test_openapi_broad_schema_conflicts.py": {
        "test_conflicting_light_product_schema_does_not_override_sensor_evidence": (
            "runtime sensor evidence overrides conflicting broad light schema"
        ),
        "test_conflicting_light_schema_respects_runtime_temp_control_category": (
            "runtime temp-control category overrides conflicting broad light schema"
        ),
    },
    "test_iot_registry_events.py": {
        "normalize_event_type": "runtime event alias normalization",
        "sensor_contacted": "CSV sensor-contact event normalization coverage",
        "single_spin": "CSV single-spin event normalization coverage",
        "test_panel_click_and_hold_event_component_matrix_matches_iot_docs": (
            "panel event component-scope coverage"
        ),
        "test_release_after_hold_remains_unassigned_until_docs_confirm_components": (
            "unassigned release-after-hold event boundary"
        ),
        "test_dali_knob_spin_remains_unassigned_until_docs_confirm_components": (
            "DALI knob event conservative boundary"
        ),
        "test_approach_events_are_scoped_to_infrared_sensor_docs": (
            "approach event component-scope coverage"
        ),
        "test_csv_unscoped_events_remain_unassigned_until_docs_confirm_components": (
            "unscoped CSV event component boundary"
        ),
    },
    "test_runtime_inference.py": {
        "test_runtime_inferred_contact_sensor_uses_registry_events_without_payload_events": (
            "runtime registry event inference coverage"
        ),
        "test_runtime_inferred_human_sensor_without_component_identity_does_not_guess_events": (
            "runtime broad-category event inference rejection coverage"
        ),
    },
    "test_runtime_inference_iot_coverage.py": {
        "test_runtime_component_identity_keeps_switch_light_as_light": (
            "documented switch light component identity coverage"
        ),
        "test_runtime_floor_heating_projects_climate_from_iot_props": (
            "documented floor-heating runtime climate coverage"
        ),
        "test_runtime_temp_control_projects_climate_and_config_controls": (
            "documented temp-control runtime helper controls coverage"
        ),
        '("light", "light", None)': (
            "runtime switch-light main light candidate coverage"
        ),
        '("climate", "temp_control", None)': (
            "runtime temp-control main climate candidate coverage"
        ),
    },
    "test_iot_registry_csv_contract.py": {
        "test_registry_categories_match_iot_category_csv": (
            "CSV category parity coverage"
        ),
        "test_registry_does_not_add_non_iot_device_categories": (
            "non-IoT fan/outlet category rejection coverage"
        ),
        '("c_waf", "c_xy", "dir", "lv", "on")': (
            "undocumented compatibility property rejection coverage"
        ),
        "test_registry_covers_iot_event_type_csv": (
            "CSV event type id parity coverage"
        ),
        "基础信息_事件类型.csv": "vendor event type CSV coverage",
        "test_registry_covers_all_documented_categorized_components": (
            "CSV component category coverage"
        ),
        "test_registry_uses_csv_access_for_documented_properties": (
            "CSV property access coverage"
        ),
    },
    "iot_registry_csv_helpers.py": {
        "component_properties_from_iot_docs": "CSV component-property helper coverage",
        "property_access_by_prop": "CSV property-access helper coverage",
        "基础信息_组件列表.csv": "vendor component CSV helper coverage",
    },
    "test_device_payload_firmware_metadata.py": {
        "test_runtime_metadata_uses_official_fv_property_as_sw_version": (
            "official fv property HA firmware metadata coverage"
        ),
        "test_runtime_metadata_uses_indexed_fv_param_as_sw_version": (
            "indexed fv property HA firmware metadata coverage"
        ),
        "test_runtime_metadata_uses_component_state_fv_as_sw_version": (
            "canonical component fv firmware metadata coverage"
        ),
    },
    "test_iot_product_catalog.py": {
        "test_registry_product_catalog_matches_iot_product_csv": (
            "CSV product catalog parity coverage"
        ),
        "test_registry_product_catalog_components_and_protocols_are_documented": (
            "product catalog component/protocol coverage"
        ),
        "test_registry_product_catalog_expands_fixed_component_counts": (
            "fixed component-count expansion coverage"
        ),
        "1.7000001e+07": "scientific product pid normalization coverage",
    },
    "test_iot_registry_protocols.py": {
        "connection_protocol": "connection protocol metadata coverage",
        "node_type": "Open API node type coverage",
        "test_open_platform_node_types_are_registered": (
            "documented Open API node type boundary"
        ),
    },
    "test_iot_registry_keys.py": {
        "format_component_property_key": "component property key formatting",
        "parse_component_property_key": "component property key parsing",
        "test_component_property_key_rejects_invalid_values": (
            "component property key validation coverage"
        ),
    },
    "test_iot_registry_property_labels.py": {
        "IOT_PROPERTY_DESCRIPTIONS": "CSV property description registry",
        "test_property_descriptions_match_iot_csv": (
            "CSV property description parity coverage"
        ),
        "test_registry_uses_csv_descriptions_for_property_display_names": (
            "CSV property display-name coverage"
        ),
    },
    "test_iot_registry_integrity.py": {
        "validate_iot_registry": "registry structural validation",
        "duplicate category": "duplicate category validation",
        "HA platform must not be an IoT category": "HA platform guard",
        "maps to both": "normalized event alias collision validation",
    },
    "test_spec_correction.py": {
        "correct_property_schema": "product schema property correction",
        "derive_component_capabilities": "component capability derivation",
        "normalize_property_operators": "operator shape normalization",
        "access\": 7": "documented numeric access coverage",
        "runtime_filtered": "runtime filtering contract",
        "summarize_product_schema_corrections": "aggregate-only correction summary",
    },
    "test_product_schema_converter.py": {
        "test_product_schema_converter_builds_canonical_components": (
            "canonical product schema conversion coverage"
        ),
        "test_product_schema_converter_applies_spec_corrections": (
            "converter applies spec correction coverage"
        ),
        "test_product_schema_converter_deduplicates_component_sources": (
            "component source dedupe coverage"
        ),
    },
    "test_product_schema_metadata.py": {
        "test_product_schema_converter_normalizes_value_range_numbers": (
            "valueRange numeric normalization coverage"
        ),
        "test_product_schema_converter_normalizes_value_list_items": (
            "valueList enum normalization coverage"
        ),
        "normalized metadata": "unit/zoom/scale metadata normalization coverage",
        "test_product_schema_converter_preserves_action_param_zoom_scale": (
            "canonical action param zoom/scale preservation coverage"
        ),
    },
    "test_device_instance_converter.py": {
        "test_device_converter_applies_schema_zoom_scale_to_runtime_state": (
            "runtime read-side zoom/scale conversion coverage"
        ),
    },
    "test_projection_scaled_state.py": {
        "test_sensor_projection_uses_schema_scaled_runtime_state": (
            "HA projection uses scaled runtime state coverage"
        ),
    },
    "test_capability_filter.py": {
        "test_unknown_bool_and_structured_values_do_not_become_controls": (
            "unknown bool/control fallback rejection coverage"
        ),
        "test_unknown_property_does_not_project_to_any_platform": (
            "unknown property platform rejection coverage"
        ),
        "test_event_input_payload_does_not_use_unknown_sensor_fallback": (
            "event-input unknown fallback rejection coverage"
        ),
        "test_low_confidence_components_do_not_use_unknown_sensor_fallback": (
            "low-frequency component fallback rejection coverage"
        ),
        "test_low_confidence_summary_counts_unsupported_without_identifiers": (
            "low-frequency diagnostics aggregate-only coverage"
        ),
    },
    "test_projection_boundaries.py": {
        "test_unknown_bool_value_does_not_project_generic_writable_or_binary_entity": (
            "unknown bool projection boundary coverage"
        ),
        "test_unknown_list_or_mapping_value_does_not_project_select_or_sensor": (
            "unknown enum/structured projection boundary coverage"
        ),
        "test_event_input_unknown_scalar_does_not_project_fallback_sensor": (
            "event-input sensor fallback boundary coverage"
        ),
        "test_low_frequency_component_unknown_scalar_does_not_project_fallback_sensor": (
            "low-frequency component projection boundary coverage"
        ),
        "test_bridge_protocol_metadata_does_not_enable_unknown_fallback_sensor": (
            "bridge protocol metadata projection boundary coverage"
        ),
        "test_unsupported_outlet_on_payload_does_not_project_switch": (
            "unsupported outlet/on switch fallback rejection coverage"
        ),
    },
}
for contract_tokens in (
    IOT_PROJECTION_CONTRACT_TEST_TOKENS,
    PLATFORM_MAPPING_CONTRACT_TEST_TOKENS,
    PROJECTOR_CONTRACT_TEST_TOKENS,
):
    for file_name, tokens in contract_tokens.items():
        IOT_REGISTRY_CONTRACT_TEST_TOKENS.setdefault(file_name, {}).update(tokens)
