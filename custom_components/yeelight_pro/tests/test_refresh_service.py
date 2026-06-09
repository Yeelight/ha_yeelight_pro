"""Manual refresh service tests."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from homeassistant.auth.const import GROUP_ID_USER
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import (
    HomeAssistantError,
    ServiceValidationError,
    Unauthorized,
)

from custom_components.yeelight_pro.const import DOMAIN
from custom_components.yeelight_pro.refresh_service import (
    ATTR_REFRESH_PRODUCT_SCHEMAS,
    ERROR_ENTRY_NOT_LOADED,
    SERVICE_REFRESH,
    async_register_refresh_service,
)

from .refresh_service_helpers import refresh_coordinator, refresh_entry


@pytest.mark.asyncio
async def test_refresh_service_refreshes_loaded_entries(
    hass: HomeAssistant,
) -> None:
    """Manual refresh should refresh every loaded Yeelight Pro entry."""
    post_refresh = AsyncMock()
    first_entry = refresh_entry("entry-1")
    second_entry = refresh_entry("entry-2")
    first = refresh_coordinator(hass)
    second = refresh_coordinator(hass)
    hass.data[DOMAIN] = {
        "entry-1": {"entry": first_entry, "coordinator": first},
        "entry-2": {"entry": second_entry, "coordinator": second},
    }

    async_register_refresh_service(hass, post_refresh)
    await hass.services.async_call(
        DOMAIN,
        SERVICE_REFRESH,
        blocking=True,
    )

    first.async_request_refresh.assert_awaited_once()
    second.async_request_refresh.assert_awaited_once()
    first.async_request_product_schema_refresh.assert_not_awaited()
    second.async_request_product_schema_refresh.assert_not_awaited()
    assert post_refresh.await_args_list[0].args == (first_entry, first)
    assert post_refresh.await_args_list[1].args == (second_entry, second)


@pytest.mark.asyncio
async def test_refresh_service_rejects_non_admin_user(
    hass: HomeAssistant,
) -> None:
    """Manual refresh is registry maintenance and must require admin access."""
    post_refresh = AsyncMock()
    entry = refresh_entry("entry-1")
    coordinator = refresh_coordinator(hass)
    hass.data[DOMAIN] = {
        "entry-1": {"entry": entry, "coordinator": coordinator},
    }
    user = await hass.auth.async_create_system_user(
        "limited",
        group_ids=[GROUP_ID_USER],
    )

    async_register_refresh_service(hass, post_refresh)
    with pytest.raises(Unauthorized):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_REFRESH,
            blocking=True,
            context=Context(user_id=user.id),
        )

    coordinator.async_request_refresh.assert_not_awaited()
    post_refresh.assert_not_awaited()


@pytest.mark.asyncio
async def test_refresh_service_filters_by_entry_id(
    hass: HomeAssistant,
) -> None:
    """Manual refresh should support targeting one config entry."""
    post_refresh = AsyncMock()
    first_entry = refresh_entry("entry-1")
    second_entry = refresh_entry("entry-2")
    first = refresh_coordinator(hass)
    second = refresh_coordinator(hass)
    hass.data[DOMAIN] = {
        "entry-1": {"entry": first_entry, "coordinator": first},
        "entry-2": {"entry": second_entry, "coordinator": second},
    }

    async_register_refresh_service(hass, post_refresh)
    await hass.services.async_call(
        DOMAIN,
        SERVICE_REFRESH,
        {"entry_id": "entry-2"},
        blocking=True,
    )

    first.async_request_refresh.assert_not_awaited()
    second.async_request_refresh.assert_awaited_once()
    post_refresh.assert_awaited_once_with(second_entry, second)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "requested_entry_id",
    [
        "missing-entry",
        "secret-token",
        "https://api.yeelight.com/house/entry-secret",
    ],
)
async def test_refresh_service_rejects_unknown_entry_id_without_echoing_input(
    hass: HomeAssistant,
    requested_entry_id: str,
) -> None:
    """未知 entry_id 应明确失败，但不能把用户输入回显到错误消息."""
    post_refresh = AsyncMock()
    entry = refresh_entry("entry-1")
    coordinator = refresh_coordinator(hass)
    hass.data[DOMAIN] = {
        "entry-1": {"entry": entry, "coordinator": coordinator},
    }

    async_register_refresh_service(hass, post_refresh)
    with pytest.raises(HomeAssistantError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_REFRESH,
            {"entry_id": requested_entry_id},
            blocking=True,
        )

    message = str(exc_info.value)
    assert ERROR_ENTRY_NOT_LOADED in message
    assert requested_entry_id not in message
    coordinator.async_request_refresh.assert_not_awaited()
    coordinator.async_request_product_schema_refresh.assert_not_awaited()
    post_refresh.assert_not_awaited()


@pytest.mark.asyncio
async def test_refresh_service_can_force_product_schema_refresh(
    hass: HomeAssistant,
) -> None:
    """Manual refresh can opt in to refetching cached product schemas."""
    post_refresh = AsyncMock()
    entry = refresh_entry("entry-1")
    coordinator = refresh_coordinator(hass)
    hass.data[DOMAIN] = {
        "entry-1": {"entry": entry, "coordinator": coordinator},
    }

    async_register_refresh_service(hass, post_refresh)
    await hass.services.async_call(
        DOMAIN,
        SERVICE_REFRESH,
        {ATTR_REFRESH_PRODUCT_SCHEMAS: True},
        blocking=True,
    )

    coordinator.async_request_refresh.assert_not_awaited()
    coordinator.async_request_product_schema_refresh.assert_awaited_once()
    post_refresh.assert_awaited_once_with(entry, coordinator)


@pytest.mark.asyncio
async def test_refresh_service_skips_entries_without_config_entry(
    hass: HomeAssistant,
) -> None:
    """Loaded data without a config entry should fail instead of reporting success."""
    post_refresh = AsyncMock()
    coordinator = refresh_coordinator(hass)
    hass.data[DOMAIN] = {
        "entry-1": {"coordinator": coordinator},
    }

    async_register_refresh_service(hass, post_refresh)
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_REFRESH,
            blocking=True,
        )

    coordinator.async_request_refresh.assert_not_awaited()
    post_refresh.assert_not_awaited()


@pytest.mark.asyncio
async def test_refresh_service_rejects_when_no_valid_entries_refresh(
    hass: HomeAssistant,
) -> None:
    """Manual refresh must not silently succeed with zero valid runtime entries."""
    post_refresh = AsyncMock()
    hass.data[DOMAIN] = {
        "entry-1": {"entry": refresh_entry("entry-1"), "coordinator": object()},
    }

    async_register_refresh_service(hass, post_refresh)
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_REFRESH,
            blocking=True,
        )

    post_refresh.assert_not_awaited()
