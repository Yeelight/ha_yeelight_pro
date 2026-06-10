"""Coordinator schema-aware canonical and cache regression tests."""
from __future__ import annotations

import pytest

from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.core.coordinator import YeelightProCoordinator

from .coordinator_helpers import _client_with_payloads, _lamp_schema


@pytest.mark.asyncio
async def test_update_data_attaches_schema_aware_canonical_models(
    hass: HomeAssistant,
) -> None:
    """真实轮询链路应把官方 schema 转成 projector 可消费的规范模型."""
    client = _client_with_payloads(
        devices=[
            [
                {
                    "id": 1,
                    "name": "Schema Lamp",
                    "category": "light",
                    "pid": 100,
                    "properties": [
                        {"propId": "o", "value": True},
                        {"propId": "p", "value": True},
                        {"propId": "l", "value": 25},
                    ],
                }
            ]
        ],
        product_schemas={100: _lamp_schema()},
    )
    coordinator = YeelightProCoordinator(hass, client, house_id=12345)

    data = await coordinator._async_update_data()
    device = data[1]

    assert device["ha_product_model"]["product"]["model_id"] == "YL-100"
    assert device["ha_device_instance"]["product_ref"] == {"model_id": "YL-100"}
    device_info = device["ha_device_instance"]["device_info"]
    assert device_info["identifiers"] == [
        ["yeelight_pro", "1"],
        ["yeelight_pro", "device:1"],
    ]
    assert device_info["name"] == "Schema Lamp"
    assert device_info["model"] == "Schema Lamp Product"
    assert device["ha_device_instance"]["components"] == [
        {
            "component_id": "light",
            "component_type": "custom",
            "category": "light",
            "available": True,
            "instance_capabilities": None,
            "state": {"p": True, "l": 25},
        }
    ]


@pytest.mark.asyncio
async def test_runtime_overrides_update_schema_aware_canonical_state(
    hass: HomeAssistant,
) -> None:
    """乐观控制状态应同步进入 ha_device_instance，避免实体读到旧值."""
    client = _client_with_payloads(
        devices=[
            [
                {
                    "id": 1,
                    "name": "Schema Lamp",
                    "category": "light",
                    "pid": 100,
                    "properties": [
                        {"propId": "o", "value": True},
                        {"propId": "p", "value": False},
                        {"propId": "l", "value": 25},
                    ],
                }
            ]
        ],
        product_schemas={100: _lamp_schema()},
    )
    coordinator = YeelightProCoordinator(hass, client, house_id=12345)
    coordinator._runtime_state.store_update(
        1,
        {"p": True, "l": 80},
        devices={},
        gateways={},
        data={},
        rebuild_canonical=lambda _device: None,
    )

    data = await coordinator._async_update_data()
    device = data[1]

    assert device["params"] == {"p": True, "l": 80}
    assert device["ha_device_instance"]["components"][0]["state"] == {
        "p": True,
        "l": 80,
    }


@pytest.mark.asyncio
async def test_update_data_infers_device_info_when_product_schema_missing(
    hass: HomeAssistant,
) -> None:
    """无官方 schema 的真实轮询设备也必须进入 HA device registry。"""
    client = _client_with_payloads(
        devices=[
            [
                {
                    "id": 304784333,
                    "name": "客厅筒灯 1",
                    "category": "light",
                    "pid": 200,
                    "roomId": 397,
                    "properties": [
                        {"propId": "p", "value": True},
                        {"propId": "l", "value": 80},
                    ],
                }
            ]
        ],
        product_schemas={},
        rooms=[{"id": "397", "name": "客厅"}],
    )
    coordinator = YeelightProCoordinator(hass, client, house_id=12345)

    data = await coordinator._async_update_data()
    device = data[304784333]

    assert device["ha_product_model"]["schema_version"] == "runtime-v1"
    assert device["ha_device_instance"]["device_info"]["identifiers"] == [
        ["yeelight_pro", "304784333"],
        ["yeelight_pro", "device:304784333"],
    ]
    assert device["ha_device_instance"]["device_info"]["name"] == "客厅筒灯 1"
    assert device["ha_device_instance"]["device_info"]["suggested_area"] == "客厅"
