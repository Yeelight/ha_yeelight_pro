"""IoT registry release-preflight contract tokens."""

from __future__ import annotations

IOT_REGISTRY_CONTRACT_TEST_TOKENS: dict[str, dict[str, str]] = {
    "test_iot_registry.py": {
        "platform_for_category": "category-to-platform mapping facade",
        "component_platform_hint": "component platform hints",
        "property_capability": "core property capability lookup",
    },
    "test_iot_registry_events.py": {
        "normalize_event_type": "runtime event alias normalization",
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
    "test_event_projection.py": {
        "test_schema_declared_sensor_events_project_event_and_trigger": (
            "schema-declared sensor event projection coverage"
        ),
        "human_enter": "human approach event projection coverage",
        "power_alarm": "power alarm schema event projection coverage",
    },
    "test_capability_filter.py": {
        "test_unknown_bool_and_structured_values_do_not_become_controls": (
            "unknown bool/control fallback rejection coverage"
        ),
        "test_unknown_property_fallback_is_sensor_only": (
            "unknown writable platform fallback rejection coverage"
        ),
        "test_event_input_payload_does_not_use_unknown_sensor_fallback": (
            "event-input unknown fallback rejection coverage"
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
        "test_vacuum_projection_is_experimental_and_requires_explicit_vacuum_payload": (
            "vacuum experimental projection boundary coverage"
        ),
        "CORE_IOT_DEVICE_CATEGORIES": "core IoT category exclusion coverage",
    },
    "test_projection_matrix.py": {
        "test_light_projection_uses_component_state_over_raw_params": (
            "light component-state merge coverage"
        ),
        "test_light_projection_preserves_gateway_via_device_info": (
            "gateway via_device projection coverage"
        ),
    },
    "test_projection_event_topology.py": {
        "test_scene_panel_projects_events_not_sensors": (
            "scene panel event-only projection coverage"
        ),
        "test_gateway_only_provides_topology_device_info": (
            "gateway topology-only projection coverage"
        ),
    },
    "test_projection_state_sensors.py": {
        "test_raw_params_and_component_state_merge_without_losing_unmodeled_params": (
            "raw params and component state merge coverage"
        ),
    },
    "test_entity_candidates.py": {
        "test_schema_unknown_actions_do_not_create_device_buttons": (
            "unknown action button fallback rejection coverage"
        ),
    },
    "test_group_number_controls.py": {
        "test_group_brightness_number_uses_iot_property_key": (
            "group brightness control uses Yeelight l property"
        ),
        "assert_awaited_once_with": "group number command path assertion",
        '{"l":': "group brightness command payload",
        "test_group_color_temp_number_uses_iot_property_key": (
            "group color temperature control uses Yeelight ct property"
        ),
        '{"ct":': "group color temperature command payload",
    },
    "test_select_dynamic_options.py": {
        "test_room_select_uses_latest_coordinator_rooms": (
            "room select dynamic options coverage"
        ),
        "test_group_select_uses_latest_coordinator_groups": (
            "group select dynamic options coverage"
        ),
        "test_scene_select_uses_latest_coordinator_scenes": (
            "scene select dynamic options coverage"
        ),
        "EMPTY_OPTION": "empty select option fallback coverage",
        "assert_not_awaited": "unknown scene select does not execute",
    },
}
