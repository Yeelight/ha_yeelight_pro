"""Push release-preflight contract tokens."""

from __future__ import annotations

from scripts.hacs_preflight_push_transport_data import (
    PUSH_TRANSPORT_CONTRACT_REQUIRED_FILES,
)

PUSH_CONTRACT_SPLIT_GUARD_FILES = (
    "tests/test_push_transport.py",
    "tests/test_push_websocket_contract.py",
    "tests/test_push_transport_failures.py",
    "tests/test_runtime_bridge_lan_events.py",
    "scripts/verify_push_websocket.py",
    "tests/test_verify_push_websocket.py",
)

PUSH_CONTRACT_REQUIRED_FILES: dict[str, dict[str, str]] = {
    **PUSH_TRANSPORT_CONTRACT_REQUIRED_FILES,
    "push_contract.py": {
        "build_push_url": "WebSocket URL builder",
        "_normalize_push_base_url": "WebSocket-only endpoint scheme guard",
        "build_subscribe_message": "subscribe frame builder",
        "build_heartbeat_message": "heartbeat frame builder",
        "PUSH_EVENT_NOTIFICATION_TRANSPORT": "WebSocket-only event transport constant",
        "PUSH_CONTROL_METHODS": "documented WebSocket control method set",
        "PUSH_DATA_TYPES": "documented WebSocket data type set",
        "PUSH_HEARTBEAT_INTERVAL_SECONDS": "documented heartbeat interval constant",
        "PUSH_HEARTBEAT_TIMEOUT_SECONDS": "documented heartbeat timeout constant",
        "heartbeat_is_stale": "heartbeat timeout helper",
        "PushMessageBuilder": "monotonic message id builder",
        "PushReconnectPolicy": "bounded reconnect policy helper",
    },
    "const.py": {
        "CLOUD_REGION_PUSH_BASE_URLS": "regional WebSocket push endpoint map",
        "push-sg.yeelight.com": "Singapore WebSocket push endpoint",
        "push-us.yeelight.com": "US WebSocket push endpoint",
        "push-de.yeelight.com": "EU WebSocket push endpoint",
        "CONF_PRIVATE_PUSH_DOMAIN": "private deployment independent push endpoint key",
    },
    "live_runtime.py": {
        "CLOUD_REGION_PUSH_BASE_URLS": "regional WebSocket push endpoint selection",
        "CONF_PRIVATE_PUSH_DOMAIN": "private deployment independent push endpoint selection",
    },
    "push_manager.py": {
        "PushTransport": "injected transport protocol",
        "PushManager": "no-network push lifecycle manager",
        "async_handle_push_payload": "coordinator-only payload bridge",
        "_transport_started": "transport cleanup retry state",
        "transport_health": "nested WebSocket transport health diagnostics",
        "last_error_type": "diagnostics-safe error aggregation",
        "last_runtime_error_type": "background WebSocket error aggregation",
        "_sync_transport_runtime_error": "transport runtime error health sync",
    },
    "tests/test_verify_push_websocket.py": {
        "test_validate_run_request_requires_explicit_confirm": (
            "production WebSocket confirm guard coverage"
        ),
        "test_validate_run_request_requires_token_env": (
            "production WebSocket token env guard coverage"
        ),
        "test_validate_run_request_rejects_unbounded_probe": (
            "production WebSocket bounded-run guard coverage"
        ),
        "test_summary_classifies_control_and_data_frames_without_payload_values": (
            "production WebSocket redacted summary coverage"
        ),
        "test_summary_classifies_methodless_result_ack_shapes_without_values": (
            "production WebSocket method-less result ACK coverage"
        ),
        "test_summary_classifies_methodless_result_error_shapes_without_values": (
            "production WebSocket method-less result error coverage"
        ),
        "test_probe_treats_bounded_idle_timeout_after_subscribe_as_ok": (
            "production WebSocket bounded idle success coverage"
        ),
        "test_main_does_not_probe_network_without_confirm": (
            "production WebSocket default no-network coverage"
        ),
        "test_script_path_execution_is_no_network_without_confirm": (
            "production WebSocket script-path no-network coverage"
        ),
        "test_probe_summarizes_heartbeat_cleanup_error_without_values": (
            "production WebSocket heartbeat cleanup redaction coverage"
        ),
    },
    "scripts/verify_push_websocket.py": {
        "confirm-production-websocket": "explicit production WebSocket confirm flag",
        "YEELIGHT_PRO_PUSH_TOKEN": "environment-only push token input",
        "validate_run_request": "production WebSocket fail-closed safety gate",
        "PushWebSocketProbeSummary": "diagnostics-safe probe summary",
        "last_error_type": "heartbeat cleanup aggregate error type",
        "async_probe_push_websocket": "explicit production WebSocket probe entrypoint",
        "PUSH_CONTRACT_PATH": "Home Assistant-free push contract load path",
        "_load_push_contract": "Home Assistant-free pure contract loader",
        "build_push_url": "documented push URL helper reuse",
        "PUSH_DATA_TYPES": "documented WebSocket data type reuse",
        "PUSH_CONTROL_METHODS": "documented WebSocket control method reuse",
        "PushMessageBuilder": "documented subscribe and heartbeat builder reuse",
        "PUSH_HEARTBEAT_INTERVAL_SECONDS": "documented heartbeat interval reuse",
        "control_error_frames": "production control-frame aggregate counter",
        "data_types": "production data payload aggregate counter",
        "json_shapes": "field-name-only JSON shape summary",
        "_is_result_control_payload": "method-less production ACK classifier",
        "_is_control_error_payload": "aggregate-only production result error classifier",
        "idle_timeouts": "bounded idle timeout aggregate counter",
    },
    "tests/test_verify_cloud_devices.py": {
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
        "test_probe_client_loader_is_homeassistant_free": (
            "production cloud devices HA-free loader coverage"
        ),
        "test_probe_client_loader_does_not_need_homeassistant_package": (
            "production cloud devices no-HA-package loader coverage"
        ),
    },
    "scripts/verify_cloud_devices.py": {
        "confirm-production-cloud-devices": (
            "explicit production cloud devices confirm flag"
        ),
        "YEELIGHT_PRO_CLOUD_ACCESS_TOKEN": (
            "environment-only cloud devices token input"
        ),
        "YEELIGHT_PRO_CLOUD_HOUSE_ID": (
            "environment-only cloud devices house input"
        ),
        "validate_run_request": "production cloud devices fail-closed safety gate",
        "CloudDevicesProbeSummary": (
            "diagnostics-safe cloud devices probe summary"
        ),
        "async_probe_cloud_devices": (
            "explicit production cloud devices probe entrypoint"
        ),
        "_load_yeelight_client": "Home Assistant-free client loader",
        "_load_probe_client": "shared HA-free production probe client",
        "_update_summary_from_devices": "aggregate-only device summary",
        "categories": "device-category aggregate counter",
    },
    "scripts/verify_probe_client.py": {
        "ProbeYeelightClient": "HA-free production probe client class",
        "load_yeelight_client": "HA-free production probe client loader",
        "request_json": "shared request_json helper reuse",
        "build_client_headers": "shared client header helper reuse",
        "house_devices_path": "shared cloud devices path helper reuse",
        "paginated_path": "shared paginated path helper reuse",
        "schema_cache": "schema-cache import regression guard token",
        "homeassistant": "Home Assistant import regression guard token",
    },
    "tests/test_push_payloads.py": {
        "test_push_property_updates_do_not_fold_message_meta_into_state": (
            "push prop metadata boundary coverage"
        ),
    },
    "tests/test_push_payload_events.py": {
        "test_push_event_payloads_redact_sensitive_event_params": (
            "push event privacy coverage"
        ),
        "secret-access-token": "push event token redaction coverage",
    },
    "tests/test_push_events.py": {
        "test_coordinator_deduplicates_replayed_push_event_message_id": (
            "push event replay dedupe coverage"
        ),
        "test_coordinator_dedupes_push_events_by_message_and_event_identity": (
            "push event dedupe identity coverage"
        ),
        "test_coordinator_does_not_dedupe_push_events_without_message_id": (
            "push event missing-message-id passthrough coverage"
        ),
    },
    "tests/test_runtime_bridge.py": {
        "async_handle_lan_payload": "LAN coordinator bridge coverage",
        "gateway_post.prop": "LAN property update bridge coverage",
        "2-p": "indexed runtime state bridge coverage",
        "test_runtime_event_dedupe_key_is_bounded_and_identifier_safe": (
            "runtime event dedupe key privacy coverage"
        ),
        "test_lan_runtime_update_rebuilds_scaled_canonical_state": (
            "schema-scaled runtime update rebuild coverage"
        ),
    },
    "tests/test_runtime_bridge_lan_events.py": {
        "gateway_post.event": "LAN event dispatch bridge coverage",
        "lan_event": "LAN fallback component inference coverage",
    },
}
