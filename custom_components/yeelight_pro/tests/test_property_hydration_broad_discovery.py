"""Property hydration tests for broad cloud category discovery."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from custom_components.yeelight_pro.core.device_payload import DevicePayloadBuilder
from custom_components.yeelight_pro.core.property_hydration import (
    async_hydrate_device_properties,
)
from custom_components.yeelight_pro.entity_candidates import iter_device_entity_candidates


@pytest.mark.asyncio
async def test_broad_cloud_light_discovers_actual_device_properties() -> None:
    """云端只给粗 light 且无属性时，应读取广谱属性后按真实设备能力投影."""
    client = AsyncMock()
    client.read_nodes_properties.return_value = {
        "code": "200",
        "data": {
            "311930426": {
                "code": "200",
                "data": [
                    {"propId": "mv", "value": True},
                    {"propId": "luminance", "value": 56},
                    {"propId": "bl", "value": 92},
                ],
            },
        },
    }

    devices = await async_hydrate_device_properties(
        client,
        house_id=429392,
        devices=[
            {
                "id": 311930426,
                "name": "设备 311930426",
                "category": "Light",
                "pid": 303,
            },
        ],
        product_schemas={},
    )
    data, _gateways = DevicePayloadBuilder().build_runtime_payloads(
        devices=devices,
        gateways=[],
        product_schemas={},
        apply_runtime_overrides=lambda payload: payload,
    )

    client.read_nodes_properties.assert_awaited_once()
    requested = set(client.read_nodes_properties.await_args.kwargs["properties"])
    assert {"mv", "luminance", "bl", "p", "ct", "cp", "acp"}.issubset(requested)
    device = data[311930426]
    assert device["iot_category"] == "human_sensor"
    assert device["ha_platform_candidates"] == ["binary_sensor", "sensor"]
    assert {
        (item.platform, item.component_id)
        for item in iter_device_entity_candidates(device)
    } == {
        ("binary_sensor", "motion"),
        ("sensor", "illuminance"),
        ("sensor", "battery"),
    }


@pytest.mark.asyncio
async def test_broad_discovery_does_not_read_generic_power_for_cover_or_climate() -> None:
    """窗帘/温控不能靠泛化 p 属性生成 switch 候选."""
    client = AsyncMock()
    client.read_nodes_properties.return_value = {"code": "200", "data": {}}

    await async_hydrate_device_properties(
        client,
        house_id=429392,
        devices=[
            {"id": 1, "name": "客厅窗帘电机", "category": "relay_switch", "pid": 11},
            {"id": 2, "name": "次卧温控器", "category": "relay_switch", "pid": 12},
        ],
        product_schemas={
            11: _relay_switch_schema(11),
            12: _relay_switch_schema(12),
        },
    )

    calls = {
        tuple(call.kwargs["resource_ids"]): set(call.kwargs["properties"])
        for call in client.read_nodes_properties.await_args_list
    }

    assert "p" not in calls[(1,)]
    assert {"cp", "tp"}.issubset(calls[(1,)])
    assert "p" not in calls[(2,)]
    assert {"acp", "aco", "actt", "acct"}.issubset(calls[(2,)])


def _relay_switch_schema(pid: int) -> dict:
    return {
        "pid": pid,
        "category": "relay_switch",
        "components": [
            {
                "category": "relay_switch",
                "properties": [{"propId": "p"}, {"propId": "sp"}],
            }
        ],
    }
