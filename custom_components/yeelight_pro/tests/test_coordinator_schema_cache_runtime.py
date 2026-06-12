"""Coordinator product schema cache lifecycle regression tests."""

from __future__ import annotations

import pytest

from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.core.coordinator import YeelightProCoordinator

from .coordinator_helpers import _client_with_payloads, _lamp_schema


@pytest.mark.asyncio
async def test_product_schema_cache_reuses_schema_between_polls(
    hass: HomeAssistant,
) -> None:
    """同一 PID 的产品 schema 不应在每轮轮询重复请求."""
    client = _client_with_payloads(
        devices=[
            [{"id": 1, "name": "Lamp A", "category": "light", "pid": 100}],
            [{"id": 2, "name": "Lamp B", "category": "light", "pid": "100"}],
        ],
        product_schemas={100: _lamp_schema()},
    )
    coordinator = YeelightProCoordinator(hass, client, house_id=12345)

    await coordinator._async_update_data()
    await coordinator._async_update_data()

    client.get_product_schemas.assert_awaited_once_with([100])
    assert coordinator.devices[2]["ha_product_model"]["product"]["model_id"] == "YL-100"


@pytest.mark.asyncio
async def test_coordinator_records_property_hydration_diagnostics(
    hass: HomeAssistant,
) -> None:
    """coordinator 刷新后应保留脱敏补水聚合，方便本地 HA 实测定位."""
    client = _client_with_payloads(
        devices=[
            [{"id": 311930423, "name": "玄关门磁传感器", "category": "light"}],
        ],
    )
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
        },
    }
    coordinator = YeelightProCoordinator(hass, client, house_id=12345)

    await coordinator._async_update_data()

    assert coordinator.property_hydration_diagnostics == {
        "request_groups": 1,
        "requested_devices": 1,
        "requested_property_sets": 37,
        "requested_node_properties": 37,
        "response_devices": 1,
        "response_values": 3,
        "merged_devices": 1,
        "merged_values": 3,
        "empty_response_groups": 0,
        "failed_groups": 0,
    }


@pytest.mark.asyncio
async def test_product_schema_manual_refresh_refetches_cached_schema(
    hass: HomeAssistant,
) -> None:
    """管理员显式强刷时，应重新拉取已缓存 PID 并更新 canonical payload."""
    client = _client_with_payloads(
        devices=[
            [{"id": 1, "name": "Lamp A", "category": "light", "pid": 100}],
            [{"id": 1, "name": "Lamp A", "category": "light", "pid": 100}],
        ],
    )
    fresh_schema = _lamp_schema(100) | {"name": "Fresh Lamp Product"}
    client.get_product_schemas.side_effect = [
        {100: _lamp_schema(100)},
        {100: fresh_schema},
    ]
    coordinator = YeelightProCoordinator(hass, client, house_id=12345)

    await coordinator._async_update_data()
    await coordinator.async_request_product_schema_refresh()

    assert client.get_product_schemas.await_args_list[0].args == ([100],)
    assert client.get_product_schemas.await_args_list[1].args == ([100],)
    assert coordinator.devices[1]["ha_product_model"]["product"]["model_id"] == "YL-100"
    assert coordinator.devices[1]["ha_product_model"]["product"]["model"] == (
        "Fresh Lamp Product"
    )


@pytest.mark.asyncio
async def test_product_schema_manual_refresh_falls_back_to_cached_schema_on_error(
    hass: HomeAssistant,
) -> None:
    """强刷 schema 失败时，应继续使用旧缓存保持实体投影稳定."""
    client = _client_with_payloads(
        devices=[
            [{"id": 1, "name": "Lamp A", "category": "light", "pid": 100}],
            [{"id": 1, "name": "Lamp A", "category": "light", "pid": 100}],
        ],
    )
    client.get_product_schemas.side_effect = [
        {100: _lamp_schema(100)},
        RuntimeError("schema endpoint down"),
    ]
    coordinator = YeelightProCoordinator(hass, client, house_id=12345)

    await coordinator._async_update_data()
    await coordinator.async_request_product_schema_refresh()

    assert client.get_product_schemas.await_args_list[0].args == ([100],)
    assert client.get_product_schemas.await_args_list[1].args == ([100],)
    assert coordinator.devices[1]["product_schema"]["pid"] == 100
    assert coordinator.devices[1]["ha_product_model"]["product"]["model_id"] == "YL-100"


