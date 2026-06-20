"""Subscribe-snapshot topology diagnostics for private push probes."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from typing import Any

from custom_components.yeelight_pro.push import (  # noqa: E402
    NODE_ID_ALIAS_KEYS,
    TOPOLOGY_NODE_ID_ALIAS_KEYS,
)
from custom_components.yeelight_pro.push_transport_frame_nodes import (  # noqa: E402
    MAX_SAFE_NODE_ID_HASH_SAMPLES,
    safe_node_id_hash,
)
from custom_components.yeelight_pro.push_transport_private_frames import (  # noqa: E402
    private_subscribe_devices,
    snapshot_state_keys,
)
from custom_components.yeelight_pro.utils import to_int  # noqa: E402

from scripts.private_push_probe.matching import classify_node_candidates
from scripts.private_push_probe.models import TopologySnapshot

_IDENTITY_FIELDS = frozenset(NODE_ID_ALIAS_KEYS)


def subscribe_snapshot_samples(
    payload: Mapping[str, Any],
    topology: TopologySnapshot,
) -> list[dict[str, Any]]:
    """Return redacted topology samples for private subscribe snapshot devices."""
    devices = private_subscribe_devices(payload)
    if devices is None:
        return []
    return [
        subscribe_snapshot_device_sample(device, topology)
        for device in devices
        if isinstance(device, Mapping)
    ]


def unsafe_subscribe_snapshot_details(
    payload: Mapping[str, Any],
    topology: TopologySnapshot,
) -> list[dict[str, Any]]:
    """Return local-only raw subscribe snapshot details for manual debugging.

    This function intentionally exposes node ids and display names. It is only
    wired behind the CLI's explicit ``--unsafe-local-details`` flag and must not
    be used by integration diagnostics.
    """
    devices = private_subscribe_devices(payload)
    if devices is None:
        return []
    return [
        _unsafe_subscribe_snapshot_device_detail(index, device, topology)
        for index, device in enumerate(devices)
        if isinstance(device, Mapping)
    ]


def subscribe_snapshot_summary(
    payload: Mapping[str, Any],
    topology: TopologySnapshot,
) -> dict[str, Any]:
    """Return aggregate subscribe-snapshot facts without raw identifiers."""
    devices = private_subscribe_devices(payload)
    if devices is None:
        return {}
    samples = [
        subscribe_snapshot_device_sample(device, topology)
        for device in devices
        if isinstance(device, Mapping)
    ]
    node_types: Counter[str] = Counter()
    state_keys: Counter[str] = Counter()
    selected_collections: Counter[str] = Counter()
    candidate_counts: Counter[str] = Counter()
    valid_candidate_counts: Counter[str] = Counter()
    loaded_candidate_counts: Counter[str] = Counter()
    identity_candidate_rows = 0
    identity_loaded_rows = 0
    relation_only_rows = 0
    for sample in samples:
        node_type = sample.get("node_type")
        node_types[str(node_type) if node_type is not None else "none"] += 1
        for key in sample.get("state_keys", []):
            state_keys[str(key)] += 1
        for collection in sample.get("selected_collections", []):
            selected_collections[str(collection)] += 1
        candidate_counts[str(sample.get("candidate_count", 0))] += 1
        valid_candidate_counts[str(sample.get("valid_candidate_count", 0))] += 1
        loaded_candidate_counts[str(sample.get("loaded_candidate_count", 0))] += 1
        identity_fields = set(sample.get("identity_candidate_fields", []))
        loaded_identity_fields = set(sample.get("loaded_identity_fields", []))
        loaded_relation_fields = set(sample.get("loaded_relation_fields", []))
        if identity_fields:
            identity_candidate_rows += 1
        if loaded_identity_fields:
            identity_loaded_rows += 1
        elif loaded_relation_fields:
            relation_only_rows += 1
    return {
        "device_count": len(samples),
        "state_device_count": sum(1 for sample in samples if sample.get("state_keys")),
        "no_candidate_count": sum(
            1 for sample in samples if sample.get("candidate_count", 0) == 0
        ),
        "selected_loaded_count": sum(
            1 for sample in samples if sample.get("selected_collections")
        ),
        "loaded_candidate_rows": sum(
            1 for sample in samples if sample.get("loaded_candidate_count", 0) > 0
        ),
        "identity_candidate_rows": identity_candidate_rows,
        "identity_loaded_rows": identity_loaded_rows,
        "relation_only_rows": relation_only_rows,
        "rows_without_loaded_candidates": sum(
            1 for sample in samples if sample.get("loaded_candidate_count", 0) == 0
        ),
        "valid_candidate_rows": sum(
            1 for sample in samples if sample.get("valid_candidate_count", 0) > 0
        ),
        "rows_without_valid_candidate": sum(
            1 for sample in samples if sample.get("valid_candidate_count", 0) == 0
        ),
        "maybe_filtered_count": sum(
            1 for sample in samples if sample.get("maybe_filtered")
        ),
        "node_types": dict(sorted(node_types.items())),
        "state_keys": dict(sorted(state_keys.items())),
        "selected_collections": dict(sorted(selected_collections.items())),
        "candidate_counts": dict(sorted(candidate_counts.items())),
        "valid_candidate_counts": dict(sorted(valid_candidate_counts.items())),
        "loaded_candidate_counts": dict(sorted(loaded_candidate_counts.items())),
    }


def subscribe_topology_coverage(
    samples: list[Mapping[str, Any]],
    topology: TopologySnapshot,
    *,
    unsafe_local_details: bool = False,
) -> dict[str, Any]:
    """Return loaded-topology coverage by private subscribe snapshot rows."""
    topology_entries = _topology_entry_map(topology)
    covered = _covered_hashes_by_collection(samples, topology_entries)
    result = {
        "loaded_total": 0,
        "covered_total": 0,
        "uncovered_total": 0,
        "loaded_counts": {},
        "covered_counts": {},
        "uncovered_counts": {},
        "covered_category_counts": {},
        "uncovered_category_counts": {},
        "covered_hash_samples": {},
        "uncovered_hash_samples": {},
    }
    unsafe_uncovered: dict[str, list[dict[str, Any]]] = {}
    for collection, entries in topology_entries.items():
        loaded_hashes = {entry["hash"] for entry in entries}
        covered_hashes = loaded_hashes & covered.get(collection, set())
        uncovered_hashes = loaded_hashes - covered_hashes
        result["loaded_counts"][collection] = len(loaded_hashes)
        result["covered_counts"][collection] = len(covered_hashes)
        result["uncovered_counts"][collection] = len(uncovered_hashes)
        result["loaded_total"] += len(loaded_hashes)
        result["covered_total"] += len(covered_hashes)
        result["uncovered_total"] += len(uncovered_hashes)
        result["covered_category_counts"][collection] = _category_counts(
            entries,
            covered_hashes,
        )
        result["uncovered_category_counts"][collection] = _category_counts(
            entries,
            uncovered_hashes,
        )
        result["covered_hash_samples"][collection] = _hash_samples(covered_hashes)
        result["uncovered_hash_samples"][collection] = _hash_samples(uncovered_hashes)
        if unsafe_local_details and uncovered_hashes:
            unsafe_uncovered[collection] = [
                _unsafe_item_brief(entry["item"])
                for entry in entries
                if entry["hash"] in uncovered_hashes
            ][:MAX_SAFE_NODE_ID_HASH_SAMPLES]
    if unsafe_local_details:
        result["unsafe_uncovered_details"] = unsafe_uncovered
    return result


def subscribe_snapshot_device_sample(
    device: Mapping[str, Any],
    topology: TopologySnapshot,
) -> dict[str, Any]:
    """Return one redacted snapshot-device topology match sample."""
    candidates = _node_id_candidates(device)
    node_type = _node_type(device)
    state_keys = snapshot_state_keys(device)
    if not candidates:
        return {
            "node_id_hash": None,
            "node_type": node_type,
            "state_keys": state_keys,
            "selected_collections": [],
            "candidate_count": 0,
            "valid_candidate_count": 0,
            "loaded_candidate_count": 0,
            "candidate_hashes": [],
            "identity_candidate_fields": [],
            "loaded_identity_fields": [],
            "loaded_relation_fields": [],
            "maybe_filtered": False,
        }
    selected_id = candidates[0][1]
    result = classify_node_candidates(
        topology=topology,
        node_id=selected_id,
        node_type=node_type,
        params={},
        node_id_candidates=candidates,
    )
    sample = dict(result["sample"])
    sample["state_keys"] = state_keys
    _add_candidate_field_groups(sample, candidates)
    return sample


def _unsafe_subscribe_snapshot_device_detail(
    index: int,
    device: Mapping[str, Any],
    topology: TopologySnapshot,
) -> dict[str, Any]:
    """Return one raw local-only subscribe snapshot row with topology matches."""
    candidates = _node_id_candidates(device)
    return {
        "row_index": index,
        "node_type": _node_type(device),
        "state_keys": snapshot_state_keys(device),
        "snapshot": _unsafe_item_brief(device),
        "candidates": [
            {
                "field": field,
                "value": value,
                "matches": _unsafe_topology_matches(topology, value),
            }
            for field, value in candidates
        ],
        "raw_keys": sorted(str(key) for key in device.keys()),
    }


def _unsafe_topology_matches(
    topology: TopologySnapshot,
    node_id: int,
) -> list[dict[str, Any]]:
    """Return raw topology rows matching a node id for local-only reports."""
    matches: list[dict[str, Any]] = []
    for collection, item in _unsafe_topology_items(topology, node_id):
        matches.append({
            "collection": collection,
            **_unsafe_item_brief(item),
        })
    return matches


def _unsafe_topology_items(
    topology: TopologySnapshot,
    node_id: int,
) -> list[tuple[str, Mapping[str, Any]]]:
    """Return matching topology items without redaction for local debugging."""
    items: list[tuple[str, Mapping[str, Any]]] = []
    if node_id in topology.data:
        items.append(("data", topology.data[node_id]))
    if node_id in topology.gateways:
        items.append(("gateways", topology.gateways[node_id]))
    for collection_name, collection in (
        ("groups", topology.groups),
        ("rooms", topology.rooms),
        ("areas", topology.areas),
        ("houses", topology.houses),
    ):
        for item in collection:
            if isinstance(item, Mapping) and to_int(item.get("id")) == node_id:
                items.append((collection_name, item))
    return items


def _unsafe_item_brief(item: Mapping[str, Any]) -> dict[str, Any]:
    """Return useful raw identity fields from one topology row."""
    keys = (
        "id",
        "device_id",
        "deviceId",
        "did",
        "gatewayDeviceId",
        "name",
        "model",
        "category",
        "type",
        "pid",
        "product_id",
        "productId",
        "connectType",
        "valid",
        "isVirtual",
        "roomId",
        "houseId",
    )
    return {
        key: item.get(key)
        for key in keys
        if item.get(key) not in (None, "")
    }


def _add_candidate_field_groups(
    sample: dict[str, Any],
    candidates: tuple[tuple[str, int], ...],
) -> None:
    """Add diagnostics-safe candidate field groups to one sample."""
    identity_fields = _identity_candidate_fields(candidates)
    loaded_fields = {
        str(item.get("field"))
        for item in sample.get("candidate_hashes", [])
        if isinstance(item, Mapping)
    }
    sample["identity_candidate_fields"] = identity_fields
    sample["loaded_identity_fields"] = [
        field for field in identity_fields if field in loaded_fields
    ]
    sample["loaded_relation_fields"] = sorted(
        field for field in loaded_fields if field not in _IDENTITY_FIELDS
    )


def _topology_entry_map(
    topology: TopologySnapshot,
) -> dict[str, list[dict[str, Any]]]:
    """Return topology rows indexed by collection with safe primary hashes."""
    result: dict[str, list[dict[str, Any]]] = {}
    for collection, items in (
        ("data", topology.data),
        ("gateways", topology.gateways),
    ):
        result[collection] = [
            {
                "hash": safe_node_id_hash(node_id),
                "item": item,
                "category": _item_category(item, collection),
            }
            for node_id, item in items.items()
        ]
    for collection, items in (
        ("groups", topology.groups),
        ("rooms", topology.rooms),
        ("areas", topology.areas),
        ("houses", topology.houses),
    ):
        result[collection] = []
        for item in items:
            node_id = to_int(item.get("id")) if isinstance(item, Mapping) else None
            if node_id is None:
                continue
            result[collection].append({
                "hash": safe_node_id_hash(node_id),
                "item": item,
                "category": collection,
            })
    return result


def _covered_hashes_by_collection(
    samples: list[Mapping[str, Any]],
    topology_entries: Mapping[str, list[dict[str, Any]]],
) -> dict[str, set[str]]:
    """Return collection -> covered primary hashes from redacted samples."""
    known_hashes = {
        collection: {entry["hash"] for entry in entries}
        for collection, entries in topology_entries.items()
    }
    covered: dict[str, set[str]] = {collection: set() for collection in topology_entries}
    for sample in samples:
        candidate_hashes = sample.get("candidate_hashes")
        if not isinstance(candidate_hashes, list):
            continue
        for candidate in candidate_hashes:
            if not isinstance(candidate, Mapping):
                continue
            digest = candidate.get("hash")
            collections = candidate.get("collections")
            if not isinstance(digest, str) or not isinstance(collections, list):
                continue
            for collection in collections:
                if not isinstance(collection, str):
                    continue
                if digest in known_hashes.get(collection, set()):
                    covered.setdefault(collection, set()).add(digest)
    return covered


def _category_counts(entries: list[dict[str, Any]], hashes: set[str]) -> dict[str, int]:
    """Return sorted category counts for selected topology hashes."""
    counts: dict[str, int] = {}
    for entry in entries:
        if entry["hash"] not in hashes:
            continue
        category = str(entry["category"] or "unknown")
        counts[category] = counts.get(category, 0) + 1
    return dict(sorted(counts.items()))


def _hash_samples(hashes: set[str]) -> list[str]:
    """Return bounded deterministic hash samples."""
    return sorted(hashes)[:MAX_SAFE_NODE_ID_HASH_SAMPLES]


def _item_category(item: Mapping[str, Any], collection: str) -> str:
    """Return an aggregate-safe category label for one topology item."""
    for key in ("category", "iot_category", "type", "model"):
        value = item.get(key)
        if value not in (None, ""):
            return str(value)
    return collection


def _identity_candidate_fields(candidates: tuple[tuple[str, int], ...]) -> list[str]:
    """Return identity alias fields without values."""
    fields: list[str] = []
    for field, _value in candidates:
        if field in _IDENTITY_FIELDS and field not in fields:
            fields.append(field)
    return fields


def _node_id_candidates(device: Mapping[str, Any]) -> tuple[tuple[str, int], ...]:
    """Return snapshot node id aliases in production parser priority order."""
    candidates: list[tuple[str, int]] = []
    for key in (*NODE_ID_ALIAS_KEYS, *TOPOLOGY_NODE_ID_ALIAS_KEYS):
        node_id = to_int(device.get(key))
        if node_id is not None:
            candidates.append((key, node_id))
    return tuple(candidates)


def _node_type(device: Mapping[str, Any]) -> int | None:
    """Return documented node type aliases from a snapshot row."""
    for key in ("nt", "nodeType", "node_type"):
        node_type = to_int(device.get(key))
        if node_type is not None:
            return node_type
    return None


__all__ = [
    "subscribe_snapshot_device_sample",
    "subscribe_snapshot_samples",
    "subscribe_snapshot_summary",
    "subscribe_topology_coverage",
    "unsafe_subscribe_snapshot_details",
]
