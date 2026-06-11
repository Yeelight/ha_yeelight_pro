"""Yeelight Pro diagnostics aggregate helpers."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from typing import Any

from .capabilities.spec_correction import summarize_product_schema_corrections
from .device_filter import matches_device_import_filter
from .diagnostic_inventory import spec_runtime_inventory_diagnostics
from .entity_candidates import EntityCandidate, iter_entity_candidates

_ONLINE_STRINGS = {
    "true": True,
    "1": True,
    "yes": True,
    "on": True,
    "false": False,
    "0": False,
    "no": False,
    "off": False,
}
_TOPOLOGY_DIFF_COLLECTION_KEYS = frozenset(
    {"added", "removed", "metadata_changed"}
)
_TOPOLOGY_DIFF_COUNT_KEYS = frozenset(
    {
        "previous_generation",
        "current_generation",
        "total_added",
        "total_removed",
        "total_metadata_changed",
        "total_changes",
    }
)
_TOPOLOGY_CANDIDATE_SOURCES = frozenset({"scene", "group", "house"})


def mapping_values(value: Any) -> list[Mapping[str, Any]]:
    """Return mapping values from dict-like coordinator collections."""
    if not isinstance(value, Mapping):
        return []
    return [item for item in value.values() if isinstance(item, Mapping)]


def safe_len(value: Any) -> int:
    """Return collection length for diagnostics, falling back to zero."""
    try:
        return len(value)
    except TypeError:
        return 0


def availability_counts(items: list[Mapping[str, Any]]) -> dict[str, int]:
    """Return online/offline aggregate counts without exposing devices."""
    counts = {"online": 0, "offline": 0, "unknown": 0}
    for item in items:
        state = _online_state(item.get("online"))
        key = "online" if state is True else "offline" if state is False else "unknown"
        counts[key] += 1
    return counts


def topology_diff_summary(coordinator: Any) -> dict[str, Any] | None:
    """Return a sanitized topology diff summary if the coordinator has one."""
    summary = getattr(coordinator, "topology_diff_summary", None)
    as_dict = getattr(summary, "as_dict", None)
    if callable(as_dict):
        return _sanitize_topology_diff_mapping(as_dict())
    return None


def spec_correction_diagnostics(
    devices: list[Mapping[str, Any]],
) -> dict[str, int]:
    """Return aggregate spec correction diagnostics."""
    totals = {
        "schemas_seen": 0,
        "components_seen": 0,
        "properties_seen": 0,
        "runtime_filtered_properties": 0,
        "normalized_format_properties": 0,
        "writable_properties": 0,
        "readonly_properties": 0,
    }
    for device in devices:
        schema = device.get("product_schema")
        if not isinstance(schema, Mapping):
            continue
        totals["schemas_seen"] += 1
        for key, value in summarize_product_schema_corrections(schema).items():
            totals[key] += value
    return totals


def entity_candidate_diagnostics(coordinator: Any) -> dict[str, Any]:
    """Return aggregate entity candidate diagnostics without raw identifiers."""
    candidate_view = _CandidateCoordinator(coordinator, _candidate_data(coordinator))
    return _entity_candidate_summary(list(iter_entity_candidates(candidate_view)))


def entity_import_filter_preview_diagnostics(
    coordinator: Any,
    filter_config: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Preview entity counts if the device import filter were applied."""
    filtered_data = {
        key: device
        for key, device in _candidate_data(coordinator).items()
        if matches_device_import_filter(device, filter_config)
    }
    filtered = _CandidateCoordinator(coordinator, filtered_data)
    return _entity_candidate_summary(list(iter_entity_candidates(filtered)))


def counter_known_values(
    items: list[Mapping[str, Any]],
    key: str,
    *,
    known_values: set[str],
) -> dict[str, int]:
    """Count mapping values by key, collapsing unknown raw strings."""
    counter: Counter[str] = Counter()
    for item in items:
        value = item.get(key)
        if value is None:
            continue
        text = str(value)
        counter[text if text in known_values else "unknown"] += 1
    return dict(counter)


def count_with_key(items: list[Mapping[str, Any]], key: str) -> int:
    """Count items that include a non-empty diagnostics aggregate key."""
    return sum(1 for item in items if bool(item.get(key)))


