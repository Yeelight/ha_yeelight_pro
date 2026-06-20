"""Shared push diagnostics test doubles."""
from __future__ import annotations


def _push_health(**overrides: object) -> dict[str, object]:
    """Return default push health diagnostics with optional overrides."""
    push_sync_status = str(overrides.get("push_sync_status", "not_running"))
    data: dict[str, object] = {
        "running": False,
        "started_count": 0,
        "stopped_count": 0,
        "handled_payloads": 0,
        "changed_payloads": 0,
        "unchanged_payloads": 0,
        "property_updates": 0,
        "empty_param_updates": 0,
        "applied_property_updates": 0,
        "unknown_property_updates": 0,
        "group_updates": 0,
        "topology_node_updates": 0,
        "routed_property_updates": 0,
        "last_applied_node_samples": [],
        "last_unknown_node_samples": [],
        "recent_applied_node_samples": [],
        "recent_unknown_node_samples": [],
        "dispatched_events": 0,
        "last_property_update_count": 0,
        "last_applied_property_update_count": 0,
        "last_unknown_property_update_count": 0,
        "last_group_update_count": 0,
        "last_topology_node_update_count": 0,
        "last_routed_property_update_count": 0,
        "last_dispatched_event_count": 0,
        "last_payload_changed": False,
        "last_payload_handle_duration_ms": None,
        "last_listener_notification_count": 0,
        "last_listener_context_count": 0,
        "last_payload_type": None,
        "last_payload_at": None,
        "last_error_type": None,
        "push_sync_status": push_sync_status,
        "payload_flow": _payload_flow(
            status=push_sync_status,
            transport_health_available=False,
        ),
    }
    data.update(overrides)
    return data

def _payload_flow(
    *,
    status: str,
    transport_health_available: bool = True,
    websocket_open: bool = True,
    received_message_count: int = 2,
    decoded_json_message_count: int = 2,
    control_frame_count: int = 1,
    private_status_non_success_count: int = 0,
    private_status_reason: str | None = None,
    unsupported_payload_count: int = 0,
    subscribe_sent: bool = True,
    subscribe_sent_count: int = 1,
    subscribe_snapshot_device_count: int | None = 0,
    subscribe_nodes_matching_loaded_topology: int = 0,
    subscribe_nodes_not_loaded: int = 0,
    subscribe_loaded_topology_count: int = 9,
    subscribe_loaded_topology_coverage: float | None = 0.0,
    subscribe_topology_check: str = "subscribe_snapshot_not_in_loaded_topology",
    data_payload_received: bool = False,
    data_payload_count: int = 0,
    handled_payload_count: int = 0,
    property_update_count: int = 0,
    last_payload_handle_duration_ms: float | None = None,
    last_listener_notification_count: int = 0,
    last_listener_context_count: int = 0,
    last_data_nodes_matching_loaded_topology: int = 0,
    last_data_nodes_not_loaded: int = 0,
    recent_data_nodes_matching_loaded_topology: int = 0,
    recent_data_nodes_not_loaded: int = 0,
    data_topology_check: str = "not_applicable_no_data_payload",
    data_import_filter_check: str = "not_applicable_no_data_payload",
    import_filter_active: bool = False,
) -> dict[str, object]:
    """Return the expected aggregate push payload-flow diagnostics."""
    if not transport_health_available:
        return {
            "status": status,
            "transport_health_available": False,
            "import_filter_active": import_filter_active,
        }
    return {
        "status": status,
        "transport_health_available": True,
        "websocket_open": websocket_open,
        "received_message_count": received_message_count,
        "decoded_json_message_count": decoded_json_message_count,
        "control_frame_count": control_frame_count,
        "private_status_non_success_count": private_status_non_success_count,
        "private_status_reason": private_status_reason,
        "unsupported_payload_count": unsupported_payload_count,
        "subscribe_sent": subscribe_sent,
        "subscribe_sent_count": subscribe_sent_count,
        "subscribe_snapshot_device_count": subscribe_snapshot_device_count,
        "subscribe_nodes_matching_loaded_topology": (
            subscribe_nodes_matching_loaded_topology
        ),
        "subscribe_nodes_not_loaded": subscribe_nodes_not_loaded,
        "subscribe_loaded_topology_count": subscribe_loaded_topology_count,
        "subscribe_loaded_topology_coverage": subscribe_loaded_topology_coverage,
        "subscribe_topology_check": subscribe_topology_check,
        "data_payload_received": data_payload_received,
        "data_payload_count": data_payload_count,
        "handled_payload_count": handled_payload_count,
        "property_update_count": property_update_count,
        "last_payload_handle_duration_ms": last_payload_handle_duration_ms,
        "last_listener_notification_count": last_listener_notification_count,
        "last_listener_context_count": last_listener_context_count,
        "last_data_nodes_matching_loaded_topology": (
            last_data_nodes_matching_loaded_topology
        ),
        "last_data_nodes_not_loaded": last_data_nodes_not_loaded,
        "recent_data_nodes_matching_loaded_topology": (
            recent_data_nodes_matching_loaded_topology
        ),
        "recent_data_nodes_not_loaded": recent_data_nodes_not_loaded,
        "data_topology_check": data_topology_check,
        "data_import_filter_check": data_import_filter_check,
        "import_filter_active": import_filter_active,
    }

