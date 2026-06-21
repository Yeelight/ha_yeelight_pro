"""Read-side property hydration tests."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from custom_components.yeelight_pro.core.device_payload import DevicePayloadBuilder
from custom_components.yeelight_pro.core.property_hydration import (
    async_hydrate_device_properties,
)
from custom_components.yeelight_pro.entity_candidates import iter_device_entity_candidates
from custom_components.yeelight_pro.projector.light import project_lights
from custom_components.yeelight_pro.projector.switch import project_switches


@pytest.mark.asyncio
async def test_hydration_reads_missing_sensor_properties_before_projection() -> None:
    """设备列表缺少 properties 时，应补拉属性后生成正确 HA 实体."""
    client = AsyncMock()
    client.read_nodes_properties.return_value = {
        "code": "200",
        "data": {
            "311930423": {
                "code": "200",
                "data": [
                    {"propId": "dc", "value": True},
                    {"propId": "alm", "value": False},
                    {"propId": "bl", "value": 86},
                ],
            },
            "311930425": {
                "code": "200",
                "data": [
                    {"propId": "t", "value": 24.5},
                    {"propId": "h", "value": 58},
                    {"propId": "bl", "value": 90},
                ],
            },
        },
    }

    devices = await async_hydrate_device_properties(
        client,
        house_id=429392,
        devices=[
            {
                "id": 311930423,
                "name": "玄关门磁传感器",
                "category": "light",
                "pid": 301,
            },
            {
                "id": 311930425,
                "name": "客厅温湿度传感器",
                "category": "light",
                "pid": 302,
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
    kwargs = client.read_nodes_properties.await_args.kwargs
    assert kwargs["house_id"] == 429392
    assert kwargs["node_kind"] == "device"
    assert kwargs["resource_ids"] == [311930423, 311930425]
    assert {"dc", "alm", "bl", "t", "h"}.issubset(kwargs["properties"])

    contact_candidates = {
        (item.platform, item.component_id)
        for item in iter_device_entity_candidates(data[311930423])
    }
    temp_candidates = {
        (item.platform, item.component_id)
        for item in iter_device_entity_candidates(data[311930425])
    }

    assert data[311930423]["iot_category"] == "contact_sensor"
    assert contact_candidates == {
        ("binary_sensor", "door"),
        ("binary_sensor", "tamper"),
        ("event", "contact_sensor"),
        ("sensor", "battery"),
    }
    assert data[311930425]["iot_category"] == "other"
    assert temp_candidates == {
        ("sensor", "temperature"),
        ("sensor", "humidity"),
        ("sensor", "battery"),
    }


@pytest.mark.asyncio
async def test_hydration_preserves_existing_property_metadata() -> None:
    """补拉属性值不能丢失列表接口中的属性元数据."""
    client = AsyncMock()
    client.read_nodes_properties.return_value = {
        "code": "200",
        "data": {
            "1": {
                "code": "200",
                "data": [{"propId": "l", "value": 72}],
            }
        },
    }

    [device] = await async_hydrate_device_properties(
        client,
        house_id=1,
        devices=[
            {
                "id": 1,
                "name": "厨房筒灯",
                "category": "light",
                "properties": [
                    {
                        "propId": "l",
                        "desc": "亮度",
                        "format": "uint8",
                        "valueRange": {"min": 1, "max": 100, "step": 1},
                    }
                ],
            }
        ],
    )

    assert device["properties"] == [
        {
            "propId": "l",
            "desc": "亮度",
            "format": "uint8",
            "valueRange": {"min": 1, "max": 100, "step": 1},
            "value": 72,
        }
    ]


@pytest.mark.asyncio
async def test_hydration_preserves_indexed_property_values_for_subdevice_projection() -> None:
    """多节点读取返回 index 时，应生成可投影的 indexed runtime params."""
    client = AsyncMock()
    product_schema = {
        "pid": 901,
        "category": "light",
        "components": [
            {
                "index": 1,
                "category": "light",
                "properties": [
                    {"propId": "p", "operators": ["set"]},
                    {"propId": "l", "operators": ["set"]},
                    {"propId": "ct", "operators": ["set"]},
                ],
            },
            {
                "index": 2,
                "category": "light",
                "properties": [
                    {"propId": "p", "operators": ["set"]},
                    {"propId": "l", "operators": ["set"]},
                    {"propId": "ct", "operators": ["set"]},
                ],
            },
        ],
    }
    client.read_nodes_properties.return_value = {
        "code": "200",
        "data": {
            "9001": {
                "code": "200",
                "data": [
                    {"propId": "p", "index": 1, "value": True},
                    {"propId": "l", "index": 1, "value": 80},
                    {"propId": "ct", "index": 1, "value": 4000},
                    {"propId": "p", "index": 2, "value": False},
                    {"propId": "l", "index": 2, "value": 30},
                    {"propId": "ct", "index": 2, "value": 3300},
                ],
            }
        },
    }

    [hydrated] = await async_hydrate_device_properties(
        client,
        house_id=429392,
        devices=[
            {
                "id": 9001,
                "name": "客厅多路灯",
                "category": "light",
                "pid": 901,
            }
        ],
        product_schemas={901: product_schema},
    )
    data, _gateways = DevicePayloadBuilder().build_runtime_payloads(
        devices=[hydrated],
        gateways=[],
        product_schemas={901: product_schema},
        apply_runtime_overrides=lambda payload: payload,
    )

    device = data[9001]
    lights = project_lights(device, domain="yeelight_pro")

    assert device["params"] == {
        "1-p": True,
        "1-l": 80,
        "1-ct": 4000,
        "2-p": False,
        "2-l": 30,
        "2-ct": 3300,
    }
    assert [light.component_id for light in lights] == ["light_1", "light_2"]
    assert all(light.available for light in lights)
    assert {(item.platform, item.component_id) for item in iter_device_entity_candidates(device)} == {
        ("light", "light_1"),
        ("light", "light_2"),
    }


@pytest.mark.asyncio
async def test_hydration_reads_missing_indexed_subdevice_values() -> None:
    """多路子设备批量读缺路时，应按 index 补读，避免后几路长期 unknown."""
    client = AsyncMock()
    client.read_nodes_properties.return_value = {
        "code": "200",
        "data": {
            "50018395": {
                "code": "200",
                "data": [
                    {"propId": "p", "index": 1, "value": True},
                    {"propId": "sp", "index": 1, "value": True},
                    {"propId": "p", "index": 2, "value": False},
                    {"propId": "sp", "index": 2, "value": False},
                ],
            }
        },
    }
    client.read_node_properties.side_effect = [
        {
            "code": "200",
            "data": [
                {"propId": "p", "value": True},
                {"propId": "sp", "value": True},
            ],
        },
        {
            "code": "200",
            "data": [
                {"propId": "p", "value": False},
                {"propId": "sp", "value": False},
            ],
        },
    ]

    [hydrated] = await async_hydrate_device_properties(
        client,
        house_id=429392,
        devices=[
            {
                "id": 50018395,
                "name": "四键",
                "category": "relay_switch",
                "subDeviceList": [
                    {
                        "index": index,
                        "category": "relay_switch",
                        "properties": [
                            {"propId": "p", "operators": ["set", "toggle"]},
                            {"propId": "sp", "operators": ["set", "toggle"]},
                        ],
                    }
                    for index in range(1, 5)
                ],
            }
        ],
        product_schemas={},
    )
    data, _gateways = DevicePayloadBuilder().build_runtime_payloads(
        devices=[hydrated],
        gateways=[],
        product_schemas={},
        apply_runtime_overrides=lambda payload: payload,
    )
    device = data[50018395]
    switches = project_switches(device, domain="yeelight_pro")

    assert device["params"] == {
        "1-p": True,
        "1-sp": True,
        "2-p": False,
        "2-sp": False,
        "3-p": True,
        "3-sp": True,
        "4-p": False,
        "4-sp": False,
    }
    assert [switch.component_id for switch in switches] == [
        "switch_1",
        "switch_2",
        "switch_3",
        "switch_4",
    ]
    assert [switch.is_on for switch in switches] == [True, False, True, False]
    assert [call.kwargs["index"] for call in client.read_node_properties.await_args_list] == [3, 4]