class _CandidateCoordinator:
    """Coordinator view with filtered device data and unchanged topology helpers."""

    def __init__(
        self,
        coordinator: Any,
        data: Mapping[Any, Mapping[str, Any]],
    ) -> None:
        self.data = data
        self.scenes = _list_attr(coordinator, "scenes")
        self.groups = _list_attr(coordinator, "groups")
        self.house_id = getattr(coordinator, "house_id", None)
        self.hide_unknown_entities = bool(
            getattr(coordinator, "hide_unknown_entities", True)
        )


def _entity_candidate_summary(
    candidates: list[EntityCandidate],
) -> dict[str, Any]:
    """Summarize entity candidates without exposing candidate identifiers."""
    return {
        "total": len(candidates),
        "platforms": _candidate_counter(candidates, "platform"),
        "device_platforms": _candidate_platforms_by_source(candidates, "device"),
        "sources": _candidate_counter(candidates, "source"),
        "source_classes": _candidate_source_classes(candidates),
        "duplicate_key_count": _duplicate_candidate_key_count(candidates),
        "availability": {
            "available": sum(1 for item in candidates if item.available),
            "unavailable": sum(1 for item in candidates if not item.available),
        },
    }


def _candidate_counter(
    candidates: list[EntityCandidate],
    attr: str,
) -> dict[str, int]:
    """Count candidate string attributes."""
    counter: Counter[str] = Counter()
    for candidate in candidates:
        value = getattr(candidate, attr, None)
        if isinstance(value, str) and value:
            counter[value] += 1
    return dict(counter)


def _candidate_platforms_by_source(
    candidates: list[EntityCandidate],
    source: str,
) -> dict[str, int]:
    """Count candidate platforms for one aggregate source class."""
    return _candidate_counter(
        [candidate for candidate in candidates if candidate.source == source],
        "platform",
    )


def _candidate_source_classes(candidates: list[EntityCandidate]) -> dict[str, int]:
    """Count candidate sources by diagnostics-safe class."""
    counter: Counter[str] = Counter()
    for candidate in candidates:
        counter[_candidate_source_class(candidate.source)] += 1
    return dict(counter)


def _candidate_source_class(source: str) -> str:
    """Return the aggregate source class for an entity candidate."""
    if source == "device":
        return "device"
    if source in _TOPOLOGY_CANDIDATE_SOURCES:
        return "topology"
    return "other"


def _duplicate_candidate_key_count(candidates: list[EntityCandidate]) -> int:
    """Count duplicate (platform, unique_id) candidates without exposing keys."""
    key_counts = Counter(candidate.key for candidate in candidates)
    return sum(count - 1 for count in key_counts.values() if count > 1)


def _candidate_data(coordinator: Any) -> dict[Any, Mapping[str, Any]]:
    """Return candidate source data, falling back to devices for diagnostics."""
    data = getattr(coordinator, "data", None)
    if isinstance(data, Mapping):
        return {
            key: value for key, value in data.items() if isinstance(value, Mapping)
        }
    devices = getattr(coordinator, "devices", None)
    if isinstance(devices, Mapping):
        return {
            key: value for key, value in devices.items() if isinstance(value, Mapping)
        }
    return {}


def _list_attr(coordinator: Any, name: str) -> list[dict[str, Any]]:
    """Return a diagnostics-safe list attribute for candidate preview."""
    value = getattr(coordinator, name, [])
    return value if isinstance(value, list) else []


def _online_state(value: Any) -> bool | None:
    """Parse a diagnostics-safe online value."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if not isinstance(value, str):
        return None
    return _ONLINE_STRINGS.get(value.strip().lower())


def _sanitize_topology_diff_mapping(value: Any) -> dict[str, Any] | None:
    """Whitelist topology diff aggregate fields for diagnostics."""
    if not isinstance(value, Mapping):
        return None
    sanitized: dict[str, Any] = {}
    for key in _TOPOLOGY_DIFF_COUNT_KEYS:
        if isinstance(value.get(key), int):
            sanitized[key] = value[key]
    for key in _TOPOLOGY_DIFF_COLLECTION_KEYS:
        counts = value.get(key)
        if isinstance(counts, Mapping):
            sanitized[key] = {
                str(name): count
                for name, count in counts.items()
                if isinstance(count, int)
            }
    return sanitized


__all__ = [
    "availability_counts",
    "count_with_key",
    "counter_known_values",
    "entity_candidate_diagnostics",
    "entity_import_filter_preview_diagnostics",
    "mapping_values",
    "safe_len",
    "spec_correction_diagnostics",
    "spec_runtime_inventory_diagnostics",
    "topology_diff_summary",
]
