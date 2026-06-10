"""Push release-preflight contract tokens."""

from __future__ import annotations

PUSH_CONTRACT_REQUIRED_FILES: dict[str, dict[str, str]] = {
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
    "push_manager.py": {
        "PushTransport": "injected transport protocol",
        "PushManager": "no-network push lifecycle manager",
        "async_handle_push_payload": "coordinator-only payload bridge",
        "_transport_started": "transport cleanup retry state",
        "last_error_type": "diagnostics-safe error aggregation",
        "last_runtime_error_type": "background WebSocket error aggregation",
        "_sync_transport_runtime_error": "transport runtime error health sync",
    },
    "push_transport.py": {
        "YeelightPushWebSocketTransport": "websocket runtime transport",
        "last_start_error_type": "recoverable initial-connect error diagnostics",
        "last_runtime_error_type": "background WebSocket error diagnostics",
        "PushWebSocketSession": "session protocol seam",
        "PushWebSocket": "websocket protocol seam",
        "ws_connect": "websocket connect boundary",
        "next_subscribe": "subscribe frame send boundary",
        "next_heartbeat": "heartbeat frame send boundary",
        "PushReconnectPolicy": "bounded reconnect policy runtime use",
        "_schedule_reconnect": "automatic reconnect scheduler",
        "_reconnect_until_connected": "automatic reconnect loop",
        "PUSH_HEARTBEAT_INTERVAL_SECONDS": "documented heartbeat interval use",
        "PUSH_DATA_TYPES": "shared WebSocket data type contract use",
        "PUSH_CONTROL_METHODS": "shared WebSocket control method contract use",
        "asyncio.create_task": "non-blocking reader task",
        "_json_payload_from_message": "incoming JSON object filter",
        "_is_push_data_payload": "prop/event payload type filter",
        "_raise_for_control_error_frame": "control frame error classifier",
        "_is_result_control_payload": "method-less result control-frame classifier",
        "_is_control_error_payload": "aggregate-only control result error classifier",
        "PushControlFrameError": "aggregate-only control frame error",
        "_cleanup_after_reader_exit": "reader failure cleanup boundary",
    },
    "push.py": {
        "safe_runtime_event_params": "push event privacy filter",
        "_add_safe_params": "push event safe params copier",
        "msgId": "documented push message id boundary",
    },
    "core/runtime_bridge.py": {
        "RuntimePayloadBridge": "shared runtime payload bridge",
        "RuntimeEventDeduper": "bounded WebSocket event dedupe guard",
        "runtime_event_dedupe_key": "privacy-safe event dedupe key",
        "MAX_RUNTIME_EVENT_DEDUPE_KEYS": "bounded event dedupe storage",
        "apply_property_updates": "runtime property merge path",
        "dispatch_event_payloads": "runtime event dispatch path",
        "infer_event_component_id": "schema event component inference",
        "property_updates_from_adapter": "adapter update conversion",
    },
    "tests/test_push_contract.py": {
        "Bearer fake-token": "Bearer prefix regression coverage",
        "build_subscribe_message": "subscribe frame coverage",
        "build_heartbeat_message": "heartbeat frame coverage",
        "test_push_heartbeat_timing_constants_match_open_platform_contract": (
            "heartbeat timing contract coverage"
        ),
        "test_heartbeat_is_stale_uses_documented_timeout": (
            "heartbeat stale helper coverage"
        ),
        "PushMessageBuilder": "message id increment coverage",
        "test_build_push_url_rejects_non_websocket_event_endpoints": (
            "WebSocket-only endpoint rejection coverage"
        ),
        "test_push_reconnect_policy_is_bounded_by_documented_timeout": (
            "reconnect policy timing coverage"
        ),
        "test_push_reconnect_policy_next_delay_is_pure_and_bounded": (
            "reconnect policy pure helper coverage"
        ),
        "test_push_reconnect_policy_rejects_invalid_values": (
            "reconnect policy validation coverage"
        ),
    },
    "tests/test_push_manager.py": {
        "FakeTransport": "injected transport test double",
        "async_handle_push_payload": "coordinator bridge coverage",
        "test_push_manager_preserves_recoverable_start_error_type": (
            "recoverable transport start error health coverage"
        ),
        "test_push_manager_reports_transport_runtime_error_type": (
            "background transport runtime error health coverage"
        ),
        "test_push_manager_accepts_payload_emitted_during_transport_start": (
            "start-time payload dispatch coverage"
        ),
        "test_push_manager_preserves_start_time_payload_error_type": (
            "start-time payload error coverage"
        ),
        "test_push_manager_stop_failure_blocks_payloads_and_allows_retry": (
            "stop failure retry coverage"
        ),
        "ignores_payload_after_stop": "stopped manager guard coverage",
        "last_error_type": "safe health aggregation coverage",
    },
    "tests/push_transport_helpers.py": {
        "FakeMessage": "aiohttp message test double coverage",
        "FakeSession": "injected websocket session coverage",
        "FakeWebSocket": "finite websocket stream coverage",
        "OpenFakeWebSocket": "open websocket stream coverage",
        "FailingSubscribeWebSocket": "subscribe failure test double coverage",
        "FailingCloseWebSocket": "stop failure retry test double coverage",
        "FailingHeartbeatWebSocket": "heartbeat failure test double coverage",
        "FailingReaderWebSocket": "reader failure test double coverage",
        "ControlledSleep": "controllable heartbeat sleep coverage",
        "wait_for_sleep_calls": "heartbeat sleep coordination coverage",
    },
    "tests/test_push_transport.py": {
        "push_transport_helpers": "shared transport helper import coverage",
        "test_push_transport_connects_subscribes_and_dispatches_json_objects": (
            "connect subscribe dispatch coverage"
        ),
        "test_push_transport_sends_heartbeat_until_stopped": (
            "heartbeat loop cancellation coverage"
        ),
        "test_push_transport_stop_closes_opened_websocket_once": (
            "transport stop cleanup coverage"
        ),
        "test_push_transport_start_is_idempotent_while_open": (
            "transport start idempotency coverage"
        ),
        "test_push_transport_reconnects_after_reader_finishes": (
            "transport reconnect after reader-end coverage"
        ),
        "test_push_transport_reconnect_backoff_retries_until_success": (
            "transport reconnect retry backoff coverage"
        ),
        "test_push_transport_initial_connect_failure_schedules_reconnect": (
            "initial connect failure reconnect coverage"
        ),
        "test_push_transport_rejects_empty_token_before_connect": (
            "token validation before connect coverage"
        ),
        "test_push_transport_ignores_control_ack_frames": (
            "control ACK and method-less result frame ignore coverage"
        ),
        '"data":{"deviceId":"device-secret"}': (
            "method-less production ACK redaction fixture"
        ),
    },
    "tests/test_push_websocket_contract.py": {
        "test_yeelight_event_notifications_use_websocket_url_contract": (
            "WebSocket-only event notification URL coverage"
        ),
        "PUSH_EVENT_NOTIFICATION_TRANSPORT": (
            "WebSocket-only event notification transport constant coverage"
        ),
        "PUSH_DATA_TYPES": "WebSocket-only data-type set coverage",
        "test_yeelight_websocket_subscribe_and_heartbeat_frames_match_docs": (
            "documented WebSocket subscribe heartbeat coverage"
        ),
        "test_websocket_transport_dispatches_only_documented_data_frames": (
            "WebSocket-only prop event dispatch coverage"
        ),
        "test_websocket_transport_does_not_dispatch_polling_or_sse_events": (
            "WebSocket-only event notification rejects non-WebSocket fallback frames"
        ),
        "eventsource": "negative EventSource data-frame coverage",
        '"sse"': "negative SSE data-frame coverage",
    },
    "tests/test_push_transport_failures.py": {
        "push_transport_helpers": "shared transport failure helper import coverage",
        "test_push_transport_closes_websocket_when_subscribe_fails": (
            "subscribe failure cleanup coverage"
        ),
        "test_push_transport_stop_failure_keeps_websocket_for_retry": (
            "transport stop retry cleanup coverage"
        ),
        "test_push_transport_heartbeat_failure_closes_websocket": (
            "heartbeat failure cleanup coverage"
        ),
        "test_push_transport_reader_failure_closes_websocket": (
            "reader failure cleanup coverage"
        ),
        "test_push_transport_callback_failure_closes_websocket": (
            "callback failure cleanup coverage"
        ),
        "test_push_transport_control_error_frame_closes_websocket": (
            "control error frame cleanup coverage"
        ),
        "test_push_transport_methodless_result_error_closes_websocket": (
            "method-less result error cleanup coverage"
        ),
    },
    "tests/test_live_runtime.py": {
        "test_live_runtime_routes_only_websocket_prop_and_event_to_coordinator": (
            "live WebSocket end-to-end coordinator dispatch coverage"
        ),
        '"server_sent"': "live runtime negative Server-Sent pseudo-frame coverage",
        '"sse"': "live runtime negative SSE pseudo-frame coverage",
        "FakeWebSocket": "live runtime injected WebSocket source coverage",
        "YeelightProCoordinator": "live runtime real coordinator coverage",
        "DEVICE_EVENT_TYPE": "live runtime HA bus event coverage",
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
