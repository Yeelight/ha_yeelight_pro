"""Diagnostics preflight data for Yeelight Pro."""

from __future__ import annotations

DIAGNOSTICS_ENABLED_CLIENT_CAPABILITIES = (
    "scan_login_contract",
    "scan_login_runtime",
    "push_message_adapter",
    "runtime_payload_bridge",
    "websocket_message_contract",
    "websocket_transport_runtime",
    "push_manager_contract",
    "push_connection",
    "websocket_subscription",
    "lan_discovery_parser",
    "lan_message_contract",
    "lan_payload_adapter",
    "local_gateway_control",
    "lan_control",
    "websocket_event_notifications",
)
DIAGNOSTICS_DISABLED_CLIENT_CAPABILITIES = (
    "mqtt_subscription",
)
DIAGNOSTICS_FORBIDDEN_CLIENT_CAPABILITIES = {
    "oauth_contract": "Yeelight cloud login is APP scan-login; remove OAuth contract flags",
    "oauth_token_runtime": "Yeelight cloud login is APP scan-login; remove OAuth runtime flags",
    "manual_oauth_authorization_code_exchange": (
        "authorization-code login path has been removed"
    ),
    "oauth_flow": "Home Assistant OAuth flow has been removed",
    "oauth_authorization_code_flow": "authorization-code login path has been removed",
    "refresh_token_contract": "refresh token is scan-login metadata, not a runtime capability",
    "refresh_token_runtime": "refresh token is scan-login metadata, not a runtime capability",
    "websocket_transport_skeleton": (
        "WebSocket transport must be represented as a tested runtime capability"
    ),
    "sse_subscription": (
        "Yeelight event notifications are WebSocket-only; do not add SSE capability"
    ),
    "eventsource_subscription": (
        "Yeelight event notifications are WebSocket-only; do not add EventSource capability"
    ),
    "server_sent_events": (
        "Yeelight event notifications are WebSocket-only; do not add Server-Sent Events capability"
    ),
}
DIAGNOSTICS_CONTRACT_TEST_TOKENS = {
    "tests/test_diagnostics_redaction.py": {
        "validate_iot_registry": "registry validation details stay aggregated",
        "topology_diff_summary": "topology diff diagnostics are allowlisted",
        "api.yeelight.com": "private endpoint leakage regression marker",
        "token-secret": "token leakage regression marker",
        "device_filter_form_keys": "device-filter form-only keys stay redacted",
        "room-secret-form": "device-filter form value leakage marker",
        "test_diagnostics_redacts_scan_login_device_identifier": (
            "scan-login device diagnostics redaction coverage"
        ),
        "ha-scan-device-secret": "scan-login device leakage regression marker",
    },
    "tests/test_diagnostics_filters.py": {
        "entity_import_filter_preview": "filter preview stays aggregate-only",
        "relay-secret": "device identifier leakage regression marker",
        "vacuum-secret": "excluded device leakage regression marker",
    },
    "tests/test_diagnostics_runtime.py": {
        "aggregate_runtime_secret_markers": "runtime diagnostics secret scan",
        "option_status": "runtime option status diagnostics are covered",
        "runtime_reload_required": "option reload status is explicit",
        "platforms_match_options": "platform/options drift status is explicit",
        "debug_mode_enabled": "debug mode option status is explicit",
        "scan_interval_seconds": "scan interval option status is explicit",
        "spec_runtime_inventory": "spec runtime inventory summary is covered",
        "entity_registry_reconcile": "registry reconciliation summary is covered",
        "entity_registry_cleanup_audit": "registry cleanup audit summary is covered",
    },
    "tests/diagnostics_runtime_helpers.py": {
        "build_aggregate_runtime_coordinator": (
            "aggregate runtime diagnostics fixture helper"
        ),
        "EntityRegistryReconcileSummary": (
            "registry reconciliation fixture summary helper"
        ),
        "EntityRegistryCleanupAudit": "registry cleanup audit fixture coverage",
        "component-secret-light": "runtime secret marker fixture coverage",
        "secret_device_action": "device action secret marker fixture coverage",
    },
    "tests/diagnostics_helpers.py": {
        "build_empty_diagnostics_coordinator": "empty diagnostics coordinator helper",
        "build_filter_preview_coordinator": "filter preview coordinator helper",
        "build_aggregate_runtime_coordinator": "aggregate coordinator facade helper",
        "diagnostics_runtime_helpers": "runtime fixture helper import",
    },
    "tests/test_diagnostics_inventory.py": {
        "test_spec_runtime_inventory_uses_spec_correction_access_rules": (
            "spec runtime inventory access normalization coverage"
        ),
        "spec_runtime_inventory_diagnostics": "spec runtime inventory helper coverage",
        "readable_properties": "spec runtime readable-property summary coverage",
        "writable_properties": "spec runtime writable-property summary coverage",
    },
    "tests/test_diagnostics_capabilities.py": {
        "client_capabilities": "client capability diagnostics are covered",
        "scan_login_contract": "scan-login no-network contract is explicit",
        "scan_login_runtime": "scan-login runtime helper is explicit",
        "push_message_adapter": "push payload adapter capability is explicit",
        "runtime_payload_bridge": "received payload bridge capability is explicit",
        "websocket_message_contract": "WebSocket message contract is explicit",
        "websocket_transport_runtime": "WebSocket transport runtime is explicit",
        "push_manager_contract": "push manager contract is explicit",
        "lan_discovery_parser": "LAN discovery parser capability is explicit",
        "lan_message_contract": "LAN message contract capability is explicit",
        "lan_payload_adapter": "LAN received payload adapter capability is explicit",
        "push_connection": "live push runtime capability is explicit",
        "websocket_subscription": "live WebSocket subscription capability is explicit",
        "websocket_event_notifications": (
            "WebSocket-only event-notification runtime is explicit"
        ),
        "local_gateway_control": "local gateway control capability is explicit",
        "lan_control": "live LAN control capability is explicit",
        "mqtt_subscription": "live MQTT subscription remains explicitly disabled",
    },
    "tests/test_diagnostic_options.py": {
        "option_status_diagnostics": "option status helper is directly covered",
        "test_option_status_normalizes_legacy_runtime_options": (
            "legacy runtime option normalization is covered"
        ),
        "runtime_reload_required": "reload status remains explicit",
        "platforms_match_options": "platform/options drift status remains explicit",
        "debug_mode_enabled": "debug mode option status remains explicit",
        "scan_interval_seconds": "scan interval option status remains explicit",
        "import_filter_active": "filter status remains aggregate-only",
    },
    "tests/test_diagnostic_summaries.py": {
        "entity_candidate_diagnostics": "entity candidate summaries are aggregate-only",
        "entity_import_filter_preview_diagnostics": "filter preview helper is covered",
        "device-secret": "raw device identifier leakage regression marker",
        "preview-automation-secret": (
            "filter preview topology identifier leakage regression marker"
        ),
    },
}
