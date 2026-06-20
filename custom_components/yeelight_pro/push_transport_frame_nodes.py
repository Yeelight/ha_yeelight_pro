"""Node-id hash sampling helpers for Yeelight Pro push frames."""

from __future__ import annotations

from collections.abc import Mapping
from hashlib import blake2b
from typing import Any

from .core.lan_topology_specs import (
    NODE_TYPE_AREA,
    NODE_TYPE_GROUP,
    NODE_TYPE_HOUSE,
    NODE_TYPE_ROOM,
)
from .lan_methods import (
    METHOD_DEVICE_POST_EVENT,
    METHOD_DEVICE_POST_PROP,
    METHOD_POST_EVENT,
    METHOD_POST_PROP,
)
from .push_contract import PUSH_DATA_TYPES

MAX_SAFE_NODE_ID_HASH_SAMPLES = 10
NODE_ID_ALIAS_KEYS = (
    "id",
    "nodeId",
    "node_id",
    "resId",
    "res_id",
    "deviceId",
    "device_id",
)
TOPOLOGY_NODE_ID_FIELDS_BY_TYPE = {
    NODE_TYPE_GROUP: ("groupId", "group_id"),
    NODE_TYPE_ROOM: ("roomId", "room_id"),
    NODE_TYPE_AREA: ("areaId", "area_id"),
    NODE_TYPE_HOUSE: ("houseId", "house_id", "projectId", "project_id"),
}


def data_frame_node_hash_samples(
    candidates: list[Mapping[str, Any]],
) -> list[str]:
    """Return redacted node-id hashes from payload candidates."""
    return [group[0] for group in data_frame_node_candidate_hash_samples(candidates) if group]


def data_frame_node_candidate_hash_samples(
    candidates: list[Mapping[str, Any]],
) -> list[list[str]]:
    """Return redacted data-frame node-id alias hash groups."""
    candidate_groups: list[list[str]] = []
    for candidate in candidates:
        extend_node_hash_sample_groups(candidate_groups, candidate)
        if len(candidate_groups) >= MAX_SAFE_NODE_ID_HASH_SAMPLES:
            break
    return candidate_groups


def extend_node_hash_sample_groups(
    samples: list[list[str]],
    payload: Mapping[str, Any],
) -> None:
    """Append data-frame node alias hash groups without exposing raw identifiers."""
    method = payload.get("method")
    if method in {METHOD_POST_PROP, METHOD_POST_EVENT, METHOD_DEVICE_POST_PROP}:
        extend_node_list_hash_sample_groups(samples, payload.get("nodes"))
        return
    if method == METHOD_DEVICE_POST_EVENT:
        params = payload.get("params")
        if isinstance(params, Mapping):
            append_node_hash_sample_group(samples, node_id_hash_group(params))
        return

    if payload.get("type") not in PUSH_DATA_TYPES:
        return
    nodes = payload.get("nodes")
    if isinstance(nodes, list):
        extend_node_list_hash_sample_groups(samples, nodes)
        return
    append_node_hash_sample_group(samples, node_id_hash_group(payload))


def extend_node_list_hash_sample_groups(
    samples: list[list[str]],
    nodes: object,
) -> None:
    """Append node hash groups from a documented nodes array."""
    if not isinstance(nodes, list):
        return
    for node in nodes:
        if not isinstance(node, Mapping):
            continue
        append_node_hash_sample_group(samples, node_id_hash_group(node))
        if len(samples) >= MAX_SAFE_NODE_ID_HASH_SAMPLES:
            return


def append_node_hash_sample_group(
    samples: list[list[str]],
    group: list[str],
) -> None:
    """Append one unique non-empty hash group."""
    if not group:
        return
    if group not in samples:
        samples.append(group)


def node_id_hash_group(payload: Mapping[str, Any]) -> list[str]:
    """Return all documented node-id alias hashes for one node object."""
    samples: list[str] = []
    for key in (*NODE_ID_ALIAS_KEYS, *topology_node_id_keys(payload)):
        value = payload.get(key)
        if value in (None, ""):
            continue
        digest = safe_node_id_hash(value)
        if digest not in samples:
            samples.append(digest)
    return samples


def topology_node_id_keys(payload: Mapping[str, Any]) -> tuple[str, ...]:
    """Return relation-id fields only when node_type declares a topology node."""
    for key in ("nt", "nodeType", "node_type"):
        try:
            node_type = int(payload.get(key)) # pyright: ignore[reportArgumentType]
        except (TypeError, ValueError):
            continue
        return TOPOLOGY_NODE_ID_FIELDS_BY_TYPE.get(node_type, ())
    return ()


def safe_node_id_hash(value: object) -> str:
    """Return a stable non-reversible node identifier for diagnostics."""
    digest = blake2b(digest_size=8)
    digest.update(str(value).encode())
    return digest.hexdigest()


__all__ = [
    "MAX_SAFE_NODE_ID_HASH_SAMPLES",
    "append_node_hash_sample_group",
    "data_frame_node_candidate_hash_samples",
    "data_frame_node_hash_samples",
    "extend_node_hash_sample_groups",
    "extend_node_list_hash_sample_groups",
    "node_id_hash_group",
    "safe_node_id_hash",
    "topology_node_id_keys",
]
