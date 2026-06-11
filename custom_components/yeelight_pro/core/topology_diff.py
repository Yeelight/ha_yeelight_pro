"""Topology diff helpers for Yeelight Pro runtime snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

TOPOLOGY_COLLECTIONS = (
    "devices",
    "gateways",
    "areas",
    "rooms",
    "groups",
    "scenes",
)

TopologySnapshot = Mapping[str, Mapping[str, tuple[Any, ...]]]


@dataclass(frozen=True)
class TopologyDiffSummary:
    """Non-sensitive topology diff summary for diagnostics and Repairs."""

    previous_generation: int
    current_generation: int
    added: dict[str, int]
    removed: dict[str, int]
    metadata_changed: dict[str, int]

    @property
    def total_added(self) -> int:
        """Return the number of added topology items."""
        return sum(self.added.values())

    @property
    def total_removed(self) -> int:
        """Return the number of removed topology items."""
        return sum(self.removed.values())

    @property
    def total_metadata_changed(self) -> int:
        """Return the number of topology items whose entity metadata changed."""
        return sum(self.metadata_changed.values())

    @property
    def total_changes(self) -> int:
        """Return the total number of classified topology changes."""
        return (
            self.total_added
            + self.total_removed
            + self.total_metadata_changed
        )

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-safe summary without IDs, names, or raw payloads."""
        return {
            "previous_generation": self.previous_generation,
            "current_generation": self.current_generation,
            "added": dict(self.added),
            "removed": dict(self.removed),
            "metadata_changed": dict(self.metadata_changed),
            "total_added": self.total_added,
            "total_removed": self.total_removed,
            "total_metadata_changed": self.total_metadata_changed,
            "total_changes": self.total_changes,
        }


def empty_topology_diff(
    *,
    previous_generation: int = 0,
    current_generation: int = 0,
) -> TopologyDiffSummary:
    """Return an empty topology diff summary."""
    return TopologyDiffSummary(
        previous_generation=previous_generation,
        current_generation=current_generation,
        added=_empty_counts(),
        removed=_empty_counts(),
        metadata_changed=_empty_counts(),
    )


def summarize_topology_diff(
    previous: TopologySnapshot | None,
    current: TopologySnapshot,
    *,
    previous_generation: int,
    current_generation: int,
) -> TopologyDiffSummary:
    """Classify topology changes by add/remove/entity-metadata update."""
    if previous is None:
        return empty_topology_diff(
            previous_generation=previous_generation,
            current_generation=current_generation,
        )

    added = _empty_counts()
    removed = _empty_counts()
    metadata_changed = _empty_counts()

    for collection in TOPOLOGY_COLLECTIONS:
        previous_items = previous.get(collection, {})
        current_items = current.get(collection, {})
        previous_keys = set(previous_items)
        current_keys = set(current_items)

        added[collection] = len(current_keys - previous_keys)
        removed[collection] = len(previous_keys - current_keys)
        metadata_changed[collection] = sum(
            1
            for key in previous_keys & current_keys
            if previous_items[key] != current_items[key]
        )

    return TopologyDiffSummary(
        previous_generation=previous_generation,
        current_generation=current_generation,
        added=added,
        removed=removed,
        metadata_changed=metadata_changed,
    )


def build_topology_snapshot(
    *,
    devices: Mapping[Any, Mapping[str, Any]],
    gateways: Mapping[Any, Mapping[str, Any]],
    areas: list[dict[str, Any]],
    rooms: list[dict[str, Any]],
    groups: list[dict[str, Any]],
    scenes: list[dict[str, Any]],
) -> dict[str, dict[str, tuple[Any, ...]]]:
    """Build a comparable topology snapshot without runtime state values."""
    return {
        "devices": _device_collection_snapshot(devices),
        "gateways": _device_collection_snapshot(gateways),
        "areas": _named_collection_snapshot(areas),
        "rooms": _named_collection_snapshot(rooms),
        "groups": _named_collection_snapshot(groups),
        "scenes": _named_collection_snapshot(scenes),
    }


