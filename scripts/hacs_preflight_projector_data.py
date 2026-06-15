"""Projector release-preflight contract tokens."""

from __future__ import annotations

PROJECTOR_CONTRACT_TEST_TOKENS: dict[str, dict[str, str]] = {
    "test_event_projection.py": {
        "test_schema_declared_sensor_events_project_event_and_trigger": (
            "schema-declared sensor event projection coverage"
        ),
        "test_occupancy_sensor_motion_events_project_event_and_trigger": (
            "occupancy sensor motion event projection coverage"
        ),
        "human_enter": "human approach event projection coverage",
        "power_alarm": "power alarm schema event projection coverage",
    },
    "test_projector_skip_logging.py": {
        "test_sensor_projection_logs_missing_property_evidence": (
            "sensor projector missing-evidence debug log coverage"
        ),
        "test_binary_sensor_projection_logs_event_style_block": (
            "binary sensor projector skip debug log coverage"
        ),
        "test_event_projection_logs_unsupported_schema_events": (
            "event projector unsupported schema debug log coverage"
        ),
        "test_cover_projection_logs_missing_position_evidence": (
            "cover projector missing-position debug log coverage"
        ),
        "test_climate_projection_logs_missing_property_evidence": (
            "climate projector missing-evidence debug log coverage"
        ),
        "missing_sensor_property_evidence": "stable sensor skip reason coverage",
        "event_style_component_owns_property": (
            "stable event-input skip reason coverage"
        ),
        "missing_supported_event_evidence": (
            "stable unsupported event skip reason coverage"
        ),
        "missing_cover_position_properties": (
            "stable cover missing-position skip reason coverage"
        ),
        "missing_climate_properties": (
            "stable climate missing-property skip reason coverage"
        ),
        "test_runtime_registry_event_inference_logs_without_user_names": (
            "runtime registry event inference debug log coverage"
        ),
        "missing_registry_component_identity": (
            "stable registry event inference skip reason coverage"
        ),
    },
    "test_openapi_subdevice_events.py": {
        "test_openapi_occupancy_subdevice_uses_registry_events_without_payload_events": (
            "OpenAPI cid-backed registry event inference coverage"
        ),
        "test_openapi_contact_subdevice_uses_unique_registry_category_events": (
            "OpenAPI unique category registry event inference coverage"
        ),
        "test_openapi_human_category_without_component_identity_does_not_guess_events": (
            "OpenAPI broad category event inference rejection coverage"
        ),
    },
    "test_cover_multi_component_projection.py": {
        "test_multi_curtain_components_create_cover_candidates": (
            "multi-curtain component cover candidate coverage"
        ),
        "test_multi_curtain_projection_reads_component_scoped_state_keys": (
            "multi-curtain component scoped state-key coverage"
        ),
        "test_zebra_blind_schema_exposes_tilt_without_current_state": (
            "zebra blind schema-declared tilt coverage"
        ),
        "multi_curtain_payload": (
            "multi-curtain component fixture coverage"
        ),
        '"2-cp"': "component-scoped cover current-position key coverage",
        '"2-tra"': "component-scoped cover tilt target key coverage",
    },
    "test_climate_multi_component_projection.py": {
        "test_multi_climate_components_create_climate_candidates": (
            "multi-climate component climate candidate coverage"
        ),
        "test_multi_climate_entity_uses_component_control_key": (
            "multi-climate component control-key coverage"
        ),
        '"2-actt"': "component-scoped climate target key coverage",
        '"2-acp"': "component-scoped climate power key coverage",
        '"2-acm"': "component-scoped climate mode key coverage",
        '"2-acf"': "component-scoped climate fan-speed key coverage",
    },
    "test_climate_entity.py": {
        "test_set_hvac_mode_sends_documented_ac_mode": (
            "documented acm HVAC mode write coverage"
        ),
        "test_set_fan_mode_sends_documented_fan_speed": (
            "documented acf fan-speed write coverage"
        ),
        "test_climate_exposes_documented_mode_and_fan_properties": (
            "documented climate mode and fan projection coverage"
        ),
    },
    "test_projection_component_state_keys.py": {
        "test_multi_component_sensor_reads_component_scoped_state_keys": (
            "multi-component sensor scoped state-key coverage"
        ),
        "test_multi_component_binary_sensor_reads_component_scoped_state_keys": (
            "multi-component binary sensor scoped state-key coverage"
        ),
        "test_component_scoped_state_read_logs_redacted_context": (
            "component-scoped state read debug log coverage"
        ),
        "test_light_reads_component_scoped_state_keys": (
            "component-scoped light state-key coverage"
        ),
        "test_switch_reads_component_scoped_state_key": (
            "component-scoped switch state-key coverage"
        ),
        "test_fan_reads_component_scoped_state_keys": (
            "component-scoped fan state-key coverage"
        ),
        "test_property_controls_read_component_scoped_state_keys": (
            "component-scoped property controls state-key coverage"
        ),
        "component_scoped_state_read": (
            "stable component-scoped state read log action coverage"
        ),
        '"2-luminance"': "component-scoped illuminance state key coverage",
        '"2-mv"': "component-scoped motion state key coverage",
    },
    "test_cover_entity.py": {
        "test_multi_component_cover_sends_component_target_key": (
            "multi-curtain component control-key coverage"
        ),
        "test_multi_component_zebra_blind_tilt_sends_component_key": (
            "multi-curtain component tilt control-key coverage"
        ),
        '"2-tp"': "component-scoped cover target key coverage",
        '"2-tra"': "component-scoped cover tilt target key coverage",
    },
}
