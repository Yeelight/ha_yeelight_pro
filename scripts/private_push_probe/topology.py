"""Topology loading and matching for the private push probe."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import aiohttp

from custom_components.yeelight_pro.const import (  # noqa: E402
    CONF_DEVICE_IMPORT_FILTER,
    CONF_HOUSE_ID,
    CONF_OPEN_API_CLIENT_ID,
    CONF_PRIVATE_DOMAIN,
)
from custom_components.yeelight_pro.core.client import YeelightProClient  # noqa: E402
from custom_components.yeelight_pro.core.device_payload import (  # noqa: E402
    DevicePayloadBuilder,
)
from custom_components.yeelight_pro.core.lan_topology_specs import (  # noqa: E402
    NODE_TYPE_DEVICE,
)
from custom_components.yeelight_pro.core.property_hydration import (  # noqa: E402
    async_hydrate_device_properties,
)
from custom_components.yeelight_pro.core.property_hydration_summary import (  # noqa: E402
    PropertyHydrationDiagnostics,
)
from custom_components.yeelight_pro.core.schema_cache import (  # noqa: E402
    product_ids_from_items,
)
from custom_components.yeelight_pro.identity import (  # noqa: E402
    apply_identity_scope_to_device_maps,
)
from custom_components.yeelight_pro.deployment_urls import (  # noqa: E402
    deployment_iot_base_url,
)
from custom_components.yeelight_pro.push import push_property_updates  # noqa: E402
from custom_components.yeelight_pro.utils import to_int  # noqa: E402

from scripts.private_push_probe.models import TopologySnapshot
from scripts.private_push_probe.io_helpers import (
    safe_house_rows,
    safe_list,
    safe_mapping,
)
from scripts.private_house_audit.schema_cache import (
    cached_product_schemas,
    merge_product_schemas,
)
from scripts.private_push_probe.matching import (
    COLLECTION_NODE_TYPES,
    classify_node_candidates,
    loaded_topology_hashes,
)


@dataclass(frozen=True, slots=True)
class SyntheticPropertyUpdate:
    """Synthetic update used to verify the probe's topology matcher."""

    node_id: int
    node_type: int | None
    params: Mapping[str, Any]
    node_id_candidates: tuple[tuple[str, int], ...]


async def fetch_topology(
    session: aiohttp.ClientSession,
    entry_data: Mapping[str, Any],
    entry_options: Mapping[str, Any],
    *,
    config_dir: Path | None = None,
) -> TopologySnapshot:
    """Fetch the current Open API topology using production helpers."""
    house_id = int(entry_data[CONF_HOUSE_ID])
    client = YeelightProClient(
        domain=deployment_iot_base_url(entry_data.get(CONF_PRIVATE_DOMAIN)),
        access_token=str(entry_data.get("access_token") or ""),
        client_id=str(entry_data.get(CONF_OPEN_API_CLIENT_ID) or ""),
        session=session,
    )
    errors: dict[str, str] = {}
    devices = await safe_list("devices", client.get_devices(house_id), errors)
    gateways = await safe_list("gateways", client.get_gateways(house_id), errors)
    cached_schemas = cached_product_schemas(config_dir) if config_dir is not None else {}
    schemas = merge_product_schemas(
        cached_schemas,
        await safe_mapping(
            "product_schemas",
            client.get_product_schemas(product_ids_from_items([*devices, *gateways])),
            errors,
        ),
    )
    hydration = PropertyHydrationDiagnostics()
    hydrated = await async_hydrate_device_properties(
        client,
        house_id=house_id,
        devices=devices,
        product_schemas=schemas,
        diagnostics=hydration,
    )
    areas, rooms, groups, houses = await __import__("asyncio").gather(
        safe_list("areas", client.get_areas(house_id), errors),
        safe_list("rooms", client.get_rooms(house_id), errors),
        safe_list("groups", client.get_groups(house_id), errors),
        safe_house_rows(client, house_id, errors),
    )
    data, gateway_data = DevicePayloadBuilder().build_runtime_payloads(
        devices=hydrated,
        gateways=gateways,
        product_schemas=schemas,
        apply_runtime_overrides=lambda payload: payload,
        rooms=rooms,
        areas=areas,
    )
    apply_identity_scope_to_device_maps(
        entry_data=entry_data,
        house_id=house_id,
        devices=data,
        gateways=gateway_data,
    )
    snapshot = TopologySnapshot(
        data=data,
        gateways=gateway_data,
        groups=groups,
        rooms=rooms,
        areas=areas,
        houses=houses,
        filter_config=entry_options.get(CONF_DEVICE_IMPORT_FILTER),
        hydration=hydration.as_dict(),
        endpoint_errors=errors,
    )
    snapshot.hash_count = len(loaded_topology_hashes(snapshot))
    return snapshot


