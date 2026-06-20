"""No-network lifecycle manager for Yeelight Pro push transports."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
import json
import logging
from time import time
from typing import Any, Protocol

from .push_topology_diagnostics import push_topology_diagnostics
from .push_transport_frames import payload_type

PushPayloadCallback = Callable[[Mapping[str, Any]], Awaitable[object]]
_LOGGER = logging.getLogger(__name__)


class PushTransport(Protocol):
    """Transport contract used by future push implementations."""

    @property
    def last_start_error_type(self) -> str | None:
        """Return the aggregate error type from a recoverable start failure."""

    @property
    def last_runtime_error_type(self) -> str | None:
        """Return the aggregate error type from a background runtime failure."""

    async def async_start(self, callback: PushPayloadCallback) -> None:
        """Start receiving push payloads and forward them to callback."""

    async def async_stop(self) -> None:
        """Stop receiving push payloads."""


@dataclass(slots=True)
class PushHealth:
    """Diagnostics-safe aggregate health for the push manager."""

    running: bool = False
    started_count: int = 0
    stopped_count: int = 0
    handled_payloads: int = 0
    changed_payloads: int = 0
    unchanged_payloads: int = 0
    property_updates: int = 0
    empty_param_updates: int = 0
    applied_property_updates: int = 0
    unknown_property_updates: int = 0
    affected_context_count: int = 0
    affected_context_samples: tuple[dict[str, Any], ...] = ()
    group_updates: int = 0
    topology_node_updates: int = 0
    routed_property_updates: int = 0
    last_applied_node_samples: tuple[dict[str, Any], ...] = ()
    last_unknown_node_samples: tuple[dict[str, Any], ...] = ()
    recent_applied_node_samples: tuple[dict[str, Any], ...] = ()
    recent_unknown_node_samples: tuple[dict[str, Any], ...] = ()
    dispatched_events: int = 0
    last_property_update_count: int = 0
    last_applied_property_update_count: int = 0
    last_unknown_property_update_count: int = 0
    last_group_update_count: int = 0
    last_topology_node_update_count: int = 0
    last_routed_property_update_count: int = 0
    last_dispatched_event_count: int = 0
    last_payload_changed: bool = False
    last_payload_handle_duration_ms: float | None = None
    last_listener_notification_count: int = 0
    last_listener_context_count: int = 0
    last_error_type: str | None = None
    last_payload_type: str | None = None
    last_payload_at: float | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return an aggregate-only diagnostics payload."""
        return {
            "running": self.running,
            "started_count": self.started_count,
            "stopped_count": self.stopped_count,
            "handled_payloads": self.handled_payloads,
            "changed_payloads": self.changed_payloads,
            "unchanged_payloads": self.unchanged_payloads,
            "property_updates": self.property_updates,
            "empty_param_updates": self.empty_param_updates,
            "applied_property_updates": self.applied_property_updates,
            "unknown_property_updates": self.unknown_property_updates,
            "affected_context_count": self.affected_context_count,
            "affected_context_samples": list(self.affected_context_samples),
            "group_updates": self.group_updates,
            "topology_node_updates": self.topology_node_updates,
            "routed_property_updates": self.routed_property_updates,
            "last_applied_node_samples": list(self.last_applied_node_samples),
            "last_unknown_node_samples": list(self.last_unknown_node_samples),
            "recent_applied_node_samples": list(self.recent_applied_node_samples),
            "recent_unknown_node_samples": list(self.recent_unknown_node_samples),
            "dispatched_events": self.dispatched_events,
            "last_property_update_count": self.last_property_update_count,
            "last_applied_property_update_count": self.last_applied_property_update_count,
            "last_unknown_property_update_count": self.last_unknown_property_update_count,
            "last_group_update_count": self.last_group_update_count,
            "last_topology_node_update_count": self.last_topology_node_update_count,
            "last_routed_property_update_count": self.last_routed_property_update_count,
            "last_dispatched_event_count": self.last_dispatched_event_count,
            "last_payload_changed": self.last_payload_changed,
            "last_payload_handle_duration_ms": self.last_payload_handle_duration_ms,
            "last_listener_notification_count": self.last_listener_notification_count,
            "last_listener_context_count": self.last_listener_context_count,
            "last_error_type": self.last_error_type,
            "last_payload_type": self.last_payload_type,
            "last_payload_at": self.last_payload_at,
        }


