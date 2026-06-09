"""Release guard tokens for split contract tests."""

from __future__ import annotations

SPLIT_CONTRACT_TEST_TOKENS = {
    "tests/test_capability_registry_contract.py": {
        "test_event_aliases_cover_backend_event_types": (
            "backend event alias contract coverage"
        ),
        "test_capability_registry_maps_core_categories_and_properties": (
            "core category/property registry coverage"
        ),
        "multi spin": "scene panel multi-spin alias coverage",
        "human enter": "human sensor enter event alias coverage",
        "power.alarm": "power alarm event alias coverage",
        "platform_for_category": "category-to-platform facade coverage",
        "property_capability": "core property capability lookup coverage",
    },
    "tests/test_options_flow_contract.py": {
        "test_options_flow_shows_defaults": "options default form coverage",
        "test_options_flow_confirms_runtime_only_options": (
            "runtime-only option confirmation coverage"
        ),
        "test_options_flow_confirms_reload_required_options": (
            "reload-required option confirmation coverage"
        ),
        "test_options_flow_manual_device_filter_requires_reload": (
            "manual device filter reload coverage"
        ),
        "test_coordinator_scan_interval_reads_entry_options": (
            "coordinator runtime scan interval coverage"
        ),
        "CONF_DEVICE_IMPORT_FILTER_INCLUDE_DEVICES": (
            "manual device filter id coverage"
        ),
        "get_enabled_platforms": "experimental platform default gate coverage",
        "test_enabled_platforms_hide_experimental_by_default": (
            "experimental platform default-off coverage"
        ),
        "EXPERIMENTAL_PLATFORMS": "experimental platform constant coverage",
    },
    "tests/test_translation_runtime_contract.py": {
        "test_translations_are_valid_and_key_aligned": (
            "translation leaf-key alignment coverage"
        ),
        "test_topology_repair_placeholders_match_translations": (
            "Repairs placeholder runtime coverage"
        ),
        "leaf_paths": "shared translation path helper reuse",
        "CONF_DEVICE_IMPORT_FILTER_INCLUDE_CATEGORIES": (
            "device filter include translation coverage"
        ),
        "refresh_product_schemas": "refresh service field translation coverage",
        "device_topology_changed": "topology Repair issue translation coverage",
    },
    "tests/config_flow_helpers.py": {
        "def config_flow": "shared config-flow fixture coverage",
        "prepare_cloud_flow": "shared cloud flow setup coverage",
    },
    "tests/conftest.py": {
        "config_flow_helpers": "shared config-flow fixture plugin registration",
    },
    "tests/test_config_flow.py": {
        "test_cloud_auth_method_schema_uses_localized_labels": (
            "config-flow auth method label coverage"
        ),
        "test_cloud_region_schema_uses_localized_region_selector": (
            "config-flow region selector coverage"
        ),
        "test_user_schema_uses_localized_connection_mode_selector": (
            "config-flow connection mode selector coverage"
        ),
        'translation_key"] == "cloud_auth_method"': (
            "cloud auth method selector translation-key coverage"
        ),
        'translation_key"] == "connection_mode"': (
            "connection mode selector translation-key coverage"
        ),
        'translation_key"] == "cloud_region"': (
            "cloud region selector translation-key coverage"
        ),
    },
    "tests/test_config_flow_cloud.py": {
        "test_cloud_region_selects_documented_multi_region_domain": (
            "multi-region cloud domain coverage"
        ),
        "test_cloud_auth_method_routes_to_scan_login": (
            "scan-login auth path coverage"
        ),
        "test_cloud_auth_method_routes_to_manual_token": (
            "manual token auth path coverage"
        ),
        "test_cloud_houses_maps_load_errors_to_form": (
            "cloud house load error mapping coverage"
        ),
        "test_cloud_houses_user_selection_opens_real_device_picker": (
            "cloud house to real device picker coverage"
        ),
        "test_cloud_devices_loads_real_devices_and_defaults_to_all": (
            "real cloud device picker API coverage"
        ),
        "test_cloud_devices_user_selection_creates_filtered_entry": (
            "real device picker import-filter persistence coverage"
        ),
        "test_create_entry_persists_open_api_client_id": (
            "Open API clientId persistence coverage"
        ),
    },
    "tests/test_config_flow_device_picker.py": {
        "test_device_choices_normalize_open_api_rows": (
            "device picker Open API row normalization coverage"
        ),
        "test_cloud_devices_schema_uses_multi_select_options": (
            "device picker multi-select schema coverage"
        ),
        "test_selected_device_filter_includes_only_selected_devices": (
            "device picker import filter coverage"
        ),
        "NO_DEVICE_SELECTED_SENTINEL": "device picker import-none sentinel coverage",
    },
    "config_flow_device_picker.py": {
        "async_load_device_choices": "cloud device picker API loader",
        "get_devices(house_id)": "cloud device picker uses house device list",
        "device_import_filter_for_selected_devices": (
            "cloud device picker filter builder"
        ),
        "SelectSelectorConfig": "Home Assistant native device multi-select",
        "CONF_DEVICE_IMPORT_FILTER_INCLUDE_DEVICES": (
            "device picker writes existing import filter option"
        ),
    },
    "tests/test_config_flow_oauth.py": {
        "test_cloud_scan_login_initial_step_creates_qrcode": (
            "scan-login qrcode creation coverage"
        ),
        'selector_type == "qr_code"': "native Home Assistant QR selector coverage",
        "CONF_SCAN_LOGIN_QRCODE": "scan-login QR selector field coverage",
        "test_cloud_scan_login_submit_starts_continuous_progress_poll": (
            "scan-login progress polling coverage"
        ),
        "test_cloud_scan_login_progress_done_loads_houses": (
            "scan-login LOGIN token flow coverage"
        ),
        "test_scan_login_poll_task_keeps_polling_until_login": (
            "continuous scan-login polling coverage"
        ),
        "test_cloud_auth_method_no_longer_routes_to_oauth_app": (
            "authorization-code UI downgrade coverage"
        ),
        "CONF_SCAN_LOGIN_REFRESH": "scan-login qrcode refresh form coverage",
    },
    "tests/test_config_flow_reauth.py": {
        "test_reauth_update_normalizes_entry_data_and_preserves_client_id": (
            "reauth entry normalization coverage"
        ),
        "test_config_flow_unknown_errors_log_only_exception_type": (
            "config-flow unknown error redaction coverage"
        ),
        "secret-token": "sensitive token log redaction marker",
    },
    "tests/p0_client_helpers.py": {
        "FakeSession": "shared HTTP client fake coverage",
        "FakeOAuthSession": "shared OAuth client fake coverage",
        "FakeScanLoginSession": "shared scan-login client fake coverage",
        "oauth_success_payload": "documented OAuth response fixture coverage",
        "scan_login_login_payload": "documented scan-login response fixture coverage",
    },
    "tests/test_client_helpers.py": {
        "roomId=678": "documented roomId query path coverage",
        "?roomId=room_1": "documented group roomId query path coverage",
        "/v1/example/2/50?roomId=678": "pagination-before-query path coverage",
        "read_properties_body": "documented read properties body coverage",
        "read_nodes_property_body": "documented multi-node single-property body coverage",
        "read_nodes_properties_body": "documented multi-node multi-property body coverage",
        "node_properties_read_path": "documented read properties path coverage",
        "node_property_read_path": "documented single-property read path coverage",
        "nodes_property_read_path": "documented multi-node single-property path coverage",
        "nodes_properties_read_path": "documented multi-node multi-property path coverage",
    },
    "tests/test_client_control_contracts.py": {
        "control_property_body": "documented single-property control body coverage",
        "control_properties_body": (
            "documented single-node multi-property control body coverage"
        ),
        "control_nodes_property_body": (
            "documented multi-node single-property control body coverage"
        ),
        "node_properties_control_path": (
            "documented single-node multi-property control path coverage"
        ),
        "node_property_control_path": (
            "documented single-property control path coverage"
        ),
        "nodes_property_control_path": (
            "documented multi-node single-property control path coverage"
        ),
        "test_client_control_property_methods_use_documented_contracts": (
            "documented property control client coverage"
        ),
        "control_node_properties": (
            "client single-node multi-property control entrypoint coverage"
        ),
        "/w/properties\",": "single-node multi-property write endpoint coverage",
        "/w/properties/l": "single-property write endpoint coverage",
        "\"params\"": "single-node multi-property body field coverage",
        "\"index\"": "documented optional index field coverage",
        "resIds": "multi-node control body field coverage",
        "delay": "documented optional delay field coverage",
        "category": "documented optional category field coverage",
    },
    "tests/test_client_pagination.py": {
        "test_client_get_houses_uses_documented_paginated_endpoint": (
            "documented house list pagination coverage"
        ),
        "/v1/open/node/house/r/list/1/200": (
            "documented house list endpoint coverage"
        ),
        "test_client_list_methods_use_paginated_endpoints": (
            "documented 3.1 list endpoint coverage"
        ),
        "/v1/open/node/house/12345/areas/r/list": (
            "documented area list endpoint coverage"
        ),
        "/v1/open/node/house/12345/rooms/r/list": (
            "documented room list endpoint coverage"
        ),
        "/v1/open/node/house/12345/scenes/r/list": (
            "documented scene list endpoint coverage"
        ),
        "test_client_room_scoped_lists_keep_query_after_pagination": (
            "room-scoped list pagination coverage"
        ),
        "test_client_get_house_snapshot_uses_documented_endpoint": (
            "documented house snapshot client request coverage"
        ),
        "/v1/open/node/house/12345/r/info": (
            "documented house snapshot endpoint coverage"
        ),
        "get_devices": "device roomId pagination coverage",
        "get_groups": "group roomId pagination coverage",
    },
    "tests/test_p0_client_contracts.py": {
        "test_client_keeps_open_api_methods_after_helper_split": (
            "client public method split stability coverage"
        ),
        "get_house_snapshot": "client snapshot method remains on public client",
        "execute_scene": "client scene execution entrypoint coverage",
        "/v1/open/control/house/12345/control/w/scenes/scene_1": (
            "documented scene execution endpoint coverage"
        ),
        "control_node_properties": (
            "client single-node multi-property control entrypoint coverage"
        ),
        "control_node_property": "client single-property control entrypoint coverage",
        "control_nodes_property": "client multi-node control entrypoint coverage",
        "test_client_read_node_properties_uses_documented_read_contract": (
            "documented read properties client coverage"
        ),
        "test_client_read_property_methods_use_documented_contracts": (
            "documented read property variants client coverage"
        ),
        "test_client_automation_action_methods_use_stable_paths": (
            "automation action client path coverage"
        ),
        "enable_automation": "automation enable client entrypoint coverage",
        "disable_automation": "automation disable client entrypoint coverage",
        "trigger_automation": "automation trigger client entrypoint coverage",
        "/r/properties": "read properties endpoint coverage",
        "propNames": "read properties body field coverage",
        "resIds": "multi-node read body field coverage",
        "/v1/automation/auto_1/trigger": "automation trigger path assertion",
    },
    "tests/test_p0_control_auth.py": {
        "test_client_request_preserves_auth_error_classification": (
            "client auth error classification coverage"
        ),
        "test_client_request_redacts_http_error_response_body": (
            "client HTTP error body redaction coverage"
        ),
        "test_command_wrapper_redacts_identifiers_and_nested_error_details": (
            "command wrapper redaction coverage"
        ),
        "test_command_wrapper_traceback_does_not_keep_sensitive_cause": (
            "command wrapper traceback redaction coverage"
        ),
        "test_validate_auth_preserves_authentication_errors": (
            "validate_auth auth propagation coverage"
        ),
        "TokenExpiredError": "token-expired classification coverage",
        "AuthenticationError": "forbidden auth classification coverage",
        "secret-token": "HTTP body redaction regression marker",
        "traceback.format_exception": "traceback redaction inspection coverage",
    },
    "tests/test_push_payloads.py": {
        "test_push_property_updates_normalize_open_platform_payload": (
            "push property payload normalization coverage"
        ),
        "test_push_event_payloads_normalize_open_platform_payload": (
            "push event payload normalization coverage"
        ),
        "test_infer_event_component_id_uses_unique_schema_event_match": (
            "schema event component inference coverage"
        ),
    },
    "tests/config_entry_lifecycle_helpers.py": {
        "make_config_entry": "shared config-entry fixture coverage",
        "make_setup_coordinator": "setup coordinator fixture coverage",
        "CONF_OAUTH_CLIENT_ID": "Open API client id runtime fixture coverage",
    },
    "tests/test_config_entry_unload.py": {
        "test_unload_entry": "config-entry unload cleanup coverage",
        "push_manager.async_stop.assert_awaited_once": (
            "push manager unload stop coverage"
        ),
        "test_unload_entry_keeps_runtime_when_platform_unload_fails": (
            "failed unload runtime preservation coverage"
        ),
        "push_manager.async_stop.assert_not_awaited": (
            "failed unload push manager preservation coverage"
        ),
        "test_remove_entry_cleans_local_topology_repair_issues": (
            "remove-entry Repairs cleanup coverage"
        ),
    },
}
