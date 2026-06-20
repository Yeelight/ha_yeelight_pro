"""Shared fixtures for debug push service tests."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from unittest.mock import AsyncMock, MagicMock


def debug_push_coordinator(
    *,
    debug_mode: bool = True,
    summary: Mapping[str, Any] | None = None,
) -> MagicMock:
    """Return a coordinator double for debug push service tests."""
    coordinator = MagicMock()
    coordinator.debug_mode = debug_mode
    coordinator.async_handle_push_payload = AsyncMock(return_value=[])
    coordinator.last_push_property_summary.as_dict.return_value = dict(summary or {})
    return coordinator


def debug_push_health_manager() -> MagicMock:
    """Return a push manager double with safe aggregate health samples."""
    manager = MagicMock()
    manager.health.as_dict.return_value = _manager_health()
    manager.transport_health = _transport_health()
    return manager


def synthetic_push_summary() -> dict[str, Any]:
    """Return a representative push routing summary with unsafe raw fields."""
    return {
        "input_updates": 1,
        "empty_param_updates": 0,
        "applied_device_updates": 1,
        "unknown_device_updates": 0,
        "group_updates": 0,
        "topology_node_updates": 0,
        "routed_updates": 1,
        "changed": True,
        "applied_node_samples": [
            {
                "node_id_hash": "ddabe06356586fa8",
                "node_type": 2,
                "param_keys": ["p"],
                "matched_collections": ["devices", "data"],
                "raw_device_id": "12345",
            }
        ],
    }


def _manager_health() -> dict[str, Any]:
    """Return manager-level push health with unsafe raw fields."""
    return {
        "running": True,
        "handled_payloads": 1,
        "changed_payloads": 1,
        "unchanged_payloads": 0,
        "property_updates": 1,
        "empty_param_updates": 0,
        "applied_property_updates": 1,
        "unknown_property_updates": 0,
        "group_updates": 0,
        "topology_node_updates": 0,
        "routed_property_updates": 1,
        "last_property_update_count": 1,
        "last_dispatched_event_count": 0,
        "last_payload_changed": True,
        "last_payload_type": "prop",
        "last_error_type": None,
        "last_applied_node_samples": [
            {
                "node_id_hash": "ddabe06356586fa8",
                "node_type": 2,
                "param_keys": ["1-sp", "o"],
                "matched_collections": ["devices", "data"],
                "raw_device_id": "secret-raw-device-id",
            },
            {"node_id_hash": "secret-node-hash"},
        ],
    }


def _transport_health() -> dict[str, Any]:
    """Return transport-level push health with unsafe raw fields."""
    return {
        "running": True,
        "websocket_open": True,
        "connect_attempts": 1,
        "connected_count": 1,
        "disconnected_count": 0,
        "reconnect_attempts": 0,
        "received_messages": 2,
        "decoded_json_messages": 2,
        "dispatched_payloads": 1,
        "ignored_messages": 1,
        "unsupported_messages": 0,
        "malformed_messages": 0,
        "control_frames": 1,
        "private_status_frames": 1,
        "private_status_non_success_frames": 0,
        "last_private_status_reason": "no_subscribable_devices",
        "subscribe_sent_count": 1,
        "heartbeat_sent_count": 0,
        "reconnect_pending": False,
        "next_reconnect_delay": None,
        "last_start_error_type": None,
        "last_runtime_error_type": None,
        "last_handshake_status": None,
        "last_disconnect_reason": None,
        "last_subscribe_error_type": None,
        "last_close_code": None,
        "last_close_exception_type": None,
        "first_frame_received": True,
        "last_control_method": "subscribe",
        "last_private_status_result": "success",
        "last_subscribe_device_count": 1,
        "last_subscribe_state_device_count": 1,
        "last_payload_type": "prop",
        "last_ignored_reason": "control_frame",
        "last_ignored_payload_type": None,
        "loaded_topology_node_hash_count": 1,
        "last_subscribe_nodes_matching_loaded_topology": 1,
        "last_subscribe_nodes_not_loaded": 0,
        "last_data_nodes_matching_loaded_topology": 1,
        "last_data_nodes_not_loaded": 0,
        "recent_data_nodes_matching_loaded_topology": 1,
        "recent_data_nodes_not_loaded": 0,
        "last_data_node_hash_samples": ["secret-data-hash"],
        "last_unsupported_payload_shape": _unsupported_payload_shape(),
    }


def _unsupported_payload_shape() -> dict[str, Any]:
    """Return an unsupported payload shape containing unsafe raw fields."""
    return {
        "objects": [
            {
                "path": "root",
                "keys": ["token", "value"],
                "flags": {"type": False, "data": True},
            }
        ],
        "status": {
            "result_length": 13,
            "result_hash": "abc123statushash",
            "data_keys": ["message"],
            "raw_result": "secret-status",
        },
        "raw_value": "secret-value",
    }
