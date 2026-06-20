"""Push payload flow diagnostics for Yeelight Pro."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def push_sync_status(
    manager_health_payload: Mapping[str, Any],
    transport_health: Mapping[str, Any] | None,
) -> str:
    """Return an aggregate push sync status for diagnostics triage."""
    if manager_health_payload.get("running") is False:
        return "not_running"
    if transport_health is None:
        return "transport_health_unavailable"
    if _has_control_frame_error(manager_health_payload, transport_health):
        return "control_frame_error"
    if (
        transport_health.get("running") is False
        or transport_health.get("websocket_open") is False
    ):
        return "not_connected"
    dispatched_payloads = int_diagnostic_value(
        transport_health.get("dispatched_payloads")
    )
    if dispatched_payloads <= 0:
        if _private_status_reason(transport_health) == "no_subscribable_devices":
            return "private_push_no_subscribable_devices"
        if _has_private_status_non_success(transport_health):
            return "private_status_non_success"
        if int_diagnostic_value(transport_health.get("unsupported_messages")) > 0:
            return "unsupported_payload_received"
        return "no_data_payload_received"
    handled_payloads = int_diagnostic_value(
        manager_health_payload.get("handled_payloads")
    )
    if handled_payloads <= 0:
        return "data_payload_not_handled"
    if recent_data_nodes_not_loaded(transport_health):
        return "data_payload_not_in_topology"
    if int_diagnostic_value(manager_health_payload.get("unknown_property_updates")) > 0:
        return "data_payload_not_in_topology"
    if manager_health_payload.get("last_payload_changed") is True:
        return "data_payload_applied"
    if int_diagnostic_value(manager_health_payload.get("property_updates")) <= 0:
        return "data_payload_no_property_updates"
    if int_diagnostic_value(manager_health_payload.get("routed_property_updates")) > 0:
        return "data_payload_routed_no_state_change"
    if int_diagnostic_value(manager_health_payload.get("empty_param_updates")) > 0:
        return "data_payload_empty_params"
    return "data_payload_no_state_change"


def _has_control_frame_error(
    manager_health_payload: Mapping[str, Any],
    transport_health: Mapping[str, Any],
) -> bool:
    """Return whether the current push failure came from a control frame."""
    if (
        manager_health_payload.get("last_error_type") != "PushControlFrameError"
        and transport_health.get("last_runtime_error_type") != "PushControlFrameError"
    ):
        return False
    return int_diagnostic_value(transport_health.get("control_frames")) > 0


def _has_private_status_non_success(transport_health: Mapping[str, Any]) -> bool:
    """Return whether private push reported a non-success status frame."""
    if transport_health.get("last_private_status_result") == "success":
        return False
    return transport_health.get("last_private_status_result") == (
        "non_success"
    ) or int_diagnostic_value(
        transport_health.get("private_status_non_success_frames")
    ) > 0


def _private_status_reason(transport_health: Mapping[str, Any]) -> str | None:
    """Return a fixed private status reason when the transport classified one."""
    reason = transport_health.get("last_private_status_reason")
    return reason if isinstance(reason, str) and reason else None


def push_payload_flow(
    manager_health_payload: Mapping[str, Any],
    transport_health: Mapping[str, Any] | None,
    *,
    sync_status: str,
    import_filter_active: bool,
) -> dict[str, Any]:
    """Return aggregate-only WebSocket payload routing diagnostics."""
    if transport_health is None:
        return {
            "status": sync_status,
            "transport_health_available": False,
            "import_filter_active": import_filter_active,
        }
    dispatched_payloads = int_diagnostic_value(
        transport_health.get("dispatched_payloads")
    )
    return {
        "status": sync_status,
        "transport_health_available": True,
        "websocket_open": transport_health.get("websocket_open") is True,
        "received_message_count": int_diagnostic_value(
            transport_health.get("received_messages")
        ),
        "decoded_json_message_count": int_diagnostic_value(
            transport_health.get("decoded_json_messages")
        ),
        "control_frame_count": int_diagnostic_value(
            transport_health.get("control_frames")
        ),
        "private_status_non_success_count": int_diagnostic_value(
            transport_health.get("private_status_non_success_frames")
        ),
        "private_status_reason": _private_status_reason(transport_health),
        "unsupported_payload_count": int_diagnostic_value(
            transport_health.get("unsupported_messages")
        ),
        "subscribe_sent": int_diagnostic_value(
            transport_health.get("subscribe_sent_count")
        )
        > 0,
        "subscribe_sent_count": int_diagnostic_value(
            transport_health.get("subscribe_sent_count")
        ),
        "subscribe_snapshot_device_count": optional_int_diagnostic_value(
            transport_health.get("last_subscribe_device_count")
        ),
        "subscribe_nodes_matching_loaded_topology": int_diagnostic_value(
            transport_health.get("last_subscribe_nodes_matching_loaded_topology")
        ),
        "subscribe_nodes_not_loaded": int_diagnostic_value(
            transport_health.get("last_subscribe_nodes_not_loaded")
        ),
        "subscribe_loaded_topology_count": int_diagnostic_value(
            transport_health.get("loaded_topology_node_hash_count")
        ),
        "subscribe_loaded_topology_coverage": subscribe_loaded_topology_coverage(
            transport_health
        ),
        "subscribe_topology_check": subscribe_topology_check(transport_health),
        "data_payload_received": dispatched_payloads > 0,
        "data_payload_count": dispatched_payloads,
        "handled_payload_count": int_diagnostic_value(
            manager_health_payload.get("handled_payloads")
        ),
        "property_update_count": int_diagnostic_value(
            manager_health_payload.get("property_updates")
        ),
        "last_payload_handle_duration_ms": optional_float_diagnostic_value(
            manager_health_payload.get("last_payload_handle_duration_ms")
        ),
        "last_listener_notification_count": int_diagnostic_value(
            manager_health_payload.get("last_listener_notification_count")
        ),
        "last_listener_context_count": int_diagnostic_value(
            manager_health_payload.get("last_listener_context_count")
        ),
        "last_data_nodes_matching_loaded_topology": int_diagnostic_value(
            transport_health.get("last_data_nodes_matching_loaded_topology")
        ),
        "last_data_nodes_not_loaded": int_diagnostic_value(
            transport_health.get("last_data_nodes_not_loaded")
        ),
        "recent_data_nodes_matching_loaded_topology": int_diagnostic_value(
            transport_health.get("recent_data_nodes_matching_loaded_topology")
        ),
        "recent_data_nodes_not_loaded": int_diagnostic_value(
            transport_health.get("recent_data_nodes_not_loaded")
        ),
        "data_topology_check": data_topology_check(transport_health),
        "data_import_filter_check": data_import_filter_check(
            manager_health_payload,
            transport_health,
            import_filter_active=import_filter_active,
        ),
        "import_filter_active": import_filter_active,
    }


def data_topology_check(transport_health: Mapping[str, Any]) -> str:
    """Return the aggregate topology conclusion for received data payloads."""
    dispatched_payloads = int_diagnostic_value(
        transport_health.get("dispatched_payloads")
    )
    if dispatched_payloads <= 0:
        return "not_applicable_no_data_payload"
    matching = int_diagnostic_value(
        transport_health.get("recent_data_nodes_matching_loaded_topology")
    )
    not_loaded = int_diagnostic_value(transport_health.get("recent_data_nodes_not_loaded"))
    if matching > 0 and not_loaded == 0:
        return "matched_loaded_topology"
    if matching == 0 and not_loaded > 0:
        return "not_in_loaded_topology"
    if matching > 0 and not_loaded > 0:
        return "partially_matched_loaded_topology"
    return "no_node_samples"


def subscribe_topology_check(transport_health: Mapping[str, Any]) -> str:
    """Return whether the subscribe snapshot covers the loaded topology."""
    subscribe_count = optional_int_diagnostic_value(
        transport_health.get("last_subscribe_device_count")
    )
    if subscribe_count is None:
        return "not_applicable_no_subscribe_snapshot"
    loaded_count = int_diagnostic_value(
        transport_health.get("loaded_topology_node_hash_count")
    )
    matching = int_diagnostic_value(
        transport_health.get("last_subscribe_nodes_matching_loaded_topology")
    )
    not_loaded = int_diagnostic_value(
        transport_health.get("last_subscribe_nodes_not_loaded")
    )
    if loaded_count <= 0:
        return "loaded_topology_unavailable"
    if matching <= 0:
        return "subscribe_snapshot_not_in_loaded_topology"
    if matching >= loaded_count and not_loaded == 0:
        return "subscribe_snapshot_covers_loaded_topology"
    return "subscribe_snapshot_partial_loaded_topology"


def subscribe_loaded_topology_coverage(
    transport_health: Mapping[str, Any],
) -> float | None:
    """Return the fraction of loaded topology covered by subscribe snapshot."""
    subscribe_count = optional_int_diagnostic_value(
        transport_health.get("last_subscribe_device_count")
    )
    if subscribe_count is None:
        return None
    loaded_count = int_diagnostic_value(
        transport_health.get("loaded_topology_node_hash_count")
    )
    if loaded_count <= 0:
        return None
    matching = int_diagnostic_value(
        transport_health.get("last_subscribe_nodes_matching_loaded_topology")
    )
    return round(min(matching, loaded_count) / loaded_count, 4)


def recent_data_nodes_not_loaded(transport_health: Mapping[str, Any]) -> bool:
    """Return whether the latest known data frame missed loaded topology."""
    not_loaded = int_diagnostic_value(transport_health.get("recent_data_nodes_not_loaded"))
    matching = int_diagnostic_value(
        transport_health.get("recent_data_nodes_matching_loaded_topology")
    )
    return not_loaded > 0 and matching == 0


def data_import_filter_check(
    manager_health_payload: Mapping[str, Any],
    transport_health: Mapping[str, Any],
    *,
    import_filter_active: bool,
) -> str:
    """Return whether received data misses may be related to import filtering."""
    dispatched_payloads = int_diagnostic_value(
        transport_health.get("dispatched_payloads")
    )
    if dispatched_payloads <= 0:
        return "not_applicable_no_data_payload"
    if not import_filter_active:
        return "filter_disabled"
    if (
        int_diagnostic_value(manager_health_payload.get("unknown_property_updates")) > 0
        or recent_data_nodes_not_loaded(transport_health)
    ):
        return "unknown_or_unloaded_nodes_may_be_filtered"
    return "no_filter_related_miss_detected"


def int_diagnostic_value(value: Any) -> int:
    """Return integer diagnostics counters without accepting bools."""
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def optional_int_diagnostic_value(value: Any) -> int | None:
    """Return an optional integer diagnostics value without accepting bools."""
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def optional_float_diagnostic_value(value: Any) -> float | None:
    """Return an optional numeric diagnostics value without accepting bools."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


__all__ = [
    "data_import_filter_check",
    "data_topology_check",
    "int_diagnostic_value",
    "optional_float_diagnostic_value",
    "optional_int_diagnostic_value",
    "push_payload_flow",
    "push_sync_status",
    "recent_data_nodes_not_loaded",
    "subscribe_loaded_topology_coverage",
    "subscribe_topology_check",
]
