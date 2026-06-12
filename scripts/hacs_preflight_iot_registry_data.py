"""IoT registry release-preflight contract tokens."""

from __future__ import annotations

IOT_REGISTRY_CONTRACT_TEST_TOKENS: dict[str, dict[str, str]] = {
    "test_iot_registry.py": {
        "platform_for_category": "category-to-platform mapping facade",
        "component_platform_hint": "component platform hints",
        "property_capability": "core property capability lookup",
    },
    "test_platform_mapping_contract.py": {
        "platform_candidates_for_payload": "payload-derived HA platform candidates",
        "test_broad_cloud_light_contact_payload_maps_to_binary_and_sensor": (
            "broad cloud light contact payload mapping guard"
        ),
        "test_broad_cloud_light_sensor_payload_maps_to_sensor_only": (
            "broad cloud light sensor mapping guard"
        ),
        "test_category_without_capability_evidence_does_not_project_platform": (
            "category-only platform projection rejection guard"
        ),
        "test_acrc_config_property_does_not_claim_remote_platform": (
            "documented auxiliary bool switch evidence guard"
        ),
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
    "test_projection_unsupported_platforms.py": {
        "test_unsupported_vacuum_payload_does_not_project_entities": (
            "unsupported vacuum projection boundary coverage"
        ),
        "CORE_IOT_DEVICE_CATEGORIES": "core IoT category exclusion coverage",
    },
    "test_projection_matrix.py": {
        "test_light_projection_uses_component_state_over_raw_params": (
            "light component-state merge coverage"
        ),
        "test_switch_light_component_projects_as_light": (
            "switch light component identity coverage"
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
        "test_sensor_schema_projects_unknown_entity_without_runtime_value": (
            "schema-backed missing sensor value unknown-state coverage"
        ),
        "test_binary_sensor_schema_projects_unknown_entity_without_runtime_value": (
            "schema-backed missing binary sensor value unknown-state coverage"
        ),
    },
    "test_projection_entity_categories.py": {
        "test_sensor_entity_exposes_ha_entity_category": (
            "HA entity category projection coverage"
        ),
        "test_gateway_properties_project_diagnostic_sensors_only": (
            "gateway diagnostic/config category projection coverage"
        ),
        "test_dali_energy_projects_runtime_diagnostic_sensors": (
            "DALI runtime diagnostic entity category coverage"
        ),
    },
    "test_device_payload_empty_values.py": {
        "test_runtime_payloads_keep_empty_control_category_metadata_only": (
            "empty value control category metadata-only coverage"
        ),
        "test_runtime_payloads_keep_sensor_category_metadata_without_values": (
            "empty value documented sensor metadata-only coverage"
        ),
        "test_runtime_payloads_keep_empty_cover_and_climate_metadata_only": (
            "empty value control category metadata-only coverage"
        ),
    },
    "test_entity_candidates.py": {
        "test_schema_unknown_actions_do_not_create_device_buttons": (
            "unknown action button fallback rejection coverage"
        ),
    },
    "test_entity_candidates_iot_boundaries.py": {
        "test_fresh_air_temp_control_category_projects_only_fan_candidate": (
            "fresh-air temp_control category fan-only projection coverage"
        ),
        '("fan", "fresh_air")': "fresh-air fan entity candidate coverage",
        '("climate", "climate")': "fresh-air climate candidate rejection coverage",
    },
    "test_entity_candidate_device_sections.py": {
        "test_schema_rich_device_projects_device_page_sections": (
            "schema-rich device page section projection coverage"
        ),
        '("light", "main_light")': "main control section candidate coverage",
        '("sensor", "temperature")': "read-only state section candidate coverage",
        '("event", "main_light")': "event section candidate coverage",
        '"config"': "config entity-category section coverage",
        '"diagnostic"': "diagnostic entity-category section coverage",
    },
    "test_entity_candidate_scenes.py": {
        "test_entity_candidates_project_cloud_scenes_as_buttons_only": (
            "cloud scene button-only projection coverage"
        ),
        "test_entity_candidates_use_friendly_scene_fallback_name": (
            "friendly cloud scene fallback name coverage"
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
    "test_property_control_entities.py": {
        "test_device_number_write_sends_indexed_control_key": (
            "device number indexed control key write coverage"
        ),
        "test_device_select_write_sends_raw_option_code": (
            "device select raw option code write coverage"
        ),
        "test_device_switch_write_sends_int_values_for_indicator_switch": (
            "device switch raw int value write coverage"
        ),
        "suggested_object_id": "friendly device property entity-id coverage",
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
