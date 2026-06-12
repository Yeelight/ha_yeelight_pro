"""Property hydration response-shape compatibility tests."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from custom_components.yeelight_pro.core.device_payload import DevicePayloadBuilder
from custom_components.yeelight_pro.core.property_hydration import (
    async_hydrate_device_properties,
)
from custom_components.yeelight_pro.entity_candidates import iter_device_entity_candidates
from custom_components.yeelight_pro.projector.light import project_lights


@pytest.mark.asyncio
async def test_hydration_accepts_list_shaped_multi_node_response() -> None:
    """兼容真实 OpenAPI 可能返回的 resId 行数组结构."""
    client = AsyncMock()
    client.read_nodes_properties.return_value = {
        "code": "200",
        "data": [
            {
                "resId": 311930423,
                "code": "200",
                "data": [
                    {"propId": "dc", "value": False},
                    {"propId": "alm", "value": False},
                    {"propId": "bl", "value": 88},
                ],
            }
        ],
    }

    device = await _hydrated_device(
        client,
        device_id=311930423,
        name="玄关门磁传感器",
    )

    assert device["iot_category"] == "contact_sensor"
    assert _candidate_keys(device) == {
        ("binary_sensor", "door"),
        ("binary_sensor", "tamper"),
        ("sensor", "battery"),
    }
    assert project_lights(device, domain="yeelight_pro") == []


@pytest.mark.asyncio
async def test_hydration_accepts_nested_list_row_multi_node_response() -> None:
    """兼容数组行内 data 再包一层 code/data 的 OpenAPI 结构."""
    client = AsyncMock()
    client.read_nodes_properties.return_value = {
        "code": "200",
        "data": [
            {
                "resId": 311930435,
                "data": {
                    "code": "200",
                    "data": [
                        {"propId": "mv", "value": True},
                        {"propId": "luminance", "value": 188},
                        {"propId": "bl", "value": 92},
                    ],
                },
            }
        ],
    }

    device = await _hydrated_device(
        client,
        device_id=311930435,
        name="厨房人体传感器",
    )

    assert device["iot_category"] == "human_sensor"
    assert _candidate_keys(device) == {
        ("binary_sensor", "motion"),
        ("sensor", "illuminance"),
        ("sensor", "battery"),
    }
    assert project_lights(device, domain="yeelight_pro") == []


async def _hydrated_device(
    client: AsyncMock,
    *,
    device_id: int,
    name: str,
) -> dict:
    """Return one normalized device after read-side hydration."""
    [hydrated] = await async_hydrate_device_properties(
        client,
        house_id=429392,
        devices=[{"id": device_id, "name": name, "category": "light"}],
    )
    data, _gateways = DevicePayloadBuilder().build_runtime_payloads(
        devices=[hydrated],
        gateways=[],
        product_schemas={},
        apply_runtime_overrides=lambda payload: payload,
    )
    return data[device_id]


def _candidate_keys(device: dict) -> set[tuple[str, str | None]]:
    """Return platform/component pairs projected for one device."""
    return {
        (item.platform, item.component_id)
        for item in iter_device_entity_candidates(device)
    }