def classify_update(update: Any, topology: TopologySnapshot) -> dict[str, Any]:
    """Return diagnostics-safe topology matching facts for one property update."""
    return classify_node_candidates(
        topology=topology,
        node_id=update.node_id,
        node_type=update.node_type,
        params=update.params,
        node_id_candidates=update.node_id_candidates,
    )


def topology_self_check(topology: TopologySnapshot) -> dict[str, Any]:
    """Return whether a synthetic push payload can match loaded topology."""
    node_id = next(iter(topology.data), None)
    if node_id is None:
        node_id = next(iter(topology.gateways), None)
    if node_id is None:
        return {
            "available": False,
            "matched": False,
            "reason": "no_loaded_device_nodes",
        }
    payload_matches = [
        classify_update(update, topology)
        for update in push_property_updates(
            {
                "type": "prop",
                "nodes": [
                    {
                        "id": int(node_id),
                        "nt": NODE_TYPE_DEVICE,
                        "params": {"p": True},
                    }
                ],
            }
        )
    ]
    result = classify_update(
        SyntheticPropertyUpdate(
            node_id=int(node_id),
            node_type=NODE_TYPE_DEVICE,
            params={"p": True},
            node_id_candidates=(("id", int(node_id)),),
        ),
        topology,
    )
    return {
        "available": True,
        "matched": bool(result["matched"]),
        "synthetic_payload_matched": bool(
            payload_matches and payload_matches[0]["matched"]
        ),
        "selected_loaded": bool(result["selected_loaded"]),
        "maybe_filtered": bool(result["maybe_filtered"]),
        "synthetic_payload_maybe_filtered": bool(
            payload_matches and payload_matches[0]["maybe_filtered"]
        ),
        "sample": result["sample"],
        "synthetic_payload_sample": (
            payload_matches[0]["sample"] if payload_matches else None
        ),
    }


def topology_payload_coverage(topology: TopologySnapshot) -> dict[str, Any]:
    """Check every loaded topology id through the push parser and matcher."""
    rows = list(iter_topology_rows(topology))
    if not rows:
        return {
            "available": False,
            "total_nodes": 0,
            "matched_nodes": 0,
            "not_loaded_nodes": 0,
            "maybe_filtered_nodes": 0,
            "parse_failures": 0,
            "by_collection": {},
        }

    result: dict[str, Any] = {
        "available": True,
        "total_nodes": len(rows),
        "matched_nodes": 0,
        "not_loaded_nodes": 0,
        "maybe_filtered_nodes": 0,
        "parse_failures": 0,
        "by_collection": {},
    }
    by_collection: dict[str, dict[str, int]] = {}
    for collection, node_id, node_type in rows:
        collection_result = by_collection.setdefault(
            collection,
            {
                "total_nodes": 0,
                "matched_nodes": 0,
                "not_loaded_nodes": 0,
                "maybe_filtered_nodes": 0,
                "parse_failures": 0,
            },
        )
        collection_result["total_nodes"] += 1
        updates = push_property_updates(
            {
                "type": "prop",
                "nodes": [
                    {
                        "id": node_id,
                        "nt": node_type,
                        "params": {"p": True},
                    }
                ],
            }
        )
        if not updates:
            result["parse_failures"] += 1
            collection_result["parse_failures"] += 1
            continue
        match = classify_update(updates[0], topology)
        for field, key in (
            ("matched", "matched_nodes"),
            ("not_loaded", "not_loaded_nodes"),
            ("maybe_filtered", "maybe_filtered_nodes"),
        ):
            if match[field]:
                result[key] += 1
                collection_result[key] += 1
    result["by_collection"] = dict(sorted(by_collection.items()))
    return result


def iter_topology_rows(topology: TopologySnapshot) -> Iterable[tuple[str, int, int]]:
    """Yield loaded topology rows as collection, node id, and documented node type."""
    for collection_name, node_map in (
        ("data", topology.data),
        ("gateways", topology.gateways),
    ):
        node_type = COLLECTION_NODE_TYPES[collection_name]
        for node_id in node_map:
            yield collection_name, int(node_id), node_type
    for collection_name, node_rows in (
        ("groups", topology.groups),
        ("rooms", topology.rooms),
        ("areas", topology.areas),
        ("houses", topology.houses),
    ):
        node_type = COLLECTION_NODE_TYPES[collection_name]
        for row in node_rows:
            if not isinstance(row, Mapping):
                continue
            topology_node_id = to_int(row.get("id"))
            if topology_node_id is None:
                continue
            yield collection_name, topology_node_id, node_type
