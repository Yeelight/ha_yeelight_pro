"""Release guard tokens for split client/control contract tests."""

from __future__ import annotations

SPLIT_CLIENT_CONTRACT_TEST_TOKENS = {
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
        "read_nodes_property_body": (
            "documented multi-node single-property body coverage"
        ),
        "read_nodes_properties_body": (
            "documented multi-node multi-property body coverage"
        ),
        "node_properties_read_path": "documented read properties path coverage",
        "node_property_read_path": "documented single-property read path coverage",
        "nodes_property_read_path": (
            "documented multi-node single-property path coverage"
        ),
        "nodes_properties_read_path": (
            "documented multi-node multi-property path coverage"
        ),
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