class _TransportHealth:
    """Transport health double used by diagnostics tests."""

    def __init__(
        self,
        *,
        websocket_open: bool = True,
        dispatched_payloads: int | None = None,
        unsupported_messages: int = 0,
        received_messages: int | None = None,
        decoded_json_messages: int | None = None,
        recent_data_nodes_matching_loaded_topology: int | None = None,
        recent_data_nodes_not_loaded: int | None = None,
        data_node_hash: str = "41cf3c54b6edb00d",
        last_runtime_error_type: str | None = None,
        control_frames: int | None = None,
        subscribe_device_count: int | None = None,
        subscribe_state_device_count: int | None = None,
        subscribe_node_hashes: list[str] | None = None,
        subscribe_node_candidate_hashes: list[list[str]] | None = None,
        private_status_non_success_frames: int = 0,
        private_status_reason: str | None = None,
    ) -> None:
        """Initialize aggregate transport health state."""
        self._websocket_open = websocket_open
        self._dispatched_payloads = dispatched_payloads
        self._unsupported_messages = unsupported_messages
        self._received_messages = received_messages
        self._decoded_json_messages = decoded_json_messages
        self._recent_data_nodes_matching_loaded_topology = (
            recent_data_nodes_matching_loaded_topology
        )
        self._recent_data_nodes_not_loaded = recent_data_nodes_not_loaded
        self._data_node_hash = data_node_hash
        self._last_runtime_error_type = last_runtime_error_type
        self._control_frames = control_frames
        self._subscribe_device_count = subscribe_device_count
        self._subscribe_state_device_count = subscribe_state_device_count
        self._subscribe_node_hashes = subscribe_node_hashes or []
        self._subscribe_node_candidate_hashes = subscribe_node_candidate_hashes or []
        self._private_status_non_success_frames = private_status_non_success_frames
        self._private_status_reason = private_status_reason

    def as_dict(self) -> dict[str, object]:
        """Return aggregate-only transport diagnostics."""
        dispatched_payloads = (
            self._dispatched_payloads
            if self._dispatched_payloads is not None
            else 0
        )
        recent_matches = (
            self._recent_data_nodes_matching_loaded_topology
            if self._recent_data_nodes_matching_loaded_topology is not None
            else int(dispatched_payloads > 0 and self._websocket_open)
        )
        recent_not_loaded = (
            self._recent_data_nodes_not_loaded
            if self._recent_data_nodes_not_loaded is not None
            else 0
        )
        has_data_payload = self._websocket_open and dispatched_payloads > 0
        received_messages = (
            self._received_messages
            if self._received_messages is not None
            else 2 if self._websocket_open else 0
        )
        decoded_json_messages = (
            self._decoded_json_messages
            if self._decoded_json_messages is not None
            else 2 if self._websocket_open else 0
        )
        subscribe_device_count = (
            self._subscribe_device_count
            if self._subscribe_device_count is not None
            else 0 if self._websocket_open else None
        )
        subscribe_state_device_count = (
            self._subscribe_state_device_count
            if self._subscribe_state_device_count is not None
            else 0 if self._websocket_open else None
        )
        return {
            "running": True,
            "websocket_open": self._websocket_open,
            "connect_attempts": 1,
            "connected_count": int(self._websocket_open),
            "disconnected_count": int(not self._websocket_open),
            "reconnect_attempts": 0,
            "received_messages": received_messages,
            "decoded_json_messages": decoded_json_messages,
            "dispatched_payloads": dispatched_payloads,
            "ignored_messages": 1 if self._websocket_open else 0,
            "unsupported_messages": self._unsupported_messages,
            "malformed_messages": 0,
            "control_frames": (
                self._control_frames
                if self._control_frames is not None
                else 1 if self._websocket_open else 0
            ),
            "private_status_frames": int(
                self._private_status_non_success_frames > 0
            ),
            "private_status_non_success_frames": (
                self._private_status_non_success_frames
            ),
            "subscribe_sent_count": 1 if self._websocket_open else 0,
            "heartbeat_sent_count": 0,
            "pre_first_frame_abnormal_close_count": 0,
            "consecutive_pre_first_frame_abnormal_close_count": 0,
            "reconnect_pending": False,
            "next_reconnect_delay": None,
            "last_start_error_type": None,
            "last_runtime_error_type": (
                self._last_runtime_error_type
                if self._last_runtime_error_type is not None
                else None if self._websocket_open else "WSServerHandshakeError"
            ),
            "last_handshake_status": None if self._websocket_open else 403,
            "last_disconnect_reason": None
            if self._websocket_open
            else "handshake_failed",
            "last_subscribe_error_type": None,
            "last_close_code": None,
            "last_close_exception_type": None,
            "first_frame_received": self._websocket_open,
            "last_control_method": "subscribe" if self._websocket_open else None,
            "last_private_status_result": (
                "non_success"
                if self._private_status_non_success_frames > 0
                else None
            ),
            "last_private_status_reason": self._private_status_reason,
            "last_subscribe_device_count": subscribe_device_count,
            "last_subscribe_state_device_count": subscribe_state_device_count,
            "last_subscribe_state_key_samples": [],
            "last_subscribe_node_hash_samples": self._subscribe_node_hashes,
            "last_subscribe_node_candidate_hash_samples": (
                self._subscribe_node_candidate_hashes
            ),
            "last_data_node_hash_samples": (
                [self._data_node_hash] if has_data_payload else []
            ),
            "last_data_node_candidate_hash_samples": (
                [[self._data_node_hash]] if has_data_payload else []
            ),
            "recent_data_node_hash_samples": (
                [self._data_node_hash] if has_data_payload else []
            ),
            "recent_data_node_candidate_hash_samples": (
                [[self._data_node_hash]] if has_data_payload else []
            ),
            "recent_data_nodes_matching_loaded_topology": recent_matches,
            "recent_data_nodes_not_loaded": recent_not_loaded,
            "last_payload_type": "prop" if has_data_payload else None,
            "last_ignored_reason": None,
            "last_ignored_payload_type": None,
            "last_unsupported_payload_shape": None,
            "last_subscribe_sent_at": 122.0 if self._websocket_open else None,
            "last_message_at": 123.0 if self._websocket_open else None,
            "last_dispatched_at": 124.0 if has_data_payload else None,
        }

