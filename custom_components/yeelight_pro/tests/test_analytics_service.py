"""Analytics refresh service tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from homeassistant.auth.const import GROUP_ID_ADMIN, GROUP_ID_USER
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import ServiceValidationError, Unauthorized

from custom_components.yeelight_pro.analytics_runtime import AnalyticsSnapshot
from custom_components.yeelight_pro.analytics_service import (
    ATTR_DATE_CODE,
    ATTR_ENDPOINT,
    ERROR_ADMIN_CONTEXT_REQUIRED,
    ERROR_ANALYTICS_DISABLED,
    ERROR_INVALID_ANALYTICS_REQUEST,
    SERVICE_REFRESH_ANALYTICS,
    async_register_analytics_service,
)
from custom_components.yeelight_pro.const import DOMAIN
from custom_components.yeelight_pro.core.exceptions import CommandError


async def _admin_user(hass: HomeAssistant):
    """Create an admin user context for analytics service calls."""
    return await hass.auth.async_create_system_user(
        "analytics-admin",
        group_ids=[GROUP_ID_ADMIN],
    )


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
    admin = await _admin_user(hass)

    async_register_analytics_service(hass)
    with pytest.raises(ServiceValidationError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_REFRESH_ANALYTICS,
            {"entry_id": "entry-1", ATTR_ENDPOINT: "energy_analyse", ATTR_DATE_CODE: "2024-08"},
            blocking=True,
            context=Context(user_id=admin.id),
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
    admin = await _admin_user(hass)

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
        context=Context(user_id=admin.id),
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
async def test_refresh_analytics_service_strips_raw_error_cause(
    hass: HomeAssistant,
) -> None:
    """服务错误不应通过异常链泄露 raw analytics 标识或 vendor 文案。"""
    coordinator = SimpleNamespace(
        analytics_runtime_enabled=True,
        async_refresh_analytics=AsyncMock(
            side_effect=CommandError(
                "deviceId=dev-secret token=secret-token raw={'user':'private'}"
            )
        ),
    )
    hass.data[DOMAIN] = {"entry-1": {"coordinator": coordinator}}
    admin = await _admin_user(hass)

    async_register_analytics_service(hass)
    with pytest.raises(ServiceValidationError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_REFRESH_ANALYTICS,
            {
                "entry_id": "entry-1",
                ATTR_ENDPOINT: "energy_analyse",
                ATTR_DATE_CODE: "2024-08",
            },
            blocking=True,
            context=Context(user_id=admin.id),
            return_response=True,
        )

    assert exc_info.value.__cause__ is None
    visible_error = str(exc_info.value)
    assert ERROR_INVALID_ANALYTICS_REQUEST in visible_error
    assert "dev-secret" not in visible_error
    assert "secret-token" not in visible_error
    assert "private" not in visible_error


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


@pytest.mark.asyncio
async def test_refresh_analytics_service_rejects_missing_user_context(
    hass: HomeAssistant,
) -> None:
    """analytics 手动刷新必须来自明确的管理员用户上下文。"""
    coordinator = SimpleNamespace(
        analytics_runtime_enabled=True,
        async_refresh_analytics=AsyncMock(),
    )
    hass.data[DOMAIN] = {"entry-1": {"coordinator": coordinator}}

    async_register_analytics_service(hass)
    with pytest.raises(Unauthorized) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_REFRESH_ANALYTICS,
            {"entry_id": "entry-1", ATTR_ENDPOINT: "energy_analyse", ATTR_DATE_CODE: "2024-08"},
            blocking=True,
            return_response=True,
        )

    assert str(exc_info.value) == "Unauthorized"
    assert exc_info.value.permission == ERROR_ADMIN_CONTEXT_REQUIRED
    coordinator.async_refresh_analytics.assert_not_awaited()