class PushManager:
    """Manage an injected push transport without opening network connections."""

    def __init__(self, coordinator: Any, transport: PushTransport) -> None:
        """Initialize the manager with a coordinator and injected transport."""
        self._coordinator = coordinator
        self._transport = transport
        self._health = PushHealth()
        self._transport_started = False
        self._recoverable_start_error_type: str | None = None

    @property
    def health(self) -> PushHealth:
        """Return diagnostics-safe aggregate push health."""
        self._sync_transport_runtime_error()
        self._clear_recovered_transport_start_error()
        return self._health

    @property
    def transport_health(self) -> dict[str, Any] | None:
        """Return diagnostics-safe transport health when the transport exposes it."""
        health = getattr(self._transport, "health", None)
        as_dict = getattr(health, "as_dict", None)
        if callable(as_dict):
            value = as_dict()
            if isinstance(value, dict):
                return {
                    **value,
                    **push_topology_diagnostics(self._coordinator, value),
                }
        return None

    async def async_start(self) -> None:
        """Start the injected transport once."""
        if self._health.running or self._transport_started:
            return
        self._health.running = True
        self._health.last_error_type = None
        try:
            await self._transport.async_start(self._handle_payload)
        except Exception as err:
            self._health.running = False
            self._health.last_error_type = type(err).__name__
            raise
        self._transport_started = True
        self._health.started_count += 1
        transport_start_error = getattr(self._transport, "last_start_error_type", None)
        if transport_start_error is not None:
            self._health.last_error_type = transport_start_error
            self._recoverable_start_error_type = transport_start_error
        self._sync_transport_runtime_error()
        _LOGGER.info(
            "Started Yeelight Pro WebSocket push runtime: recoverable_start_error=%s",
            self._health.last_error_type,
        )

    async def async_stop(self) -> None:
        """Stop the injected transport once."""
        if not self._health.running and not self._transport_started:
            return
        self._health.running = False
        if not self._transport_started:
            return
        had_error = False
        try:
            await self._transport.async_stop()
        except Exception as err:
            self._health.last_error_type = type(err).__name__
            had_error = True
            raise
        finally:
            if not had_error:
                self._transport_started = False
                self._health.last_error_type = None
                self._health.stopped_count += 1

    async def _handle_payload(self, payload: Mapping[str, Any]) -> object | None:
        """Forward payloads to the coordinator while the manager is running."""
        if not self._health.running:
            return None
        started_at = time()
        try:
            result = await self._coordinator.async_handle_push_payload(payload)
        except Exception as err:
            self._recoverable_start_error_type = None
            self._health.last_error_type = type(err).__name__
            return None
        self._health.last_payload_handle_duration_ms = round(
            (time() - started_at) * 1000,
            3,
        )
        self._health.handled_payloads += 1
        self._record_payload_result(result)
        self._health.last_payload_type = payload_type(payload)
        self._health.last_payload_at = time()
        self._recoverable_start_error_type = None
        self._health.last_error_type = None
        _log_payload_result(self._coordinator, self._health)
        return result

    def _sync_transport_runtime_error(self) -> None:
        """Copy transport runtime error type into aggregate health."""
        transport_error = getattr(self._transport, "last_runtime_error_type", None)
        if isinstance(transport_error, str) and transport_error:
            self._health.last_error_type = transport_error

    def _clear_recovered_transport_start_error(self) -> None:
        """Clear a stale recoverable start error after the transport is healthy."""
        if (
            self._recoverable_start_error_type is None
            or self._health.last_error_type != self._recoverable_start_error_type
        ):
            return
        transport_error = getattr(self._transport, "last_runtime_error_type", None)
        if isinstance(transport_error, str) and transport_error:
            return
        health = getattr(self._transport, "health", None)
        as_dict = getattr(health, "as_dict", None)
        if not callable(as_dict):
            return
        value = as_dict()
        if not isinstance(value, Mapping):
            return
        if value.get("websocket_open") is True and value.get("running") is not False:
            self._health.last_error_type = None
            self._recoverable_start_error_type = None

    def _record_payload_result(self, result: object | None) -> None:
        """Copy aggregate coordinator push results into diagnostics health."""
        summary = getattr(self._coordinator, "last_push_property_summary", None)
        summary_dict = _summary_as_dict(summary)
        input_updates = _int_value(summary_dict.get("input_updates"))
        empty_params = _int_value(summary_dict.get("empty_param_updates"))
        applied = _int_value(summary_dict.get("applied_device_updates"))
        unknown = _int_value(summary_dict.get("unknown_device_updates"))
        affected_context_count = _int_value(summary_dict.get("affected_context_count"))
        affected_context_samples = _sample_tuple(
            summary_dict.get("affected_context_samples")
        )
        group_updates = _int_value(summary_dict.get("group_updates"))
        topology_updates = _int_value(summary_dict.get("topology_node_updates"))
        routed_updates = _int_value(summary_dict.get("routed_updates"))
        applied_samples = _sample_tuple(summary_dict.get("applied_node_samples"))
        unknown_samples = _sample_tuple(summary_dict.get("unknown_node_samples"))
        changed = bool(summary_dict.get("changed"))
        event_count = _event_count(result)

        self._health.property_updates += input_updates
        self._health.empty_param_updates += empty_params
        self._health.applied_property_updates += applied
        self._health.unknown_property_updates += unknown
        self._health.affected_context_count = affected_context_count
        self._health.affected_context_samples = affected_context_samples
        self._health.group_updates += group_updates
        self._health.topology_node_updates += topology_updates
        self._health.routed_property_updates += routed_updates
        self._health.last_applied_node_samples = applied_samples
        self._health.last_unknown_node_samples = unknown_samples
        if applied_samples:
            self._health.recent_applied_node_samples = applied_samples
        if unknown_samples:
            self._health.recent_unknown_node_samples = unknown_samples
        self._health.dispatched_events += event_count
        self._health.last_property_update_count = input_updates
        self._health.last_applied_property_update_count = applied
        self._health.last_unknown_property_update_count = unknown
        self._health.last_group_update_count = group_updates
        self._health.last_topology_node_update_count = topology_updates
        self._health.last_routed_property_update_count = routed_updates
        self._health.last_dispatched_event_count = event_count
        self._health.last_payload_changed = changed or event_count > 0
        self._health.last_listener_notification_count = _int_value(
            getattr(self._coordinator, "last_listener_notification_count", None)
        )
        self._health.last_listener_context_count = _int_value(
            getattr(self._coordinator, "last_listener_context_count", None)
        )
        if self._health.last_payload_changed:
            self._health.changed_payloads += 1
        else:
            self._health.unchanged_payloads += 1

