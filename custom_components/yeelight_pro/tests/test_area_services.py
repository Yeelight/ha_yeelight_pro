"""assign_areas 区域分配服务契约测试。"""
from __future__ import annotations

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr

from custom_components.yeelight_pro.area_service import (
    ERROR_AREA_NOT_FOUND,
    ERROR_DEVICE_REFERENCE_INVALID,
    ERROR_DEVICE_REFERENCE_NOT_YEELIGHT,
)
from custom_components.yeelight_pro.const import DOMAIN

from .area_service_helpers import (
    SENSITIVE_REFERENCE,
    assert_error_does_not_echo,
    async_setup_area_services,
    create_area,
    create_entity_for_device,
    create_non_yeelight_device,
    create_yeelight_device,
)


@pytest.fixture(autouse=True)
async def setup_area_services(hass: HomeAssistant) -> None:
    """为每个测试注册 Yeelight Pro 区域服务。"""
    await async_setup_area_services(hass)


@pytest.mark.asyncio
async def test_assign_areas_accepts_entity_id_and_updates_device_area(
    hass: HomeAssistant,
) -> None:
    """assign_areas 应支持 entity_id，并解析到 HA device_id 后设置 area_id."""
    area_id = create_area(hass, "Kitchen")
    device_id = create_yeelight_device(
        hass,
        identifier="device-1",
        name="Kitchen Light",
    )
    create_entity_for_device(
        hass,
        device_id=device_id,
        entity_id="light.kitchen_light",
        unique_id="yeelight_pro_light_device_1",
    )

    await hass.services.async_call(
        DOMAIN,
        "assign_areas",
        {
            "devices": ["light.kitchen_light"],
            "area_id": area_id,
        },
        blocking=True,
    )

    updated = dr.async_get(hass).async_get(device_id)
    assert updated is not None
    assert updated.area_id == area_id


@pytest.mark.asyncio
async def test_assign_areas_rejects_missing_area_id(
    hass: HomeAssistant,
) -> None:
    """assign_areas 传入不存在的 area_id 应抛错，不应静默写入注册表."""
    device_id = create_yeelight_device(
        hass,
        identifier="device-1",
        name="Kitchen Light",
    )

    with pytest.raises(HomeAssistantError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            "assign_areas",
            {
                "devices": [device_id],
                "area_id": SENSITIVE_REFERENCE,
            },
            blocking=True,
        )

    assert_error_does_not_echo(
        exc_info.value,
        expected=ERROR_AREA_NOT_FOUND,
        sensitive=SENSITIVE_REFERENCE,
    )


@pytest.mark.asyncio
async def test_assign_areas_rejects_unknown_device_or_entity_id(
    hass: HomeAssistant,
) -> None:
    """assign_areas 传入非 HA device_id 且非 entity_id 的值应抛错."""
    area_id = create_area(hass, "Kitchen")

    with pytest.raises(HomeAssistantError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            "assign_areas",
            {
                "devices": [SENSITIVE_REFERENCE],
                "area_id": area_id,
            },
            blocking=True,
        )

    assert_error_does_not_echo(
        exc_info.value,
        expected=ERROR_DEVICE_REFERENCE_INVALID,
        sensitive=SENSITIVE_REFERENCE,
    )


@pytest.mark.asyncio
async def test_assign_areas_rejects_non_yeelight_device(
    hass: HomeAssistant,
) -> None:
    """assign_areas 不应修改其他集成拥有的 HA device registry entry."""
    area_id = create_area(hass, "Kitchen")
    device_id = create_non_yeelight_device(
        hass,
        identifier="device-1",
        name="Other Light",
    )

    with pytest.raises(HomeAssistantError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            "assign_areas",
            {
                "devices": [device_id],
                "area_id": area_id,
            },
            blocking=True,
        )

    assert_error_does_not_echo(
        exc_info.value,
        expected=ERROR_DEVICE_REFERENCE_NOT_YEELIGHT,
        sensitive=device_id,
    )
    device = dr.async_get(hass).async_get(device_id)
    assert device is not None
    assert device.area_id is None


@pytest.mark.asyncio
async def test_assign_areas_rejects_non_yeelight_entity(
    hass: HomeAssistant,
) -> None:
    """assign_areas 通过 entity_id 解析时仍必须限制 Yeelight Pro 设备."""
    area_id = create_area(hass, "Kitchen")
    device_id = create_non_yeelight_device(
        hass,
        identifier="device-1",
        name="Other Light",
    )
    create_entity_for_device(
        hass,
        device_id=device_id,
        entity_id="light.other_light",
        unique_id="other_light_device_1",
    )

    with pytest.raises(HomeAssistantError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            "assign_areas",
            {
                "devices": ["light.other_light"],
                "area_id": area_id,
            },
            blocking=True,
        )

    assert_error_does_not_echo(
        exc_info.value,
        expected=ERROR_DEVICE_REFERENCE_NOT_YEELIGHT,
        sensitive="light.other_light",
    )
    device = dr.async_get(hass).async_get(device_id)
    assert device is not None
    assert device.area_id is None

