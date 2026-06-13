"""IoT projection release-preflight contract tokens."""

from __future__ import annotations

IOT_PROJECTION_CONTRACT_TEST_TOKENS: dict[str, dict[str, str]] = {
    "test_projection_component_boundaries.py": {
        "test_light_component_category_power_only_does_not_project_light": (
            "component category-only light rejection coverage"
        ),
        "test_relay_component_category_power_only_does_not_project_switch": (
            "component category-only switch rejection coverage"
        ),
        "test_curtain_component_category_without_position_does_not_project_cover": (
            "component category-only cover rejection coverage"
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
        "test_light_sensor_auxiliary_switch_candidates_match_projected_entities": (
            "runtime sensor auxiliary switch candidate/entity parity coverage"
        ),
        '("fan", "fresh_air")': "fresh-air fan entity candidate coverage",
        '("climate", "climate")': "fresh-air climate candidate rejection coverage",
        '("switch", "light_sensor_blp_switch", "config")': (
            "light-sensor switch entity candidate coverage"
        ),
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
    "test_entity_candidate_logging.py": {
        "test_entity_candidate_logging_reports_projected_domain_summary": (
            "entity candidate projection debug summary coverage"
        ),
        "test_entity_candidate_logging_reports_device_page_sections": (
            "entity candidate device-page section debug coverage"
        ),
        "test_entity_candidate_logging_reports_filter_skip": (
            "entity candidate filter skip debug coverage"
        ),
        "sections={'config'": "device-page section aggregate logging coverage",
        "device_import_filter_excluded": "stable filter skip reason coverage",
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
