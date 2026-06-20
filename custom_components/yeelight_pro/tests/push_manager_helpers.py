"""Shared helpers for PushManager tests."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from custom_components.yeelight_pro.push_manager import PushPayloadCallback


class FakeTransport:
    """In-memory transport double used by PushManager tests."""

    def __init__(self) -> None:
        """Initialize the fake transport."""
        self.callback: PushPayloadCallback | None = None
        self.started_count = 0
        self.stopped_count = 0
        self.last_start_error_type: str | None = None
        self.last_runtime_error_type: str | None = None

    async def async_start(self, callback: PushPayloadCallback) -> None:
        """Store the callback without opening any network connection."""
        self.callback = callback
        self.started_count += 1

    async def async_stop(self) -> None:
        """Mark the fake transport as stopped."""
        self.stopped_count += 1

    async def emit(self, payload: Mapping[str, Any]) -> object | None:
        """Deliver a payload to the stored callback."""
        if self.callback is None:
            raise AssertionError("transport was not started")
        return await self.callback(payload)


class FakeTransportHealth:
    """Diagnostics-safe transport health double."""

    def __init__(self, payload: dict[str, Any]) -> None:
        """Store the aggregate health payload."""
        self._payload = payload

    def as_dict(self) -> dict[str, Any]:
        """Return the aggregate health payload."""
        return dict(self._payload)


def base_health(**overrides: object) -> dict[str, object]:
    """Return the default diagnostics-safe health payload."""
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
        "affected_context_count": 0,
        "affected_context_samples": [],
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
        "last_error_type": None,
        "last_payload_type": None,
        "last_payload_at": None,
    }
    data.update(overrides)
    return data


__all__ = ["FakeTransport", "FakeTransportHealth", "base_health"]