def topology_snapshot_signature(snapshot: TopologySnapshot) -> tuple[Any, ...]:
    """Return a stable comparable signature for a topology snapshot."""
    return tuple(
        (
            collection,
            tuple(sorted(snapshot.get(collection, {}).items(), key=lambda item: item[0])),
        )
        for collection in TOPOLOGY_COLLECTIONS
    )


def _empty_counts() -> dict[str, int]:
    """Return zero counts for every topology collection."""
    return dict.fromkeys(TOPOLOGY_COLLECTIONS, 0)


def _device_collection_snapshot(
    items: Mapping[Any, Mapping[str, Any]],
) -> dict[str, tuple[Any, ...]]:
    """Return a diffable snapshot for device-like topology items."""
    return {
        _device_item_key(item): _device_item_signature(item)
        for item in items.values()
    }


def _device_item_key(item: Mapping[str, Any]) -> str:
    """Return an internal stable key that is never exposed in summaries."""
    return str(item.get("device_id", item.get("id", "")))


def _device_item_signature(item: Mapping[str, Any]) -> tuple[Any, ...]:
    """Return the fields that affect HA device/entity topology."""
    device_info = item.get("ha_device_instance", {}).get("device_info", {})
    components = item.get("ha_device_instance", {}).get("components", [])
    identifiers = device_info.get("identifiers")
    via_device = device_info.get("via_device")
    return (
        item.get("device_id", item.get("id")),
        item.get("name"),
        item.get("type"),
        item.get("category"),
        item.get("pid"),
        item.get("model_id", item.get("modelId")),
        device_info.get("name"),
        device_info.get("model"),
        device_info.get("model_id"),
        device_info.get("suggested_area"),
        item.get("roomId", item.get("room_id")),
        item.get("gatewayId", item.get("gateway_id")),
        _component_signature(components),
        _freeze_for_signature(identifiers),
        _freeze_for_signature(via_device),
    )


def _component_signature(components: Any) -> tuple[Any, ...]:
    """Return component topology identity without component runtime state."""
    if not isinstance(components, list):
        return ()
    return tuple(
        (
            component.get("component_id", component.get("componentId")),
            component.get("component_type", component.get("componentType")),
            component.get("category"),
        )
        for component in components
        if isinstance(component, Mapping)
    )


def _named_collection_snapshot(items: list[dict[str, Any]]) -> dict[str, tuple[Any, ...]]:
    """Return a diffable snapshot for area/room/group/scene collections."""
    return {
        _named_item_key(item): _named_item_signature(item)
        for item in items
    }


def _named_item_key(item: Mapping[str, Any]) -> str:
    """Return an internal stable key for named topology collections."""
    item_id = item.get("id")
    if item_id is not None:
        return str(item_id)
    return str((item.get("type"), item.get("name")))


def _named_item_signature(item: Mapping[str, Any]) -> tuple[Any, ...]:
    """Return named item metadata that affects HA topology."""
    return (
        item.get("id"),
        item.get("name"),
        item.get("type"),
        item.get("nodeType", item.get("node_type")),
        item.get("parentId", item.get("parent_id")),
        _freeze_unordered_collection(
            item.get("device_ids", item.get("deviceIds", [])) or []
        ),
        _freeze_unordered_collection(
            item.get("roomIds", item.get("room_ids", [])) or []
        ),
    )


def _freeze_unordered_collection(value: Any) -> tuple[Any, ...]:
    """Return a stable signature for membership lists whose order is not meaningful."""
    if not isinstance(value, list | tuple | set):
        return ()
    return tuple(
        sorted(
            (_freeze_for_signature(child) for child in value),
            key=repr,
        )
    )


def _freeze_for_signature(value: Any) -> Any:
    """Turn nested lists/dicts into stable comparable tuples."""
    if isinstance(value, Mapping):
        return tuple(
            (key, _freeze_for_signature(child))
            for key, child in sorted(value.items(), key=lambda item: str(item[0]))
        )
    if isinstance(value, list | tuple | set):
        return tuple(_freeze_for_signature(child) for child in value)
    return value