def _event_count(result: object | None) -> int:
    """Return dispatched event count from the coordinator result."""
    return len(result) if isinstance(result, list) else 0


def _summary_as_dict(summary: Any) -> Mapping[str, Any]:
    """Return a real coordinator summary, ignoring mock-created attributes."""
    if isinstance(summary, Mapping):
        return summary
    if _is_mock_object(summary):
        return {}
    as_dict = getattr(summary, "as_dict", None)
    if not callable(as_dict):
        return {}
    value = as_dict()
    return value if isinstance(value, Mapping) else {}


def _is_mock_object(value: Any) -> bool:
    """Return true for unittest.mock dynamic attributes without importing mocks."""
    return value.__class__.__module__.startswith("unittest.mock")


def _int_value(value: Any) -> int:
    """Return safe integer diagnostics counters."""
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _sample_tuple(value: Any) -> tuple[dict[str, Any], ...]:
    """Return diagnostics samples only when they are already mapping objects."""
    if not isinstance(value, list):
        return ()
    return tuple(dict(item) for item in value if isinstance(item, Mapping))


def _log_payload_result(coordinator: Any, health: PushHealth) -> None:
    """Log aggregate push routing facts; debug mode promotes them to INFO."""
    payload = {
        "type": health.last_payload_type,
        "handled_payloads": health.handled_payloads,
        "changed": health.last_payload_changed,
        "property_updates": health.last_property_update_count,
        "applied_property_updates": health.last_applied_property_update_count,
        "unknown_property_updates": health.last_unknown_property_update_count,
        "affected_context_count": health.affected_context_count,
        "affected_context_samples": list(health.affected_context_samples),
        "group_updates": health.last_group_update_count,
        "topology_node_updates": health.last_topology_node_update_count,
        "routed_property_updates": health.last_routed_property_update_count,
        "listener_notifications": health.last_listener_notification_count,
        "listener_contexts": health.last_listener_context_count,
        "handle_duration_ms": health.last_payload_handle_duration_ms,
        "applied_node_samples": list(health.last_applied_node_samples),
        "unknown_node_samples": list(health.last_unknown_node_samples),
    }
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    if getattr(coordinator, "debug_mode", False) is True:
        _LOGGER.info("Yeelight Pro push payload applied: %s", text)
        return
    _LOGGER.debug("Yeelight Pro push payload applied: %s", text)


__all__ = [
    "PushHealth",
    "PushManager",
    "PushPayloadCallback",
    "PushTransport",
]
