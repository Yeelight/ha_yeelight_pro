"""Push release-preflight contract tokens."""

from __future__ import annotations

PUSH_CONTRACT_REQUIRED_FILES: dict[str, dict[str, str]] = {
    "push_contract.py": {
        "build_push_url": "WebSocket URL builder",
        "build_subscribe_message": "subscribe frame builder",
        "build_heartbeat_message": "heartbeat frame builder",
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
    },
    "push_transport.py": {
        "YeelightPushWebSocketTransport": "websocket runtime transport",
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
        "_json_payload_from_message": "incoming JSON object filter",
        "_cleanup_after_reader_exit": "reader failure cleanup boundary",
    },
    "push.py": {
        "safe_runtime_event_params": "push event privacy filter",
        "_add_safe_params": "push event safe params copier",
        "msgId": "documented push message id boundary",
    },
    "core/runtime_bridge.py": {
        "RuntimePayloadBridge": "shared runtime payload bridge",
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
        "test_push_transport_rejects_empty_token_before_connect": (
            "token validation before connect coverage"
        ),
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
    "tests/test_runtime_bridge.py": {
        "async_handle_lan_payload": "LAN coordinator bridge coverage",
        "gateway_post.prop": "LAN property update bridge coverage",
        "2-p": "indexed runtime state bridge coverage",
        "test_lan_runtime_update_rebuilds_scaled_canonical_state": (
            "schema-scaled runtime update rebuild coverage"
        ),
    },
    "tests/test_runtime_bridge_lan_events.py": {
        "gateway_post.event": "LAN event dispatch bridge coverage",
        "lan_event": "LAN fallback component inference coverage",
    },
}