@pytest.mark.asyncio
async def test_product_schema_cache_reuses_persisted_schema_after_restart(
    hass: HomeAssistant,
) -> None:
    """新 coordinator 应从 .storage 缓存恢复 schema，避免重启后重复请求."""
    client = _client_with_payloads(
        devices=[
            [{"id": 1, "name": "Lamp A", "category": "light", "pid": 100}],
        ],
        product_schemas={100: _lamp_schema()},
    )
    first = YeelightProCoordinator(hass, client, house_id=12345)
    await first._async_update_data()
    persisted = first._product_schema_cache.as_storage_data()

    restarted_client = _client_with_payloads(
        devices=[
            [{"id": 2, "name": "Lamp B", "category": "light", "pid": 100}],
        ],
        product_schemas={},
    )
    restarted = YeelightProCoordinator(hass, restarted_client, house_id=12345)
    restarted._product_schema_cache.update(persisted["schemas"])

    data = await restarted._async_update_data()

    restarted_client.get_product_schemas.assert_not_awaited()
    assert data[2]["ha_product_model"]["product"]["model_id"] == "YL-100"


@pytest.mark.asyncio
async def test_product_schema_cache_fetches_only_missing_product_ids(
    hass: HomeAssistant,
) -> None:
    """新增 PID 时只补拉缺失 schema，已缓存 PID 不重复请求."""
    client = _client_with_payloads(
        devices=[
            [{"id": 1, "name": "Lamp A", "category": "light", "pid": 100}],
            [
                {"id": 1, "name": "Lamp A", "category": "light", "pid": 100},
                {"id": 2, "name": "Lamp B", "category": "light", "pid": 101},
            ],
        ],
    )
    client.get_product_schemas.side_effect = [
        {100: _lamp_schema(100)},
        {101: _lamp_schema(101)},
    ]
    coordinator = YeelightProCoordinator(hass, client, house_id=12345)

    await coordinator._async_update_data()
    await coordinator._async_update_data()

    assert client.get_product_schemas.await_args_list[0].args == ([100],)
    assert client.get_product_schemas.await_args_list[1].args == ([101],)
    assert coordinator.devices[1]["ha_product_model"]["product"]["model_id"] == "YL-100"
    assert coordinator.devices[2]["ha_product_model"]["product"]["model_id"] == "YL-101"


@pytest.mark.asyncio
async def test_product_schema_cache_falls_back_to_cached_schema_on_fetch_error(
    hass: HomeAssistant,
) -> None:
    """schema 端点临时失败时，应复用已缓存 schema 保持 canonical payload."""
    client = _client_with_payloads(
        devices=[
            [
                {
                    "id": 1,
                    "name": "Schema Lamp",
                    "category": "light",
                    "pid": 100,
                    "properties": [
                        {"propId": "p", "value": True},
                        {"propId": "l", "value": 25},
                    ],
                }
            ],
            [
                {
                    "id": 1,
                    "name": "Schema Lamp",
                    "category": "light",
                    "pid": 100,
                    "properties": [
                        {"propId": "p", "value": False},
                        {"propId": "l", "value": 80},
                    ],
                },
                {
                    "id": 2,
                    "name": "New Lamp",
                    "category": "light",
                    "pid": 101,
                    "properties": [
                        {"propId": "p", "value": True},
                        {"propId": "l", "value": 40},
                    ],
                },
            ],
        ],
    )
    client.get_product_schemas.side_effect = [
        {100: _lamp_schema()},
        RuntimeError("schema endpoint down"),
    ]
    coordinator = YeelightProCoordinator(hass, client, house_id=12345)

    await coordinator._async_update_data()
    data = await coordinator._async_update_data()

    assert client.get_product_schemas.await_args_list[0].args == ([100],)
    assert client.get_product_schemas.await_args_list[1].args == ([101],)
    cached_device = data[1]
    uncached_device = data[2]
    assert cached_device["product_schema"]["pid"] == 100
    assert cached_device["ha_device_instance"]["components"][0]["state"] == {
        "p": False,
        "l": 80,
    }
    assert "product_schema" not in uncached_device
    assert uncached_device["ha_product_model"]["schema_version"] == "runtime-v1"
    assert uncached_device["ha_device_instance"]["device_info"]["name"] == "New Lamp"
    assert uncached_device["ha_device_instance"]["components"][0]["state"] == {
        "p": True,
        "l": 40,
    }
