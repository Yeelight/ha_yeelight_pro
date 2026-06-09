"""Analytics refresh service tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from homeassistant.auth.const import GROUP_ID_USER
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import ServiceValidationError, Unauthorized

from custom_components.yeelight_pro.analytics_runtime import AnalyticsSnapshot
from custom_components.yeelight_pro.analytics_service import (
    ATTR_DATE_CODE,
    ATTR_ENDPOINT,
    ERROR_ANALYTICS_DISABLED,
    SERVICE_REFRESH_ANALYTICS,
    async_register_analytics_service,
)
from custom_components.yeelight_pro.const import DOMAIN


@pytest.mark.asyncio
async def test_refresh_analytics_service_rejects_disabled_entry(
    hass: HomeAssistant,
) -> None:
    """未显式启用 analytics runtime 时服务必须失败且不调用云端。"""
    coordinator = SimpleNamespace(
        analytics_runtime_enabled=False,
        async_refresh_analytics=AsyncMock(),
    )
    hass.data[DOMAIN] = {"entry-1": {"coordinator": coordinator}}

    async_register_analytics_service(hass)
    with pytest.raises(ServiceValidationError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_REFRESH_ANALYTICS,
            {"entry_id": "entry-1", ATTR_ENDPOINT: "energy_analyse", ATTR_DATE_CODE: "2024-08"},
            blocking=True,
            return_response=True,
        )

    assert ERROR_ANALYTICS_DISABLED in str(exc_info.value)
    coordinator.async_refresh_analytics.assert_not_awaited()


@pytest.mark.asyncio
async def test_refresh_analytics_service_returns_redacted_aggregate_response(
    hass: HomeAssistant,
) -> None:
    """刷新服务只返回聚合结果，不暴露 raw payload。"""
    coordinator = SimpleNamespace(
        analytics_runtime_enabled=True,
        async_refresh_analytics=AsyncMock(
            return_value=AnalyticsSnapshot(
                endpoint_key="energy_analyse",
                refreshed_at="2026-06-09T00:00:00+00:00",
                sample_count=1,
                energy_used_kwh=3.5,
            )
        ),
    )
    hass.data[DOMAIN] = {"entry-1": {"coordinator": coordinator}}

    async_register_analytics_service(hass)
    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_REFRESH_ANALYTICS,
        {
            "entry_id": "entry-1",
            ATTR_ENDPOINT: "energy_analyse",
            ATTR_DATE_CODE: "2024-08",
        },
        blocking=True,
        return_response=True,
    )

    assert response == {
        "action": "refresh_analytics",
        "refreshed_entries": 1,
        "entries": [
            {
                "entry_id": "entry-1",
                "endpoint_key": "energy_analyse",
                "refreshed_at": "2026-06-09T00:00:00+00:00",
                "sample_count": 1,
                "energy_used_kwh": 3.5,
            }
        ],
    }
    coordinator.async_refresh_analytics.assert_awaited_once_with(
        endpoint_key="energy_analyse",
        date_code="2024-08",
        start_date=None,
        end_date=None,
        area_id=None,
    )


@pytest.mark.asyncio
async def test_refresh_analytics_service_rejects_non_admin_user(
    hass: HomeAssistant,
) -> None:
    """数据分析刷新可能调用云端 API，必须限制管理员。"""
    coordinator = SimpleNamespace(
        analytics_runtime_enabled=True,
        async_refresh_analytics=AsyncMock(),
    )
    hass.data[DOMAIN] = {"entry-1": {"coordinator": coordinator}}
    user = await hass.auth.async_create_system_user(
        "limited",
        group_ids=[GROUP_ID_USER],
    )

    async_register_analytics_service(hass)
    with pytest.raises(Unauthorized):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_REFRESH_ANALYTICS,
            {"entry_id": "entry-1", ATTR_ENDPOINT: "energy_analyse", ATTR_DATE_CODE: "2024-08"},
            blocking=True,
            context=Context(user_id=user.id),
            return_response=True,
        )

    coordinator.async_refresh_analytics.assert_not_awaited()
