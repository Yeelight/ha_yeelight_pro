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
        state={"acp": True, "aco": True, "acct": 24, "actt": 26},
        params={"acp": True, "aco": True, "acct": 24, "actt": 26},
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
@pytest.mark.parametrize(
    ("hvac_mode", "expected_power"),
    [
        (HVACMode.OFF, False),
        (HVACMode.AUTO, True),
    ],
)
async def test_set_hvac_mode_sends_power_state(
    mock_coordinator,
    hvac_mode: HVACMode,
    expected_power: bool,
) -> None:
    """HVAC 模式应映射为 acp 开关状态，aco 仅表示在线状态。"""
    mock_coordinator.get_device.return_value = _climate_payload()
    climate = YeelightProClimate(mock_coordinator, "12345")

    await climate.async_set_hvac_mode(hvac_mode)

    mock_coordinator.async_control_device.assert_awaited_once_with(
        "12345",
        {"acp": expected_power},
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
