"""Node-id resolution helpers for Yeelight Pro runtime push payloads."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from hashlib import blake2b
from typing import Any

from ..const import ATTR_EVENT_ATTRIBUTES
from ..push import ATTR_NODE_ID_CANDIDATES
from .lan_topology_specs import (
    NODE_TYPE_AREA,
    NODE_TYPE_DEVICE,
    NODE_TYPE_GROUP,
    NODE_TYPE_HOUSE,
    NODE_TYPE_ROOM,
)
from .runtime_bridge_types import (
    MAX_RUNTIME_PROPERTY_PARAM_KEYS,
    MAX_RUNTIME_PROPERTY_SAMPLE_ITEMS,
    RuntimePropertyUpdate,
)

_NODE_IDENTITY_FIELDS = frozenset(
    {"id", "nodeId", "node_id", "resId", "res_id", "deviceId", "device_id"}
)
_TOPOLOGY_RELATION_FIELDS = {
    "groupId": (NODE_TYPE_GROUP, "groups"),
    "group_id": (NODE_TYPE_GROUP, "groups"),
    "roomId": (NODE_TYPE_ROOM, "rooms"),
    "room_id": (NODE_TYPE_ROOM, "rooms"),
    "areaId": (NODE_TYPE_AREA, "areas"),
    "area_id": (NODE_TYPE_AREA, "areas"),
    "houseId": (NODE_TYPE_HOUSE, "houses"),
    "house_id": (NODE_TYPE_HOUSE, "houses"),
    "projectId": (NODE_TYPE_HOUSE, "houses"),
    "project_id": (NODE_TYPE_HOUSE, "houses"),
}


def node_type_collections(node_type: int | None) -> set[str]:
    """Return coordinator topology collections allowed for a node type."""
    if node_type == NODE_TYPE_DEVICE:
        return {"devices", "gateways", "data"}
    if node_type == NODE_TYPE_GROUP:
        return {"groups"}
    if node_type == NODE_TYPE_ROOM:
        return {"rooms"}
    if node_type == NODE_TYPE_AREA:
        return {"areas"}
    if node_type == NODE_TYPE_HOUSE:
        return {"houses"}
    return set()


def selected_candidate_field(update: RuntimePropertyUpdate) -> str | None:
    """Return the field that produced the currently selected node id."""
    for field_name, candidate_id in update.node_id_candidates:
        if candidate_id == update.node_id:
            return field_name
    return None


def candidate_matches_node_type(
    field_name: str | None,
    matched_collections: Sequence[str],
    node_type: int | None,
    *,
    expected_collections: set[str] | None = None,
) -> bool:
    """Return whether an alias is valid for the documented node type."""
    if not matched_collections:
        return False
    if field_name is None or field_name in _NODE_IDENTITY_FIELDS:
        allowed = expected_collections or node_type_collections(node_type)
        return bool(set(matched_collections) & allowed) if allowed else True

    relation = _TOPOLOGY_RELATION_FIELDS.get(str(field_name))
    if relation is None:
        return False
    expected_type, expected_collection = relation
    if node_type != expected_type:
        return False
    return expected_collection in matched_collections


def collection_contains_node(
    collection: Iterable[Mapping[str, Any]],
    node_id: int,
) -> bool:
    """Return whether a topology collection contains a node id."""
    for item in collection:
        if isinstance(item, Mapping) and coerce_device_id(item.get("id")) == node_id:
            return True
    return False


def unknown_update_reason(matched_collections: Sequence[str]) -> str:
    """Classify an unknown update without exposing raw identifiers."""
    if "groups" in matched_collections:
        return "missing_group_node_type"
    if {"rooms", "areas", "houses"} & set(matched_collections):
        return "missing_topology_node_type"
    return "not_loaded"


def safe_param_keys(params: Mapping[str, Any]) -> list[str]:
    """Return sorted param keys only, never param values."""
    keys = sorted(str(key) for key in params)
    return keys[:MAX_RUNTIME_PROPERTY_PARAM_KEYS]


def safe_node_id_candidate_diagnostics(
    candidates: Sequence[tuple[str, int]],
    matching_collections: Callable[[int], list[str]],
) -> dict[str, Any]:
    """Return redacted alternate node-id candidates for unknown update diagnosis."""
    if len(candidates) <= 1:
        return {}
    safe_candidates: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for field_name, node_id in candidates[:MAX_RUNTIME_PROPERTY_SAMPLE_ITEMS]:
        key = (str(field_name), node_id)
        if key in seen:
            continue
        seen.add(key)
        safe_candidates.append(
            {
                "field": str(field_name),
                "node_id_hash": stable_digest(node_id),
                "matched_collections": matching_collections(node_id),
            }
        )
    return {"node_id_candidates": safe_candidates}


def runtime_event_node_id_candidates(
    payload: Mapping[str, Any],
    source_id: int,
) -> tuple[tuple[str, int], ...]:
    """Return event node id aliases in runtime bridge format."""
    raw_candidates = payload.get(ATTR_NODE_ID_CANDIDATES)
    if not isinstance(raw_candidates, Sequence) or isinstance(
        raw_candidates, (str, bytes)
    ):
        return (("source_device_id", source_id),)

    candidates: list[tuple[str, int]] = []
    seen: set[tuple[str, int]] = set()
    for item in raw_candidates:
        if not isinstance(item, Sequence) or isinstance(item, (str, bytes)):
            continue
        if len(item) != 2:
            continue
        field_name = str(item[0])
        candidate_id = coerce_device_id(item[1])
        if candidate_id is None:
            continue
        key = (field_name, candidate_id)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(key)
    if not candidates:
        return (("source_device_id", source_id),)
    return tuple(candidates)


def runtime_event_node_type(payload: Mapping[str, Any]) -> int | None:
    """Return node type carried in safe event attributes."""
    attributes = payload.get(ATTR_EVENT_ATTRIBUTES)
    if not isinstance(attributes, Mapping):
        return None
    return coerce_device_id(attributes.get("node_type"))


def stable_digest(value: Any) -> str:
    """Return a stable non-reversible identifier for diagnostics."""
    digest = blake2b(digest_size=8)
    digest.update(str(value).encode())
    return digest.hexdigest()


def coerce_device_id(value: Any) -> int | None:
    """将事件 source_device_id 转换为运行时设备键。"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


__all__ = [
    "candidate_matches_node_type",
    "coerce_device_id",
    "collection_contains_node",
    "node_type_collections",
    "runtime_event_node_id_candidates",
    "runtime_event_node_type",
    "safe_node_id_candidate_diagnostics",
    "safe_param_keys",
    "selected_candidate_field",
    "stable_digest",
    "unknown_update_reason",
]
