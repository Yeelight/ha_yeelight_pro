"""auto_assign_areas 区域分配服务契约测试。"""
from __future__ import annotations

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
)

from custom_components.yeelight_pro.area_service import (
    ERROR_GATEWAY_NOT_FOUND,
    ERROR_GATEWAY_NOT_YEELIGHT,
)
from custom_components.yeelight_pro.const import DOMAIN

from .area_service_helpers import (
    SENSITIVE_REFERENCE,
    assert_error_does_not_echo,
    async_setup_area_services,
    create_non_yeelight_device,
    create_yeelight_device,
)


@pytest.fixture(autouse=True)
async def setup_area_services(hass: HomeAssistant) -> None:
    """为每个测试注册 Yeelight Pro 区域服务。"""
    await async_setup_area_services(hass)


@pytest.mark.asyncio
async def test_auto_assign_areas_gateway_id_matches_gateway_child_devices(
    hass: HomeAssistant,
) -> None:
    """auto_assign_areas 的 gateway_id 应匹配网关子设备."""
    gateway_device_id = create_yeelight_device(
        hass,
        identifier="gateway",
        name="Yeelight Gateway",
    )
    matched_device_id = create_yeelight_device(
        hass,
        identifier="matched",
        name="客厅主灯",
        via_device_id=gateway_device_id,
    )
    skipped_device_id = create_yeelight_device(
        hass,
        identifier="skipped",
        name="卧室主灯",
    )

    await hass.services.async_call(
        DOMAIN,
        "auto_assign_areas",
        {"gateway_id": gateway_device_id},
        blocking=True,
    )

    device_registry = dr.async_get(hass)
    matched = device_registry.async_get(matched_device_id)
    skipped = device_registry.async_get(skipped_device_id)

    assert matched is not None
    assert matched.area_id == ar.async_get(hass).async_get_area_by_name("客厅").id
    assert skipped is not None
    assert skipped.area_id is None


@pytest.mark.asyncio
async def test_auto_assign_areas_rejects_non_yeelight_gateway_id(
    hass: HomeAssistant,
) -> None:
    """auto_assign_areas 的 gateway_id 不能指向其他集成设备."""
    gateway_device_id = create_non_yeelight_device(
        hass,
        identifier="gateway",
        name="Other Gateway",
    )
    matched_device_id = create_yeelight_device(
        hass,
        identifier="matched",
        name="客厅主灯",
        via_device_id=gateway_device_id,
    )

    with pytest.raises(HomeAssistantError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            "auto_assign_areas",
            {"gateway_id": gateway_device_id},
            blocking=True,
        )

    assert_error_does_not_echo(
        exc_info.value,
        expected=ERROR_GATEWAY_NOT_YEELIGHT,
        sensitive=gateway_device_id,
    )
    device = dr.async_get(hass).async_get(matched_device_id)
    assert device is not None
    assert device.area_id is None


@pytest.mark.asyncio
async def test_auto_assign_areas_rejects_unknown_gateway_without_echoing_input(
    hass: HomeAssistant,
) -> None:
    """auto_assign_areas 不应在未知 gateway 错误中回显 gateway_id."""
    with pytest.raises(HomeAssistantError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            "auto_assign_areas",
            {"gateway_id": SENSITIVE_REFERENCE},
            blocking=True,
        )

    assert_error_does_not_echo(
        exc_info.value,
        expected=ERROR_GATEWAY_NOT_FOUND,
        sensitive=SENSITIVE_REFERENCE,
    )