class _TransportWithHealth:
    """Push transport double exposing aggregate health."""

    last_start_error_type: str | None = None
    last_runtime_error_type: str | None = None

    def __init__(
        self,
        *,
        websocket_open: bool = True,
        dispatched_payloads: int | None = None,
        unsupported_messages: int = 0,
        received_messages: int | None = None,
        decoded_json_messages: int | None = None,
        recent_data_nodes_matching_loaded_topology: int | None = None,
        recent_data_nodes_not_loaded: int | None = None,
        data_node_hash: str = "41cf3c54b6edb00d",
        last_runtime_error_type: str | None = None,
        control_frames: int | None = None,
        subscribe_device_count: int | None = None,
        subscribe_state_device_count: int | None = None,
        subscribe_node_hashes: list[str] | None = None,
        subscribe_node_candidate_hashes: list[list[str]] | None = None,
        private_status_non_success_frames: int = 0,
        private_status_reason: str | None = None,
    ) -> None:
        """Initialize transport health shape."""
        self._websocket_open = websocket_open
        self._dispatched_payloads = dispatched_payloads
        self._unsupported_messages = unsupported_messages
        self._received_messages = received_messages
        self._decoded_json_messages = decoded_json_messages
        self._recent_data_nodes_matching_loaded_topology = (
            recent_data_nodes_matching_loaded_topology
        )
        self._recent_data_nodes_not_loaded = recent_data_nodes_not_loaded
        self._data_node_hash = data_node_hash
        self._last_runtime_error_type = last_runtime_error_type
        self._control_frames = control_frames
        self._subscribe_device_count = subscribe_device_count
        self._subscribe_state_device_count = subscribe_state_device_count
        self._subscribe_node_hashes = subscribe_node_hashes
        self._subscribe_node_candidate_hashes = subscribe_node_candidate_hashes
        self._private_status_non_success_frames = private_status_non_success_frames
        self._private_status_reason = private_status_reason
        if last_runtime_error_type is not None:
            self.last_runtime_error_type = last_runtime_error_type
        elif not websocket_open:
            self.last_runtime_error_type = "WSServerHandshakeError"

    @property
    def health(self) -> _TransportHealth:
        """Return aggregate-only transport health."""
        return _TransportHealth(
            websocket_open=self._websocket_open,
            dispatched_payloads=self._dispatched_payloads,
            unsupported_messages=self._unsupported_messages,
            received_messages=self._received_messages,
            decoded_json_messages=self._decoded_json_messages,
            recent_data_nodes_matching_loaded_topology=(
                self._recent_data_nodes_matching_loaded_topology
            ),
            recent_data_nodes_not_loaded=self._recent_data_nodes_not_loaded,
            data_node_hash=self._data_node_hash,
            last_runtime_error_type=self._last_runtime_error_type,
            control_frames=self._control_frames,
            subscribe_device_count=self._subscribe_device_count,
            subscribe_state_device_count=self._subscribe_state_device_count,
            subscribe_node_hashes=self._subscribe_node_hashes,
            subscribe_node_candidate_hashes=self._subscribe_node_candidate_hashes,
            private_status_non_success_frames=(
                self._private_status_non_success_frames
            ),
            private_status_reason=self._private_status_reason,
        )

    async def async_start(self, _callback) -> None:
        """Start no-op transport."""

    async def async_stop(self) -> None:
        """Stop no-op transport."""
