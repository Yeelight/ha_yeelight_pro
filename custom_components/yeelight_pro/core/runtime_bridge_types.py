"""Shared runtime bridge models for Yeelight Pro push/LAN updates."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from hashlib import blake2b
from typing import Any

RuntimeEventDedupeKey = str
RuntimeUpdateContext = tuple[str, str]
MAX_RUNTIME_EVENT_DEDUPE_KEYS = 256
MAX_RUNTIME_PROPERTY_SAMPLE_ITEMS = 5
MAX_RUNTIME_PROPERTY_PARAM_KEYS = 12
MAX_RUNTIME_CONTEXT_SAMPLE_ITEMS = 5


@dataclass(frozen=True, slots=True)
class RuntimePropertyUpdate:
    """已接收推送帧中的属性更新。"""

    node_id: int
    node_type: int | None
    params: Mapping[str, Any]
    node_id_candidates: tuple[tuple[str, int], ...] = field(
        default=(),
        compare=False,
    )


@dataclass(frozen=True, slots=True)
class RuntimePropertyUpdateSummary:
    """Aggregate result for diagnostics after applying property updates."""

    input_updates: int = 0
    empty_param_updates: int = 0
    applied_device_updates: int = 0
    unknown_device_updates: int = 0
    group_updates: int = 0
    topology_node_updates: int = 0
    routed_updates: int = 0
    changed: bool = False
    device_import_filter_enabled: bool = False
    applied_node_samples: tuple[dict[str, Any], ...] = ()
    unknown_node_samples: tuple[dict[str, Any], ...] = ()
    affected_contexts: tuple[RuntimeUpdateContext, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        """Return diagnostics-safe aggregate counters."""
        return {
            "input_updates": self.input_updates,
            "empty_param_updates": self.empty_param_updates,
            "applied_device_updates": self.applied_device_updates,
            "unknown_device_updates": self.unknown_device_updates,
            "group_updates": self.group_updates,
            "topology_node_updates": self.topology_node_updates,
            "routed_updates": self.routed_updates,
            "changed": self.changed,
            "device_import_filter_enabled": self.device_import_filter_enabled,
            "applied_node_samples": list(self.applied_node_samples),
            "unknown_node_samples": list(self.unknown_node_samples),
            "affected_context_count": len(self.affected_contexts),
            "affected_context_samples": _safe_context_samples(
                self.affected_contexts,
            ),
        }


__all__ = [
    "MAX_RUNTIME_EVENT_DEDUPE_KEYS",
    "MAX_RUNTIME_CONTEXT_SAMPLE_ITEMS",
    "MAX_RUNTIME_PROPERTY_PARAM_KEYS",
    "MAX_RUNTIME_PROPERTY_SAMPLE_ITEMS",
    "RuntimeEventDedupeKey",
    "RuntimePropertyUpdate",
    "RuntimePropertyUpdateSummary",
    "RuntimeUpdateContext",
]


def _safe_context_samples(
    contexts: tuple[RuntimeUpdateContext, ...],
) -> list[dict[str, str]]:
    """Return redacted runtime listener contexts for diagnostics."""
    samples: list[dict[str, str]] = []
    for kind, value in contexts[:MAX_RUNTIME_CONTEXT_SAMPLE_ITEMS]:
        samples.append(
            {
                "kind": str(kind),
                "node_id_hash": _stable_digest(value),
            }
        )
    return samples


def _stable_digest(value: Any) -> str:
    """Return a stable non-reversible identifier for diagnostics."""
    digest = blake2b(digest_size=8)
    digest.update(str(value).encode())
    return digest.hexdigest()
