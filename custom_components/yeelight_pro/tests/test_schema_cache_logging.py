"""Product schema cache 日志脱敏测试."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.yeelight_pro.core.schema_cache import ProductSchemaCache


@pytest.mark.asyncio
async def test_cache_force_refresh_failure_log_is_aggregate_only(caplog) -> None:
    """强刷失败日志只能保留聚合数量，不能泄露 PID 或上游详情."""
    cache = ProductSchemaCache()
    cache.update({100: {"pid": 100, "name": "Cached Schema"}})
    fetcher = AsyncMock(
        side_effect=RuntimeError(
            "token=secret-token https://api.yeelight.com/apis/iot/house/12345 "
            "device_id=67890 pid=100"
        )
    )

    with caplog.at_level(logging.WARNING):
        schemas = await cache.async_get_with_fallback(
            [100, 101],
            fetcher,
            force_refresh=True,
        )

    assert schemas == {100: {"pid": 100, "name": "Cached Schema"}}
    assert "Failed to fetch product schemas: RuntimeError" in caplog.text
    assert "using 1 cached schemas, 1 product ids remain without schema" in caplog.text
    _assert_sensitive_details_redacted(caplog.text)
    assert "pid=100" not in caplog.text


@pytest.mark.asyncio
async def test_cache_load_error_log_does_not_expose_sensitive_details(caplog) -> None:
    """缓存加载失败日志不能带出底层异常中的 token、URL 或 ID."""
    hass = MagicMock()
    cache = ProductSchemaCache(hass)
    store = MagicMock()
    store.async_load = AsyncMock(
        side_effect=RuntimeError(
            "token=secret-token https://api.yeelight.com/apis/iot/house/12345 "
            "device_id=67890"
        )
    )
    cache._store = store

    with caplog.at_level(logging.WARNING):
        await cache.async_load()

    assert "Failed to load Yeelight product schema cache: RuntimeError" in caplog.text
    _assert_sensitive_details_redacted(caplog.text)


@pytest.mark.asyncio
async def test_cache_fetch_error_log_does_not_expose_sensitive_details(
    caplog,
) -> None:
    """schema 拉取失败日志不能依赖上游异常已脱敏."""
    cache = ProductSchemaCache()
    cache.update({100: {"pid": 100, "name": "Cached Schema"}})
    fetcher = AsyncMock(
        side_effect=RuntimeError(
            "token=secret-token https://api.yeelight.com/apis/iot/house/12345 "
            "device_id=67890"
        )
    )

    with caplog.at_level(logging.WARNING):
        schemas = await cache.async_get_with_fallback([100, 101], fetcher)

    assert schemas == {100: {"pid": 100, "name": "Cached Schema"}}
    assert "Failed to fetch product schemas: RuntimeError" in caplog.text
    assert "using 1 cached schemas, 1 product ids remain without schema" in caplog.text
    _assert_sensitive_details_redacted(caplog.text)


def _assert_sensitive_details_redacted(log_text: str) -> None:
    """schema cache warning 日志只能包含安全聚合信息."""
    assert "secret-token" not in log_text
    assert "api.yeelight.com" not in log_text
    assert "12345" not in log_text
    assert "67890" not in log_text
