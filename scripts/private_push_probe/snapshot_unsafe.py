"""Unsafe local subscribe-snapshot diagnostics for private push probes."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from custom_components.yeelight_pro.push_transport_private_frames import snapshot_state_keys
from custom_components.yeelight_pro.utils import to_int
from scripts.private_push_probe.models import TopologySnapshot
from scripts.private_push_probe.snapshot_ids import _node_id_candidates, _node_type



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

__all__ = ["_unsafe_item_brief", "_unsafe_subscribe_snapshot_device_detail"]
