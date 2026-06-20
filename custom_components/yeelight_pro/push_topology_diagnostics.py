"""Topology matching helpers for WebSocket push diagnostics."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .push_transport_frames import safe_node_id_hash

_DEVICE_IDENTITY_KEYS = (
    "id",
    "nodeId",
    "node_id",
    "resId",
    "res_id",
    "deviceId",
    "device_id",
)
_GROUP_IDENTITY_KEYS = (*_DEVICE_IDENTITY_KEYS, "groupId", "group_id")
_ROOM_IDENTITY_KEYS = (*_DEVICE_IDENTITY_KEYS, "roomId", "room_id")
_AREA_IDENTITY_KEYS = (*_DEVICE_IDENTITY_KEYS, "areaId", "area_id")
_HOUSE_IDENTITY_KEYS = (
    *_DEVICE_IDENTITY_KEYS,
    "houseId",
    "house_id",
    "projectId",
    "project_id",
)


def push_topology_diagnostics(
    coordinator: Any,
    transport_health: Mapping[str, Any],
) -> dict[str, Any]:
    """Compare redacted push node-id samples with the loaded topology."""
    return {
        **_topology_size_summary(coordinator),
        **_subscribe_topology_match_summary(coordinator, transport_health),
        **_data_payload_topology_match_summary(coordinator, transport_health),
    }


def _subscribe_topology_match_summary(
    coordinator: Any,
    transport_health: Mapping[str, Any],
) -> dict[str, Any]:
    """Compare redacted subscribe snapshot ids with the loaded topology."""
    return _topology_match_summary(
        coordinator,
        transport_health.get("last_subscribe_node_hash_samples"),
        candidate_groups=transport_health.get(
            "last_subscribe_node_candidate_hash_samples"
        ),
        matched_key="last_subscribe_nodes_matching_loaded_topology",
        not_loaded_key="last_subscribe_nodes_not_loaded",
    )


def _data_payload_topology_match_summary(
    coordinator: Any,
    transport_health: Mapping[str, Any],
) -> dict[str, Any]:
    """Compare redacted data-payload ids with the loaded topology."""
    return {
        **_topology_match_summary(
            coordinator,
            transport_health.get("last_data_node_hash_samples"),
            candidate_groups=transport_health.get(
                "last_data_node_candidate_hash_samples"
            ),
            matched_key="last_data_nodes_matching_loaded_topology",
            not_loaded_key="last_data_nodes_not_loaded",
        ),
        **_topology_match_summary(
            coordinator,
            transport_health.get("recent_data_node_hash_samples"),
            candidate_groups=transport_health.get(
                "recent_data_node_candidate_hash_samples"
            ),
            matched_key="recent_data_nodes_matching_loaded_topology",
            not_loaded_key="recent_data_nodes_not_loaded",
        ),
    }


def _topology_match_summary(
    coordinator: Any,
    samples: Any,
    *,
    candidate_groups: Any = None,
    matched_key: str,
    not_loaded_key: str,
) -> dict[str, Any]:
    """Compare redacted node id samples with the loaded topology."""
    normalized_groups = _normalized_hash_groups(candidate_groups)
    if not normalized_groups:
        normalized_groups = _single_hash_groups(samples)
    if not normalized_groups:
        if isinstance(candidate_groups, list) or isinstance(samples, list):
            return {matched_key: 0, not_loaded_key: 0}
        return {}

    topology_hashes = _loaded_topology_node_hashes(coordinator)
    if not topology_hashes:
        return {matched_key: 0, not_loaded_key: len(normalized_groups)}

    matching = sum(
        1 for group in normalized_groups if _group_matches_topology(group, topology_hashes)
    )
    return {
        matched_key: matching,
        not_loaded_key: max(0, len(normalized_groups) - matching),
    }


def _group_matches_topology(
    group: tuple[str, ...],
    topology_hashes: set[str],
) -> bool:
    """Return whether any alias hash in a node sample belongs to loaded topology."""
    return any(sample in topology_hashes for sample in group)


def _single_hash_groups(samples: Any) -> list[tuple[str, ...]]:
    """Return legacy single-hash samples as one-candidate groups."""
    if not isinstance(samples, list):
        return []
    return [(sample,) for sample in samples if isinstance(sample, str) and sample]


def _normalized_hash_groups(candidate_groups: Any) -> list[tuple[str, ...]]:
    """Return diagnostics hash groups from transport health."""
    if not isinstance(candidate_groups, list):
        return []
    groups: list[tuple[str, ...]] = []
    for group in candidate_groups:
        if not isinstance(group, list):
            continue
        hashes = tuple(item for item in group if isinstance(item, str) and item)
        if hashes:
            groups.append(hashes)
    return groups


def _topology_size_summary(coordinator: Any) -> dict[str, int]:
    """Return aggregate topology sample size for push diagnostics."""
    return {
        "loaded_topology_node_hash_count": len(_loaded_topology_node_hashes(coordinator))
    }


def _loaded_topology_node_hashes(coordinator: Any) -> set[str]:
    """Return redacted node id hashes for loaded runtime topology collections."""
    hashes: set[str] = set()
    for attr in ("devices", "gateways", "data"):
        value = getattr(coordinator, attr, None)
        if isinstance(value, Mapping):
            hashes.update(safe_node_id_hash(key) for key in value)
            for item in value.values():
                if isinstance(item, Mapping):
                    _add_topology_node_hashes(hashes, item, _DEVICE_IDENTITY_KEYS)
    for attr, keys in (
        ("groups", _GROUP_IDENTITY_KEYS),
        ("rooms", _ROOM_IDENTITY_KEYS),
        ("areas", _AREA_IDENTITY_KEYS),
        ("houses", _HOUSE_IDENTITY_KEYS),
    ):
        value = getattr(coordinator, attr, None)
        if not isinstance(value, list):
            continue
        for item in value:
            if isinstance(item, Mapping):
                _add_topology_node_hashes(hashes, item, keys)
    return hashes


def _add_topology_node_hashes(
    hashes: set[str],
    item: Mapping[str, Any],
    keys: tuple[str, ...],
) -> None:
    """Add collection-specific node identity aliases to the diagnostics hash pool."""
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            hashes.add(safe_node_id_hash(value))


__all__ = ["push_topology_diagnostics"]
