"""Local HA release tokens for guarded production probe scripts."""

from __future__ import annotations

LOCAL_HA_PRODUCTION_PROBE_TOKENS = {
    "scripts/hacs_preflight_local_ha_probes.py": {
        "LOCAL_HA_PRODUCTION_PROBE_TOKENS": "production probe token registry",
        "scripts/verify_push_websocket.py": (
            "production WebSocket probe script token guard"
        ),
        "tests/test_verify_push_websocket.py": (
            "production WebSocket probe test token guard"
        ),
        "scripts/verify_scan_login.py": (
            "production scan-login probe script token guard"
        ),
        "tests/test_verify_scan_login.py": (
            "production scan-login probe test token guard"
        ),
        "scripts/verify_cloud_devices.py": (
            "production cloud devices probe script token guard"
        ),
        "tests/test_verify_cloud_devices.py": (
            "production cloud devices probe test token guard"
        ),
        "scripts/verify_lan_gateway.py": (
            "production LAN gateway probe script token guard"
        ),
        "tests/test_verify_lan_gateway.py": (
            "production LAN gateway probe test token guard"
        ),
        "scripts/verify_analytics.py": (
            "production analytics probe script token guard"
        ),
        "scripts/verify_analytics_support.py": (
            "production analytics probe helper token guard"
        ),
        "tests/test_verify_analytics.py": (
            "production analytics probe test token guard"
        ),
    },
    "scripts/verify_push_websocket.py": {
        "confirm-production-websocket": "production WebSocket confirm flag",
        "YEELIGHT_PRO_PUSH_TOKEN": "production WebSocket token env guard",
        "validate_run_request": "production WebSocket fail-closed guard",
        "PushWebSocketProbeSummary": "production WebSocket safe summary",
        "async_probe_push_websocket": "explicit production WebSocket entrypoint",
        "PUSH_CONTRACT_PATH": "production WebSocket HA-free contract path",
        "_load_push_contract": "production WebSocket HA-free contract loader",
        "json_shapes": "production WebSocket field-shape summary",
    },
    "scripts/verify_scan_login.py": {
        "confirm-production-scan-login": "production scan-login confirm flag",
        "YEELIGHT_PRO_SCAN_LOGIN_DEVICE": "production scan-login device env guard",
        "validate_run_request": "production scan-login fail-closed guard",
        "ScanLoginProbeSummary": "production scan-login safe summary",
        "async_probe_scan_login": "explicit production scan-login entrypoint",
        "SCAN_LOGIN_CONTRACT_PATH": "production scan-login HA-free contract path",
        "_load_scan_login_contract": (
            "production scan-login HA-free contract loader"
        ),
    },
    "scripts/verify_cloud_devices.py": {
        "confirm-production-cloud-devices": "production cloud devices confirm flag",
        "YEELIGHT_PRO_CLOUD_ACCESS_TOKEN": (
            "production cloud devices token env guard"
        ),
        "YEELIGHT_PRO_CLOUD_HOUSE_ID": (
            "production cloud devices house env guard"
        ),
        "validate_run_request": "production cloud devices fail-closed guard",
        "CloudDevicesProbeSummary": "production cloud devices safe summary",
        "async_probe_cloud_devices": "explicit production cloud devices entrypoint",
        "_load_yeelight_client": "production cloud devices client loader",
        "_update_summary_from_devices": (
            "production cloud devices aggregate-only summary"
        ),
        "categories": "production cloud devices category-count summary",
    },
    "scripts/verify_lan_gateway.py": {
        "confirm-production-lan-gateway": "production LAN gateway confirm flag",
        "YEELIGHT_PRO_LAN_GATEWAY_HOST": "production LAN gateway host env guard",
        "YEELIGHT_PRO_LAN_GATEWAY_PORT": "production LAN gateway port env guard",
        "validate_run_request": "production LAN gateway fail-closed guard",
        "LanGatewayProbeSummary": "production LAN gateway safe summary",
        "async_probe_lan_gateway": "explicit production LAN gateway entrypoint",
        "gateway_get.topology": "production LAN gateway topology probe frame",
        "_update_summary_from_payload": (
            "production LAN gateway aggregate-only summary"
        ),
        "methods": "production LAN gateway method-count summary",
    },
    "scripts/verify_analytics.py": {
        "confirm-production-analytics": "production analytics confirm flag",
        "YEELIGHT_PRO_ANALYTICS_ACCESS_TOKEN": (
            "production analytics token env guard"
        ),
        "YEELIGHT_PRO_ANALYTICS_HOUSE_ID": (
            "production analytics house env guard"
        ),
        "validate_run_request": "production analytics fail-closed guard",
        "async_probe_analytics": "explicit production analytics entrypoint",
    },
    "scripts/verify_analytics_support.py": {
        "AnalyticsProbeSummary": "production analytics safe summary",
        "update_summary_from_payload": (
            "production analytics aggregate-only summary"
        ),
        "object_shapes": "production analytics field-shape summary",
        "numeric_fields": "production analytics numeric-field summary",
        "load_yeelight_client": "production analytics client loader",
    },
    "custom_components/yeelight_pro/tests/test_verify_scan_login.py": {
        "test_validate_run_request_requires_explicit_confirm": (
            "production scan-login confirm guard coverage"
        ),
        "test_validate_run_request_requires_device_env": (
            "production scan-login device env guard coverage"
        ),
        "test_validate_run_request_rejects_invalid_region_and_unbounded_probe": (
            "production scan-login bounded-run guard coverage"
        ),
        "test_summary_redacts_qr_device_token_and_user_values": (
            "production scan-login redacted summary coverage"
        ),
        "test_main_does_not_probe_network_without_confirm": (
            "production scan-login default no-network coverage"
        ),
        "test_script_path_execution_is_no_network_without_confirm": (
            "production scan-login script-path no-network coverage"
        ),
        "test_probe_summarizes_created_scanned_login_without_values": (
            "production scan-login fake-login aggregate coverage"
        ),
    },
    "custom_components/yeelight_pro/tests/test_verify_cloud_devices.py": {
        "test_validate_run_request_requires_explicit_confirm": (
            "production cloud devices confirm guard coverage"
        ),
        "test_validate_run_request_requires_token_env": (
            "production cloud devices token env guard coverage"
        ),
        "test_validate_run_request_requires_house_id_env": (
            "production cloud devices house env guard coverage"
        ),
        "test_validate_run_request_rejects_invalid_region_and_unbounded_probe": (
            "production cloud devices bounded-run guard coverage"
        ),
        "test_summary_counts_devices_without_identifier_values": (
            "production cloud devices redacted summary coverage"
        ),
        "test_main_does_not_probe_network_without_confirm": (
            "production cloud devices default no-network coverage"
        ),
        "test_script_path_execution_is_no_network_without_confirm": (
            "production cloud devices script-path no-network coverage"
        ),
        "test_probe_summarizes_devices_without_values": (
            "production cloud devices fake-device aggregate coverage"
        ),
    },
    "custom_components/yeelight_pro/tests/test_verify_lan_gateway.py": {
        "test_validate_run_request_requires_explicit_confirm": (
            "production LAN gateway confirm guard coverage"
        ),
        "test_validate_run_request_requires_host_env": (
            "production LAN gateway host env guard coverage"
        ),
        "test_validate_run_request_rejects_invalid_port_timeout_and_frame_limit": (
            "production LAN gateway bounded-run guard coverage"
        ),
        "test_summary_classifies_lan_frames_without_payload_values": (
            "production LAN gateway redacted summary coverage"
        ),
        "test_main_does_not_probe_network_without_confirm": (
            "production LAN gateway default no-network coverage"
        ),
        "test_script_path_execution_is_no_network_without_confirm": (
            "production LAN gateway script-path no-network coverage"
        ),
        "test_probe_summarizes_lan_frames_without_values": (
            "production LAN gateway fake-frame aggregate coverage"
        ),
    },
    "custom_components/yeelight_pro/tests/test_verify_analytics.py": {
        "test_validate_run_request_requires_explicit_confirm": (
            "production analytics confirm guard coverage"
        ),
        "test_validate_run_request_requires_token_and_house_env": (
            "production analytics env guard coverage"
        ),
        "YEELIGHT_PRO_ANALYTICS_AREA_ID": (
            "production analytics optional area env guard coverage"
        ),
        "test_validate_run_request_rejects_invalid_region_endpoint_and_timeout": (
            "production analytics bounded-request guard coverage"
        ),
        "test_summary_describes_payload_shape_without_raw_values": (
            "production analytics raw payload redaction coverage"
        ),
        "test_main_does_not_probe_network_without_confirm": (
            "production analytics default no-network coverage"
        ),
        "test_script_path_execution_is_no_network_without_confirm": (
            "production analytics script-path no-network coverage"
        ),
        "test_probe_summarizes_analytics_payload_without_values": (
            "production analytics fake-payload aggregate coverage"
        ),
    },
}
