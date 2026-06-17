"""Push transport release-preflight contract token data."""

from __future__ import annotations

PUSH_TRANSPORT_CONTRACT_REQUIRED_FILES: dict[str, dict[str, str]] = {
    "push_transport.py": {
        "YeelightPushWebSocketTransport": "websocket runtime transport",
        "PushTransportHealth": "aggregate WebSocket transport health diagnostics",
        "base_url": "private deployment push endpoint override",
        "last_start_error_type": "recoverable initial-connect error diagnostics",
        "last_runtime_error_type": "background WebSocket error diagnostics",
        "received_messages": "received frame count diagnostics",
        "decoded_json_messages": "decoded JSON frame count diagnostics",
        "dispatched_payloads": "coordinator-dispatched payload count diagnostics",
        "ignored_messages": "ignored frame count diagnostics",
        "malformed_messages": "malformed frame count diagnostics",
        "control_frames": "control frame count diagnostics",
        "heartbeat_sent_count": "heartbeat send count diagnostics",
        "PushWebSocketSession": "session protocol seam",
        "PushWebSocket": "websocket protocol seam",
        "ws_connect": "websocket connect boundary",
        "next_subscribe": "subscribe frame send boundary",
        "next_heartbeat": "heartbeat frame send boundary",
        "PushReconnectPolicy": "bounded reconnect policy runtime use",
        "_schedule_reconnect": "automatic reconnect scheduler",
        "_reconnect_until_connected": "automatic reconnect loop",
        "PUSH_HEARTBEAT_INTERVAL_SECONDS": "documented heartbeat interval use",
        "asyncio.create_task": "non-blocking reader task",
        "PushControlFrameError": "aggregate-only control frame error",
        "_cleanup_after_reader_exit": "reader failure cleanup boundary",
    },
    "push_transport_frames.py": {
        "PUSH_DATA_TYPES": "shared WebSocket data type contract use",
        "PUSH_CONTROL_METHODS": "shared WebSocket control method contract use",
        "json_payload_from_message": "incoming JSON object filter",
        "is_push_data_payload": "prop/event payload type filter",
        "raise_for_control_error_frame": "control frame error classifier",
        "is_result_control_payload": "method-less result control-frame classifier",
        "is_control_error_payload": "aggregate-only control result error classifier",
        "PushControlFrameError": "aggregate-only control frame error helper",
    },
    "push_transport_types.py": {
        "PushTransportHealth": "aggregate WebSocket transport health model",
        "PushWebSocketSession": "session protocol seam helper",
        "PushWebSocket": "websocket protocol seam helper",
        "PushTransportPayloadCallback": "payload callback type helper",
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
        "test_build_push_url_accepts_private_http_websocket_endpoint": (
            "private deployment ws endpoint coverage"
        ),
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
        "test_push_manager_exposes_transport_health_when_available": (
            "nested transport health diagnostics coverage"
        ),
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
        "received_messages": "transport received-count health coverage",
        "dispatched_payloads": "transport dispatch-count health coverage",
        "malformed_messages": "transport malformed-count health coverage",
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
    "tests/test_push_transport_reconnect.py": {
        "test_push_transport_uses_private_base_url_override": (
            "private deployment push endpoint transport coverage"
        ),
        "test_push_transport_passes_bounded_connect_timeout": (
            "bounded websocket connect timeout coverage"
        ),
        "test_push_transport_clears_recoverable_start_error_after_reconnect": (
            "recoverable start error clear coverage"
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
    "tests/test_live_runtime_endpoints.py": {
        "test_live_runtime_uses_private_deployment_push_endpoint": (
            "private deployment live push endpoint coverage"
        ),
        "test_live_runtime_uses_region_push_endpoint_for_cloud_entries": (
            "regional cloud push endpoint coverage"
        ),
        "test_live_runtime_falls_back_to_private_api_host_for_legacy_entries": (
            "legacy private entry push fallback coverage"
        ),
        "ws-dev.yeedev.com": "private push endpoint example coverage",
        "push-sg.yeelight.com": "Singapore push endpoint test coverage",
        "push-us.yeelight.com": "US push endpoint test coverage",
        "push-de.yeelight.com": "EU push endpoint test coverage",
        "ws-test.yeedev.com": "private test push endpoint override coverage",
    },
}
