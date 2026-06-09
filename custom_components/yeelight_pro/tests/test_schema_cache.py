"""Product schema cache tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.yeelight_pro.core.schema_cache import (
    ProductSchemaCache,
    normalize_product_ids,
    product_ids_from_items,
)


def test_normalize_product_ids_keeps_order_and_deduplicates() -> None:
    """PID 归一化应兼容字符串并保持稳定顺序."""
    assert normalize_product_ids([100, "101", 100, None, "", "bad", 102]) == [
        100,
        101,
        102,
    ]


def test_product_ids_from_items_ignores_invalid_payloads() -> None:
    """设备/网关载荷中的无效 PID 不应进入 schema 请求."""
    assert product_ids_from_items([
        {"pid": "100"},
        {"productId": 101},
        {"product_id": "102"},
        {"productKey": 103},
        {"pid": "bad"},
        {"name": "no pid"},
    ]) == [100, 101, 102, 103]


def test_cache_returns_deep_copies() -> None:
    """调用方修改返回值不能污染缓存."""
    cache = ProductSchemaCache()
    cache.update({100: {"pid": 100, "components": [{"name": "light"}]}})

    first = cache.get_many([100])
    first[100]["components"][0]["name"] = "changed"

    assert cache.get_many([100])[100]["components"][0]["name"] == "light"


def test_cache_uses_schema_pid_when_map_key_is_not_numeric() -> None:
    """远端返回 key 不稳定时可回退到 schema 内 pid 字段."""
    cache = ProductSchemaCache()

    cache.update({"bad-key": {"productId": "100", "name": "Schema"}})

    assert cache.size == 1
    assert cache.get_many([100])[100]["name"] == "Schema"


def test_cache_storage_data_contains_only_schema_map() -> None:
    """持久缓存只能保存产品 schema map，不能混入设备或用户上下文."""
    cache = ProductSchemaCache()
    cache.update({100: {"pid": 100, "components": [{"name": "light"}]}})

    storage_data = cache.as_storage_data()

    assert storage_data == {
        "schemas": {
            "100": {
                "pid": 100,
                "components": [{"name": "light"}],
            }
        }
    }
    assert "devices" not in storage_data
    assert "house_id" not in storage_data
    assert "access_token" not in storage_data


def test_cache_storage_data_keeps_json_safe_schema_values_only() -> None:
    """持久缓存应只输出 JSON-safe schema 值，避免 .storage 写入失败."""
    cache = ProductSchemaCache()
    cache.update({
        100: {
            "pid": 100,
            "name": "Safe Schema",
            "components": [
                {"name": "light", "properties": [{"propId": "l"}]},
                {"bad": object(), "kept": True},
            ],
            "bad_object": object(),
            "bad_set": {"not-json"},
        },
        101: {},
        "bad-key": {"name": "No PID"},
    })

    assert cache.as_storage_data() == {
        "schemas": {
            "100": {
                "pid": 100,
                "name": "Safe Schema",
                "components": [
                    {"name": "light", "properties": [{"propId": "l"}]},
                    {"kept": True},
                ],
            }
        }
    }


def test_cache_storage_data_drops_sensitive_runtime_context() -> None:
    """持久缓存不能把账号、家庭、设备、房间或原始载荷上下文写入 .storage."""
    cache = ProductSchemaCache()
    cache.update({
        100: {
            "pid": 100,
            "name": "Safe Schema",
            "description": "Device supports wall switch mode.",
            "accessToken": "secret-token",
            "houseId": "house-secret",
            "roomName": "private room",
            "macAddress": "AA:BB:CC:DD:EE:FF",
            "rawPayload": {"device_id": "device-secret", "kept": False},
            "components": [
                {
                    "name": "light",
                    "properties": [{"propId": "l", "token": "nested-secret"}],
                    "notes": "device_id=device-secret",
                },
                {
                    "name": "switch",
                    "properties": [{"propId": "p", "description": "Power"}],
                },
            ],
            "metadata": {
                "authorization": "Bearer abc.def",
                "display": "Ordinary product metadata",
            },
        }
    })

    assert cache.as_storage_data() == {
        "schemas": {
            "100": {
                "pid": 100,
                "name": "Safe Schema",
                "description": "Device supports wall switch mode.",
                "components": [
                    {
                        "name": "light",
                        "properties": [{"propId": "l"}],
                    },
                    {
                        "name": "switch",
                        "properties": [{"propId": "p", "description": "Power"}],
                    },
                ],
                "metadata": {"display": "Ordinary product metadata"},
            }
        }
    }


@pytest.mark.asyncio
async def test_cache_loads_persisted_schema_and_skips_fetcher() -> None:
    """重启后已有持久 schema 时，不应重复请求远端 schema 端点."""
    hass = MagicMock()
    cache = ProductSchemaCache(hass)
    store = MagicMock()
    store.async_load = AsyncMock(return_value={
        "schemas": {
            "100": {"pid": 100, "name": "Persisted Schema"},
        }
    })
    cache._store = store
    fetcher = AsyncMock(return_value={})

    schemas = await cache.async_get([100], fetcher)

    assert schemas[100]["name"] == "Persisted Schema"
    fetcher.assert_not_awaited()
    store.async_delay_save.assert_not_called()


@pytest.mark.asyncio
async def test_cache_schedules_save_after_fetching_missing_schema() -> None:
    """远端补齐缺失 schema 后，应延迟写入 .storage."""
    hass = MagicMock()
    cache = ProductSchemaCache(hass)
    store = MagicMock()
    store.async_load = AsyncMock(return_value={"schemas": {}})
    cache._store = store
    fetcher = AsyncMock(return_value={100: {"pid": 100, "name": "Fetched Schema"}})

    schemas = await cache.async_get([100], fetcher)

    assert schemas[100]["name"] == "Fetched Schema"
    fetcher.assert_awaited_once_with([100])
    store.async_delay_save.assert_called_once()


@pytest.mark.asyncio
async def test_cache_force_refresh_refetches_cached_schema() -> None:
    """手动强制刷新应重新请求已缓存 PID，并更新缓存副本."""
    cache = ProductSchemaCache()
    cache.update({100: {"pid": 100, "name": "Cached Schema"}})
    fetcher = AsyncMock(return_value={100: {"pid": 100, "name": "Fresh Schema"}})

    schemas = await cache.async_get([100], fetcher, force_refresh=True)

    fetcher.assert_awaited_once_with([100])
    assert schemas == {100: {"pid": 100, "name": "Fresh Schema"}}
    assert cache.get_many([100]) == {100: {"pid": 100, "name": "Fresh Schema"}}


@pytest.mark.asyncio
async def test_cache_force_refresh_failure_falls_back_to_cached_schema() -> None:
    """强制刷新失败时仍应保留并返回旧缓存，避免投影退化."""
    cache = ProductSchemaCache()
    cache.update({100: {"pid": 100, "name": "Cached Schema"}})
    fetcher = AsyncMock(side_effect=RuntimeError("schema endpoint down"))

    schemas = await cache.async_get_with_fallback(
        [100],
        fetcher,
        force_refresh=True,
    )

    fetcher.assert_awaited_once_with([100])
    assert schemas == {100: {"pid": 100, "name": "Cached Schema"}}

