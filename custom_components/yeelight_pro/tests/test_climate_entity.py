"""Climate entity service behavior tests."""
from __future__ import annotations

import traceback
from unittest.mock import AsyncMock

import pytest

from homeassistant.components.climate import HVACMode
from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.exceptions import HomeAssistantError

from custom_components.yeelight_pro.climate import YeelightProClimate
from custom_components.yeelight_pro.core.exceptions import YeelightProError

from .projection_helpers import projection_payload

SENSITIVE_VALUES = ("secret-token", "api.yeelight.com", "12345", "67890")


def _climate_payload() -> dict:
    """构造 schema-aware climate payload."""
    return projection_payload(
        device_id="12345",
        category="temp_control",
        component_id="air_conditioner",
        component_category="air_conditioner",
        state={"acp": True, "aco": True, "acm": 1, "acf": 4, "acct": 24, "actt": 26},
        params={"acp": True, "aco": True, "acm": 1, "acf": 4, "acct": 24, "actt": 26},
    )


def _sensitive_error() -> YeelightProError:
    """Build a vendor error containing values that must stay hidden."""
    return YeelightProError(
        "secret-token failed at https://api.yeelight.com/houses/12345/devices/67890"
    )


def _assert_redacted(error: HomeAssistantError, *, action: str) -> None:
    """Assert user-facing and traceback text omit vendor details."""
    message = str(error)
    formatted = "".join(
        traceback.format_exception(type(error), error, error.__traceback__)
    )

    assert error.__cause__ is None
    assert message == f"Yeelight Pro service failed: {action}: YeelightProError"
    for value in SENSITIVE_VALUES:
        assert value not in message
        assert value not in formatted


def test_climate_handles_missing_device_payload(mock_coordinator) -> None:
    """设备拓扑短暂缺失时 climate 不能向 projector 传 None."""
    mock_coordinator.get_device.return_value = None

    climate = YeelightProClimate(mock_coordinator, "12345")

    assert climate.available is False
    assert climate.current_temperature is None
    assert climate.hvac_modes == [HVACMode.OFF]


def test_climate_exposes_documented_mode_and_fan_properties(mock_coordinator) -> None:
    """acm/acf 应投影为 HA climate 模式和风速能力。"""
    mock_coordinator.get_device.return_value = _climate_payload()

    climate = YeelightProClimate(mock_coordinator, "12345")

    assert climate.hvac_mode == HVACMode.COOL
    assert climate.hvac_modes == [
        HVACMode.OFF,
        HVACMode.AUTO,
        HVACMode.COOL,
        HVACMode.FAN_ONLY,
        HVACMode.HEAT,
    ]
    assert climate.fan_mode == "低"
    assert climate.fan_modes == ["高", "中", "低"]


@pytest.mark.asyncio
async def test_set_temperature_none_does_not_send_control(mock_coordinator) -> None:
    """温度为空时不下发控制，避免写入无效目标温度。"""
    mock_coordinator.get_device.return_value = _climate_payload()
    climate = YeelightProClimate(mock_coordinator, "12345")

    await climate.async_set_temperature(temperature=None)

    mock_coordinator.async_control_device.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_temperature_sends_target_temperature(mock_coordinator) -> None:
    """有效目标温度应下发 actt。"""
    mock_coordinator.get_device.return_value = _climate_payload()
    climate = YeelightProClimate(mock_coordinator, "12345")

    await climate.async_set_temperature(**{ATTR_TEMPERATURE: 23})

    mock_coordinator.async_control_device.assert_awaited_once_with(
        "12345",
        {"actt": 23.0},
    )


@pytest.mark.asyncio
async def test_set_hvac_mode_off_sends_power_state(mock_coordinator) -> None:
    """关闭 HVAC 只应写 acp=false，aco 仅表示在线状态。"""
    mock_coordinator.get_device.return_value = _climate_payload()
    climate = YeelightProClimate(mock_coordinator, "12345")

    await climate.async_set_hvac_mode(HVACMode.OFF)

    mock_coordinator.async_control_device.assert_awaited_once_with(
        "12345",
        {"acp": False},
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("hvac_mode", "raw_mode"),
    [
        (HVACMode.COOL, 1),
        (HVACMode.FAN_ONLY, 4),
        (HVACMode.HEAT, 8),
    ],
)
async def test_set_hvac_mode_sends_documented_ac_mode(
    mock_coordinator,
    hvac_mode: HVACMode,
    raw_mode: int,
) -> None:
    """制冷/送风/制热应按易来文档写 acm 原始值。"""
    mock_coordinator.get_device.return_value = _climate_payload()
    climate = YeelightProClimate(mock_coordinator, "12345")

    await climate.async_set_hvac_mode(hvac_mode)

    mock_coordinator.async_control_device.assert_awaited_once_with(
        "12345",
        {"acp": True, "acm": raw_mode},
    )


@pytest.mark.asyncio
async def test_set_hvac_mode_auto_keeps_power_only(mock_coordinator) -> None:
    """AUTO 没有易来 acm 文档值时只打开电源，不伪造模式。"""
    mock_coordinator.get_device.return_value = _climate_payload()
    climate = YeelightProClimate(mock_coordinator, "12345")

    await climate.async_set_hvac_mode(HVACMode.AUTO)

    mock_coordinator.async_control_device.assert_awaited_once_with(
        "12345",
        {"acp": True},
    )


@pytest.mark.asyncio
async def test_set_fan_mode_sends_documented_fan_speed(mock_coordinator) -> None:
    """空调风速应按易来文档写 acf 原始值。"""
    mock_coordinator.get_device.return_value = _climate_payload()
    climate = YeelightProClimate(mock_coordinator, "12345")

    await climate.async_set_fan_mode("低")

    mock_coordinator.async_control_device.assert_awaited_once_with(
        "12345",
        {"acf": 4},
    )


@pytest.mark.asyncio
async def test_set_temperature_control_error_is_redacted(mock_coordinator) -> None:
    """Climate 温度控制错误不得泄露 token、URL 或设备标识。"""
    mock_coordinator.get_device.return_value = _climate_payload()
    mock_coordinator.async_control_device = AsyncMock(side_effect=_sensitive_error())
    climate = YeelightProClimate(mock_coordinator, "12345")

    with pytest.raises(HomeAssistantError) as exc_info:
        await climate.async_set_temperature(**{ATTR_TEMPERATURE: 23})

    _assert_redacted(exc_info.value, action="climate.set_temperature")


@pytest.mark.asyncio
async def test_set_hvac_mode_control_error_is_redacted(mock_coordinator) -> None:
    """Climate HVAC 控制错误不得泄露 token、URL 或设备标识。"""
    mock_coordinator.get_device.return_value = _climate_payload()
    mock_coordinator.async_control_device = AsyncMock(side_effect=_sensitive_error())
    climate = YeelightProClimate(mock_coordinator, "12345")

    with pytest.raises(HomeAssistantError) as exc_info:
        await climate.async_set_hvac_mode(HVACMode.AUTO)

    _assert_redacted(exc_info.value, action="climate.set_hvac_mode")
