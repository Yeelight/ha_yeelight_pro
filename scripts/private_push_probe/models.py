"""Shared models for the private push topology probe."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class TopologySnapshot:
    """Runtime topology and filter facts used by the push probe."""

    data: dict[int, dict[str, Any]]
    gateways: dict[int, dict[str, Any]]
    groups: list[dict[str, Any]]
    rooms: list[dict[str, Any]]
    areas: list[dict[str, Any]]
    houses: list[dict[str, Any]]
    filter_config: Mapping[str, Any] | None
    hydration: Mapping[str, int]
    endpoint_errors: dict[str, str]
    hash_count: int = 0


@dataclass(slots=True)
class ProbeSummary:
    """Diagnostics-safe aggregate push/topology matching result."""

    connected: bool = False
    subscribe_sent: bool = False
    frames_seen: int = 0
    control_frames: int = 0
    private_status_non_success_frames: int = 0
    last_private_status_reason: str | None = None
    data_frames: int = 0
    prop_updates: int = 0
    event_payloads: int = 0
    unsupported_frames: int = 0
    malformed_frames: int = 0
    close_frames: int = 0
    last_close_code: int | None = None
    last_close_exception_type: str | None = None
    idle_timeouts: int = 0
    heartbeats_sent: int = 0
    matched_loaded_topology: int = 0
    selected_id_loaded: int = 0
    alias_resolved_matches: int = 0
    not_loaded: int = 0
    maybe_filtered: int = 0
    ambiguous_candidates: int = 0
    empty_param_updates: int = 0
    event_matched_loaded_topology: int = 0
    event_selected_id_loaded: int = 0
    event_alias_resolved_matches: int = 0
    event_not_loaded: int = 0
    event_maybe_filtered: int = 0
    event_ambiguous_candidates: int = 0
    last_error_type: str | None = None
    payload_types: Counter[str] = field(default_factory=Counter)
    control_methods: Counter[str] = field(default_factory=Counter)
    update_samples: list[dict[str, Any]] = field(default_factory=list)
    event_samples: list[dict[str, Any]] = field(default_factory=list)
    subscribe_samples: list[dict[str, Any]] = field(default_factory=list)
    unsafe_subscribe_details: list[dict[str, Any]] = field(default_factory=list)
    subscribe_match: Counter[str] = field(default_factory=Counter)
    subscribe_snapshot_summary: dict[str, Any] = field(default_factory=dict)
    subscribe_topology_coverage: dict[str, Any] = field(default_factory=dict)
    data_hash_match: Counter[str] = field(default_factory=Counter)

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-safe summary."""
        return {
            "connected": self.connected,
            "subscribe_sent": self.subscribe_sent,
            "frames_seen": self.frames_seen,
            "control_frames": self.control_frames,
            "private_status_non_success_frames": (
                self.private_status_non_success_frames
            ),
            "last_private_status_reason": self.last_private_status_reason,
            "data_frames": self.data_frames,
            "prop_updates": self.prop_updates,
            "event_payloads": self.event_payloads,
            "unsupported_frames": self.unsupported_frames,
            "malformed_frames": self.malformed_frames,
            "close_frames": self.close_frames,
            "last_close_code": self.last_close_code,
            "last_close_exception_type": self.last_close_exception_type,
            "idle_timeouts": self.idle_timeouts,
            "heartbeats_sent": self.heartbeats_sent,
            "matched_loaded_topology": self.matched_loaded_topology,
            "selected_id_loaded": self.selected_id_loaded,
            "alias_resolved_matches": self.alias_resolved_matches,
            "not_loaded": self.not_loaded,
            "maybe_filtered": self.maybe_filtered,
            "ambiguous_candidates": self.ambiguous_candidates,
            "empty_param_updates": self.empty_param_updates,
            "event_matched_loaded_topology": self.event_matched_loaded_topology,
            "event_selected_id_loaded": self.event_selected_id_loaded,
            "event_alias_resolved_matches": self.event_alias_resolved_matches,
            "event_not_loaded": self.event_not_loaded,
            "event_maybe_filtered": self.event_maybe_filtered,
            "event_ambiguous_candidates": self.event_ambiguous_candidates,
            "last_error_type": self.last_error_type,
            "payload_types": dict(sorted(self.payload_types.items())),
            "control_methods": dict(sorted(self.control_methods.items())),
            "subscribe_match": dict(sorted(self.subscribe_match.items())),
            "subscribe_snapshot_summary": self.subscribe_snapshot_summary,
            "subscribe_topology_coverage": self.subscribe_topology_coverage,
            "data_hash_match": dict(sorted(self.data_hash_match.items())),
            "update_samples": self.update_samples,
            "event_samples": self.event_samples,
            "subscribe_samples": self.subscribe_samples,
            **(
                {"unsafe_subscribe_details": self.unsafe_subscribe_details}
                if self.unsafe_subscribe_details
                else {}
            ),
        }
