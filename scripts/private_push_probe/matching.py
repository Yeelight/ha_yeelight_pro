"""Topology matching helpers for private push probes."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from custom_components.yeelight_pro.core.lan_topology_specs import (  # noqa: E402
    NODE_TYPE_AREA,
    NODE_TYPE_DEVICE,
    NODE_TYPE_GROUP,
    NODE_TYPE_HOUSE,
    NODE_TYPE_ROOM,
)
from custom_components.yeelight_pro.device_filter import (  # noqa: E402
    matches_device_import_filter,
)
from custom_components.yeelight_pro.push_transport_frames import (  # noqa: E402
    safe_node_id_hash,
)
from custom_components.yeelight_pro.utils import to_int  # noqa: E402

from scripts.private_push_probe.io_helpers import digest
from scripts.private_push_probe.models import TopologySnapshot

MAX_SAMPLES = 12
DEVICE_IDENTITY_KEYS = (
    "id",
    "nodeId",
    "node_id",
    "resId",
    "res_id",
    "deviceId",
    "device_id",
)
GROUP_IDENTITY_KEYS = (*DEVICE_IDENTITY_KEYS, "groupId", "group_id")
ROOM_IDENTITY_KEYS = (*DEVICE_IDENTITY_KEYS, "roomId", "room_id")
AREA_IDENTITY_KEYS = (*DEVICE_IDENTITY_KEYS, "areaId", "area_id")
HOUSE_IDENTITY_KEYS = (
    *DEVICE_IDENTITY_KEYS,
    "houseId",
    "house_id",
    "projectId",
    "project_id",
)
NODE_TYPE_COLLECTIONS = {
    NODE_TYPE_DEVICE: {"data", "gateways"},
    NODE_TYPE_GROUP: {"groups"},
    NODE_TYPE_ROOM: {"rooms"},
    NODE_TYPE_AREA: {"areas"},
    NODE_TYPE_HOUSE: {"houses"},
}
COLLECTION_NODE_TYPES = {
    "data": NODE_TYPE_DEVICE,
    "gateways": NODE_TYPE_DEVICE,
    "groups": NODE_TYPE_GROUP,
    "rooms": NODE_TYPE_ROOM,
    "areas": NODE_TYPE_AREA,
    "houses": NODE_TYPE_HOUSE,
}
NODE_IDENTITY_FIELDS = frozenset(DEVICE_IDENTITY_KEYS)
RELATION_FIELDS = {
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
SENSITIVE_FIELD_LABELS = {
    "id": "identity_primary",
    "nodeId": "identity_node",
    "node_id": "identity_node",
    "resId": "identity_resource",
    "res_id": "identity_resource",
    "deviceId": "identity_device",
    "device_id": "identity_device",
    "groupId": "relation_group",
    "group_id": "relation_group",
    "roomId": "relation_room",
    "room_id": "relation_room",
    "areaId": "relation_area",
    "area_id": "relation_area",
    "houseId": "relation_house",
    "house_id": "relation_house",
    "projectId": "relation_house",
    "project_id": "relation_house",
}


def classify_node_candidates(
    *,
    topology: TopologySnapshot,
    node_id: int,
    node_type: int | None,
    params: Mapping[str, Any],
    node_id_candidates: Sequence[tuple[str, int]],
) -> dict[str, Any]:
    """Return diagnostics-safe topology matching facts for one node id group."""
    selected = matching_collections(topology, node_id)
    valid: list[tuple[str, int, list[str]]] = []
    loaded: list[tuple[str, int, list[str]]] = []
    for field_name, candidate_id in node_id_candidates:
        collections = matching_collections(topology, candidate_id)
        if collections:
            loaded.append((field_name, candidate_id, collections))
        if candidate_matches_node_type(field_name, collections, node_type):
            valid.append((field_name, candidate_id, collections))
    matched = bool(valid) or bool(selected)
    sample = {
        "node_id_hash": digest(node_id),
        "node_type": node_type,
        "param_keys": sorted(str(key) for key in params)[:12],
        "selected_collections": selected,
        "candidate_count": len(node_id_candidates),
        "valid_candidate_count": len(valid),
        "loaded_candidate_count": len(loaded),
        "candidate_hashes": [
            {
                "field_label": safe_field_label(field),
                "hash": digest(candidate_id),
                "collections": collections,
            }
            for field, candidate_id, collections in loaded[:MAX_SAMPLES]
        ],
        "maybe_filtered": any(is_filtered_device(topology, item[1]) for item in loaded),
    }
    return {
        "matched": matched,
        "selected_loaded": bool(selected),
        "alias_resolved": bool(not selected and len(valid) == 1 and valid[0][1] != node_id),
        "not_loaded": not matched,
        "maybe_filtered": sample["maybe_filtered"],
        "ambiguous": len(valid) > 1,
        "sample": sample,
    }


def record_hash_group_match(
    counter: Counter[str],
    groups: Sequence[Sequence[str]],
    topology: TopologySnapshot,
) -> None:
    """Record whether redacted node-hash groups are loaded."""
    hashes = loaded_topology_hashes(topology)
    for group in groups:
        key = "matched_loaded_topology" if any(item in hashes for item in group) else "not_loaded"
        counter[key] += 1


def matching_collections(topology: TopologySnapshot, node_id: int) -> list[str]:
    """Return loaded topology collections containing a node id."""
    matches: list[str] = []
    if node_id in topology.data:
        matches.append("data")
    if node_id in topology.gateways:
        matches.append("gateways")
    for name, collection in (
        ("groups", topology.groups),
        ("rooms", topology.rooms),
        ("areas", topology.areas),
        ("houses", topology.houses),
    ):
        if any(to_int(item.get("id")) == node_id for item in collection):
            matches.append(name)
    return matches


def candidate_matches_node_type(
    field_name: str | None,
    matched_collections: Sequence[str],
    node_type: int | None,
) -> bool:
    """Return whether one candidate alias matches the documented node type."""
    if not matched_collections:
        return False
    if field_name is None or field_name in NODE_IDENTITY_FIELDS:
        if node_type is None:
            return True
        expected = NODE_TYPE_COLLECTIONS.get(node_type)
        return bool(set(matched_collections) & expected) if expected else True
    relation = RELATION_FIELDS.get(str(field_name))
    if relation is None:
        return False
    expected_type, expected_collection = relation
    return node_type == expected_type and expected_collection in matched_collections


def is_filtered_device(topology: TopologySnapshot, node_id: int) -> bool:
    """Return whether a loaded device would be excluded by import filtering."""
    payload = topology.data.get(node_id) or topology.gateways.get(node_id)
    if not isinstance(payload, Mapping):
        return False
    return not matches_device_import_filter(payload, topology.filter_config)


def safe_field_label(field_name: str | None) -> str:
    """Return a diagnostics-safe alias label without exposing raw id field names."""
    if field_name is None:
        return "unknown"
    return SENSITIVE_FIELD_LABELS.get(field_name, "other")


def loaded_topology_hashes(topology: TopologySnapshot) -> set[str]:
    """Return redacted node identifier hashes for loaded topology."""
    hashes: set[str] = set()
    for key, item in topology.data.items():
        hashes.add(safe_node_id_hash(key))
        add_hashes(hashes, item, DEVICE_IDENTITY_KEYS)
    for key, item in topology.gateways.items():
        hashes.add(safe_node_id_hash(key))
        add_hashes(hashes, item, DEVICE_IDENTITY_KEYS)
    for collection, keys in (
        (topology.groups, GROUP_IDENTITY_KEYS),
        (topology.rooms, ROOM_IDENTITY_KEYS),
        (topology.areas, AREA_IDENTITY_KEYS),
        (topology.houses, HOUSE_IDENTITY_KEYS),
    ):
        for item in collection:
            add_hashes(hashes, item, keys)
    return hashes


def add_hashes(hashes: set[str], item: Mapping[str, Any], keys: Iterable[str]) -> None:
    """Add redacted identifier hashes from one topology item."""
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            hashes.add(safe_node_id_hash(value))


__all__ = [
    "COLLECTION_NODE_TYPES",
    "classify_node_candidates",
    "loaded_topology_hashes",
    "record_hash_group_match",
    "safe_field_label",
]
