"""Runtime component source contract tokens for local HA validation."""

from __future__ import annotations

LOCAL_HA_RUNTIME_SOURCE_TOKENS = {
    "scripts/hacs_preflight_local_ha_runtime_sources.py": {
        "LOCAL_HA_RUNTIME_SOURCE_TOKENS": "runtime component source token registry",
        "custom_components/yeelight_pro/core/schema_cache.py": "schema cache source token coverage",
        "custom_components/yeelight_pro/core/lan_control.py": "LAN source token coverage",
        "custom_components/yeelight_pro/core/lan_sensor_values.py": (
            "LAN sensor value normalization source token coverage"
        ),
        "custom_components/yeelight_pro/core/lan_topology_merge.py": (
            "LAN topology merge source token coverage"
        ),
        "custom_components/yeelight_pro/core/lan_topology_payload.py": (
            "LAN topology payload source token coverage"
        ),
        "custom_components/yeelight_pro/core/firmware_metadata.py": (
            "firmware metadata source token coverage"
        ),
        "custom_components/yeelight_pro/projector/event_identity_helpers.py": (
            "event identity helper source token coverage"
        ),
        "custom_components/yeelight_pro/projector/climate_helpers.py": (
            "climate projector value helper coverage"
        ),
        "custom_components/yeelight_pro/projector/event_helpers.py": (
            "event projector source token coverage"
        ),
        "custom_components/yeelight_pro/projector/property_controls.py": (
            "writable property control projector source token coverage"
        ),
        "custom_components/yeelight_pro/projector/common.py": "projector shared state-key helper coverage",
        "custom_components/yeelight_pro/projector/property_control_common.py": (
            "writable property control shared helper coverage"
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
        '"device": 2': "LAN node type for documented device writes",
        '"group": 4': "LAN node type for documented group writes",
        "\"set\": dict(params)": "LAN gateway_set.prop set-payload boundary",
        "\"toggle\": list(properties)": "LAN gateway_set.prop toggle boundary",
        "scenes=[{\"id\": node_id, \"duration\": duration}]": (
            "LAN scene execution payload boundary"
        ),
        "_lan_uint_id": "LAN numeric id fallback guard",
        "safe_error_summary": "LAN control error redaction helper",
    },
    "custom_components/yeelight_pro/core/lan_sensor_values.py": {
        "normalize_lan_device_params": "LAN sensor value normalization helper",
        "LAN_TEMPERATURE_HUMIDITY_TYPE = 136": (
            "documented LAN temperature humidity sensor type"
        ),
        "LAN_TEMPERATURE_HUMIDITY_SCALE = 100": (
            "documented LAN temperature humidity scale"
        ),
    },
    "custom_components/yeelight_pro/core/lan_topology_merge.py": {
        "merge_lan_payload": "LAN same-id physical endpoint merge helper",
        "mixed_lan_types": "LAN mixed endpoint classification marker",
        "_merged_rows_by_identity": "LAN merged row de-duplication helper",
    },
    "custom_components/yeelight_pro/core/lan_topology_payload.py": {
        "build_lan_topology_payloads": "LAN topology normalization facade",
        "_LAN_TYPE_SPECS": "documented LAN type to IoT category registry",
        "builder.normalize(payload, {})": "DevicePayloadBuilder normalization boundary",
        "builder.attach_canonical_models_if_available": (
            "canonical runtime device rebuild boundary"
        ),
        "platform_candidates_for_payload": "HA platform candidate metadata boundary",
        "NODE_TYPE_DEVICE = 2": "documented LAN Mesh sub-device node type",
        "NODE_TYPE_SCENE = 6": "documented LAN scene node type",
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
        "device_model_name": "friendly model display helper reuse",
        "_device_identifiers": "legacy and fallback device identifier guard",
        "_room_name": "room and area suggested_area resolver",
        "_area_name_by_room_id": "area roomIds fallback resolver",
    },
    "custom_components/yeelight_pro/core/firmware_metadata.py": {
        "firmware_version": "official fv firmware metadata helper",
        "_FIRMWARE_VERSION_KEYS": "top-level firmware metadata aliases",
        "parse_component_property_key": "indexed fv property key parsing",
    },
    "custom_components/yeelight_pro/core/property_hydration_summary.py": {
        "PropertyHydrationDiagnostics": (
            "property hydration aggregate diagnostics model"
        ),
        "record_requests": "hydration request aggregate coverage",
        "record_response": "hydration response aggregate coverage",
        "as_dict": "hydration diagnostics JSON-safe serializer",
    },
    "custom_components/yeelight_pro/device_display.py": {
        "device_type_label": "friendly picker device type summary",
        "channel_name_label": "friendly sub-entity channel label",
        "_CATEGORY_LABELS": "category label registry",
    },
    "custom_components/yeelight_pro/device_channel_semantics.py": {
        "uses_output_channel_label": "input/output channel naming semantics",
        "OUTPUT_CHANNEL_CATEGORIES": "relay output channel category guard",
        "EVENT_INPUT_CATEGORIES": "event input channel category guard",
    },
    "custom_components/yeelight_pro/device_channel_generated_names.py": {
        "looks_like_generated_channel_name": "generated channel name replacement guard",
        "generated_channel_name_index": "generated channel index parser guard",
        "CHANNEL_NUMERAL_LABELS": "Chinese channel numeral label registry",
    },
    "custom_components/yeelight_pro/device_select.py": {
        "YeelightProDeviceSelect": "device select entity split helper",
        "iter_device_select_entities": "device select dynamic entity factory",
        "suggested_entity_object_id": "device select friendly entity-id guard",
        "project_select_controls": "schema-backed writable enum projection source",
    },
    "custom_components/yeelight_pro/entity_device_id.py": {
        "source_device_id": "device payload source-id resolver",
        "_normalize_device_id": "numeric device id normalization guard",
    },
    "custom_components/yeelight_pro/device_channels.py": {
        "channel_name_label": "friendly sub-entity channel label",
        "switch_channel_count_hint": "switch channel count inference",
        "_CHANNEL_LABELS": "indexed switch channel label registry",
        "_POSITIONAL_CHANNEL_LABELS": "physical switch position label registry",
    },
    "custom_components/yeelight_pro/projector/climate_helpers.py": {
        "AC_MODE_TO_HVAC": "documented Yeelight acm to HA HVAC mapping",
        "HVAC_TO_AC_MODE": "HA HVAC to documented Yeelight acm mapping",
        "AC_FAN_LABELS": "documented Yeelight acf label mapping",
        "climate_raw_mode_for_hvac": "climate mode write helper",
        "climate_raw_fan_for_mode": "climate fan speed write helper",
    },
    "custom_components/yeelight_pro/entity_category.py": {
        "entity_category_for_property": "projection entity category resolver",
        "ha_entity_category": "HA EntityCategory conversion helper",
        "CONFIG_PROPERTIES": "config property category registry",
        "DIAGNOSTIC_PROPERTIES": "diagnostic property category registry",
    },
    "custom_components/yeelight_pro/entity_lifecycle_entity_id.py": {
        "safe_entity_id_migration": "safe legacy entity-id migration helper",
        "registry_entity_ids": "entity-id conflict set helper",
        "_legacy_unique_id_tail": "legacy channel suffix detector",
    },
    "custom_components/yeelight_pro/ha_house_registry.py": {
        "sync_house_device": "house helper registry sync facade",
        "_house_device_entries": "legacy house helper registry matcher",
        "_safe_house_identifiers": "duplicate house helper identifier guard",
        "is_house_placeholder_name": "placeholder house device name cleanup guard",
    },
    "custom_components/yeelight_pro/entry_setup.py": {
        "async_start_optional_lan_runtime": "optional LAN runtime startup boundary",
        "OptionalRuntimeStartupFailure": "optional LAN startup failure diagnostics",
        "coordinator.set_lan_runtime(None)": (
            "failed optional LAN runtime not attached for writes"
        ),
        "safe_error_summary(err)": "optional LAN startup log redaction",
    },
    "custom_components/yeelight_pro/config_flow_lan.py": {
        "LanConfigFlowMixin": "LAN config-flow split mixin",
        "async_step_lan_config": "LAN config-flow step",
        "_create_lan_entry": "LAN config-entry creation helper",
        "async_validate_lan_connection": "LAN config validation boundary",
        "CONF_LOCAL_GATEWAY_CONTROL": "LAN-only entry enables local gateway runtime",
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
    "custom_components/yeelight_pro/projector/event_input.py": {
        "EVENT_INPUT_CATEGORIES": "documented event-input category registry",
        "EVENT_STYLE_PRODUCT_TYPES": "documented LAN event-input product type registry",
        "event_input_category_for_device": "event-input device category resolver",
        "event_input_component_category": "event-input component category resolver",
        "is_event_input_device": "shared event-input device guard",
    },
    "custom_components/yeelight_pro/projector/event_identity_helpers.py": {
        "event_input_category": "schema event-input identity helper",
        "product_model_has_official_component_names": (
            "runtime user component names excluded from type inference"
        ),
        "has_registry_supported_events": "registry component alias matching helper",
        "registry_component_keys": "registry component key expansion helper",
        "normalize_component_alias": "registry component alias normalizer",
    },
    "custom_components/yeelight_pro/projector/event_helpers.py": {
        "SAFETY_EVENT_TYPES": "safety alarm schema event types",
        "is_safety_event_device": "safety event schema-evidence route",
        "event_components": "event component projection helper",
        "event_types": "normalized schema event type helper",
        "event_device_class": "event device class inference helper",
        "event_icon": "event icon inference helper",
    },
    "custom_components/yeelight_pro/event_identity.py": {
        "SAFETY_EVENT_COMPONENT_ID": "shared safety event component id",
        "SAFETY_EVENT_TYPES": "shared safety event type registry",
        "is_safety_event_device": "shared safety event identity helper",
        "is_safety_event_type": "shared safety event type helper",
    },
    "custom_components/yeelight_pro/event_support.py": {
        "SAFETY_EVENT_COMPONENT_ID": "runtime safety event component route",
        "is_safety_event_type": "runtime safety event type route",
        "is_safety_event_device": "runtime safety event schema-evidence route",
    },
    "custom_components/yeelight_pro/projector/sensor_helpers.py": {
        "SensorSpec": "sensor projection spec model",
        "sensor_specs": "sensor spec derivation helper",
        "should_project_registry_sensor": "sensor registry boundary helper",
        "runtime_state": "sensor runtime state merge helper",
        "is_event_style_device": "sensor event-input filter helper",
    },
    "custom_components/yeelight_pro/projector/sensor_metadata.py": {
        "SENSOR_LABELS": "registry-backed sensor metadata labels",
        "registry_sensor_spec": "registry-backed sensor spec helper",
        "sensor_entity_category": "sensor entity category helper",
    },
    "custom_components/yeelight_pro/projector/property_controls.py": {
        "project_number_controls": "device number control projection helper",
        "project_select_controls": "device select control projection helper",
        "project_switch_controls": "device switch config control projection helper",
        "HASwitchControlProjection": "documented bool config switch projection model",
    },
    "custom_components/yeelight_pro/projector/property_control_common.py": {
        "is_writable_auxiliary_property": "main-entity duplicate property guard",
        "is_writable_auxiliary_bool_property": "writable bool config property guard",
        "component_state_key": "indexed Yeelight control key helper",
        "MAIN_ENTITY_PROPS": "main entity property exclusion registry",
        "AUXILIARY_BOOL_CONFIG_PROPS": "documented bool config property registry",
    },
    "custom_components/yeelight_pro/projector/common.py": {
        "component_state_key": "component-scoped state key resolver",
        "component_state_key_map": "component-state extension map parser",
        "format_component_property_key": "indexed Yeelight control key formatter",
        "state_value": "component-scoped state value reader",
    },
    "custom_components/yeelight_pro/converter/openapi_properties.py": {
        "openapi_property_model": "OpenAPI property metadata conversion helper",
        "property_spec": "CSV registry-backed property metadata fallback",
        "openapi_property_access": "OpenAPI operators/access parser",
        "openapi_runtime_properties": "top-level OpenAPI properties parser",
        "openapi_value_range": "OpenAPI valueRange parser",
        "openapi_value_list": "OpenAPI valueList parser",
    },
    "custom_components/yeelight_pro/converter/runtime_inference_helpers.py": {
        "infer_runtime_components": "runtime component inference helper",
        "infer_subdevice_components": "OpenAPI sub-device inference facade",
        "infer_indexed_switch_components": "indexed switch inference helper",
        "build_runtime_property_model": "runtime template property builder",
        "infer_openapi_events": "explicit OpenAPI runtime event inference helper",
        "infer_runtime_capabilities": "runtime capability inference helper",
        "_infer_runtime_properties": "runtime property builder facade reuse",
    },
    "custom_components/yeelight_pro/converter/runtime_property_builder.py": {
        "build_runtime_property_model": "runtime template property builder",
        "infer_runtime_properties": "runtime property inference helper",
        "openapi_runtime_properties": "top-level OpenAPI property metadata reuse",
        "RUNTIME_PROPERTY_TEMPLATES": "runtime template registry use",
        "property_spec": "registry-backed runtime property fallback",
        "ValueItemModel": "runtime registry enum model conversion",
    },
    "custom_components/yeelight_pro/converter/runtime_model_labels.py": {
        "capability_model_name": "runtime capability model label helper",
        "开关控制器": "relay-switch capability-first model label",
    },
    "custom_components/yeelight_pro/converter/runtime_registry_events.py": {
        "registry_component_for_identity": "runtime registry event identity matcher",
        "registry_component_event_models": "runtime registry event model builder",
        "log_registry_event_inference": "runtime registry event inference debug log",
        "missing_registry_component_identity": "runtime registry event skip reason",
    },
    "custom_components/yeelight_pro/converter/runtime_template_selector.py": {
        "runtime_template_key": "runtime property-evidence template selector",
        "runtime_property_ids_from_params": "runtime property id extraction helper",
        "category_from_property_keys": "registry-backed category evidence reuse",
    },
    "custom_components/yeelight_pro/converter/runtime_templates.py": {
        "RUNTIME_CONTROL_TEMPLATES": "runtime control template split import",
        "RUNTIME_SENSOR_TEMPLATES": "runtime sensor template split import",
        "RUNTIME_HVAC_TEMPLATES": "runtime HVAC template split import",
        "INDEXED_SWITCH_KEY_RE": "runtime indexed switch regex facade",
        "RUNTIME_PROPERTY_TEMPLATES": "runtime template facade registry",
    },
    "custom_components/yeelight_pro/converter/runtime_template_controls.py": {
        "RUNTIME_CONTROL_TEMPLATES": "runtime control template registry",
        "DEFAULT_BRIGHTNESS_RANGE": "runtime brightness range reuse",
        "DEFAULT_COLOR_TEMP_RANGE_KELVIN": "runtime color-temperature range reuse",
    },
    "custom_components/yeelight_pro/converter/runtime_template_sensors.py": {
        "RUNTIME_SENSOR_TEMPLATES": "runtime sensor template registry",
        "\"contact_sensor\"": "runtime contact sensor template coverage",
        "\"human_sensor\"": "runtime human sensor template coverage",
        "\"light_sensor\"": "runtime light sensor template coverage",
    },
    "custom_components/yeelight_pro/converter/runtime_template_hvac.py": {
        "RUNTIME_HVAC_TEMPLATES": "runtime HVAC template registry",
        "\"temp_control\"": "runtime temp-control template coverage",
    },
    "custom_components/yeelight_pro/capabilities/product_catalog.py": {
        "normalize_product_pid": "product pid normalization helper",
        "product_model_from_catalog": "product catalog canonical model builder",
        "product_hydration_properties": "product catalog hydration property list",
        "registry_property_model": "registry-backed catalog property builder",
    },
    "custom_components/yeelight_pro/capabilities/product_catalog_data.py": {
        "IOT_PRODUCT_SPECS": "embedded Yeelight product composition registry",
        "Yeelight Pro S21 智能墙壁开关-双键": (
            "documented S21 switch product row"
        ),
        "DALI网关": "documented DALI gateway product row",
    },
    "custom_components/yeelight_pro/converter/runtime_subdevices.py": {
        "infer_subdevice_components": "OpenAPI sub-device component builder",
        "_events_by_subdevice_index": "OpenAPI keyN event component scoping",
        "_component_id": "OpenAPI indexed component id builder",
        "openapi_property_model": "OpenAPI property metadata preservation",
    },
    "custom_components/yeelight_pro/core/device_registry_classification.py": {
        "registry_category_from_property_keys": "CSV registry-backed category classifier",
        "categories_for_property": "property-to-category registry index helper",
    },
    "custom_components/yeelight_pro/core/device_runtime_constants.py": {
        "TEMP_CONTROL_STRONG_PROPS": "runtime temp-control evidence constants",
        "LIGHT_SENSOR_CONFIG_PROPS": "runtime light-sensor config evidence constants",
    },
}
