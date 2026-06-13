"""Shared coordinator test helpers."""
from __future__ import annotations

from unittest.mock import AsyncMock

from custom_components.yeelight_pro.core.client import YeelightProClient


def _client_with_payloads(
    *,
    devices: list[list[dict]],
    product_schemas: dict[int, dict] | None = None,
    areas: list[list[dict]] | None = None,
    rooms: list[dict] | None = None,
    groups: list[dict] | None = None,
    houses: list[dict] | None = None,
    scenes: list[list[dict]] | None = None,
) -> AsyncMock:
    """Build a coordinator client mock with stable auxiliary endpoints."""
    client = AsyncMock(spec=YeelightProClient)
    client.get_devices.side_effect = devices
    client.get_gateways.return_value = []
    client.get_product_schemas.return_value = product_schemas or {}
    client.get_areas.side_effect = areas or [[] for _ in devices]
    client.get_rooms.return_value = rooms or []
    client.get_groups.return_value = groups or []
    client.get_house_snapshot.return_value = {"data": houses or []}
    client.get_scenes.side_effect = scenes or [[] for _ in devices]
    client.read_nodes_properties.return_value = {"code": "200", "data": {}}
    return client


def _lamp_schema(pid: int = 100) -> dict:
    """Build a minimal schema-aware lamp product."""
    return {
        "pid": pid,
        "name": "Schema Lamp Product",
        "category": "light",
        "components": [
            {
                "cid": 4,
                "name": "brightness light",
                "type": 0,
                "category": "light",
                "index": 1,
                "properties": [
                    {"propId": "p", "operators": ["set"]},
                    {"propId": "l", "operators": ["set"]},
                ],
            }
        ],
    }
