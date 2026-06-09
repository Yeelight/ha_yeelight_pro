"""Entity service error redaction tests."""

from __future__ import annotations

import traceback
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from homeassistant.exceptions import HomeAssistantError

from custom_components.yeelight_pro.core.exceptions import YeelightProError
from custom_components.yeelight_pro.light import YeelightProLight
from custom_components.yeelight_pro.number import YeelightProGroupBrightness
from custom_components.yeelight_pro.scene import YeelightProScene
from custom_components.yeelight_pro.vacuum import (
    ERROR_INVALID_VACUUM_FAN_SPEED,
    YeelightProVacuum,
)


SENSITIVE_VALUES = ("secret-token", "api.yeelight.com", "12345", "67890")


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


def _light_payload() -> dict[str, Any]:
    """Build a minimal legacy light payload."""
    return {
        "device_id": 12345,
        "name": "Leaky 67890 Light",
        "type": "light",
        "online": True,
        "params": {"p": False, "l": 50},
    }


def _vacuum_payload() -> dict[str, Any]:
    """Build a minimal experimental vacuum payload."""
    return {
        "device_id": 12345,
        "name": "Leaky 67890 Vacuum",
        "type": "vacuum",
        "online": True,
        "params": {"status": "idle", "battery": 80, "fan_speed": 1},
    }


@pytest.mark.asyncio
async def test_light_control_error_is_redacted() -> None:
    """Device control errors should hide IDs, URLs, tokens, and raw details."""
    coordinator = MagicMock()
    coordinator.get_device.return_value = _light_payload()
    coordinator.async_control_device = AsyncMock(side_effect=_sensitive_error())
    light = YeelightProLight(coordinator, 12345)

    with pytest.raises(HomeAssistantError) as exc_info:
        await light.async_turn_on()

    _assert_redacted(exc_info.value, action="light.turn_on")


@pytest.mark.asyncio
async def test_scene_entity_error_is_redacted() -> None:
    """Scene entity errors should not expose scene names, IDs, or raw details."""
    coordinator = MagicMock()
    coordinator.house_id = 12345
    coordinator.async_execute_scene = AsyncMock(side_effect=_sensitive_error())
    scene = YeelightProScene(
        coordinator,
        "67890",
        name="Secret Scene secret-token api.yeelight.com 12345",
    )

    with pytest.raises(HomeAssistantError) as exc_info:
        await scene.async_activate()

    _assert_redacted(exc_info.value, action="scene.activate")


@pytest.mark.asyncio
async def test_group_number_error_is_redacted() -> None:
    """Group number errors should not expose group identifiers or raw details."""
    coordinator = MagicMock()
    coordinator.house_id = 12345
    coordinator.async_control_group = AsyncMock(side_effect=_sensitive_error())
    entity = YeelightProGroupBrightness(
        coordinator,
        "67890",
        "Secret Group secret-token api.yeelight.com 12345",
    )

    with pytest.raises(HomeAssistantError) as exc_info:
        await entity.async_set_native_value(42)

    _assert_redacted(exc_info.value, action="number.set_group_brightness")


@pytest.mark.asyncio
async def test_vacuum_control_error_is_redacted() -> None:
    """Experimental vacuum control errors should hide device vendor details."""
    coordinator = MagicMock()
    coordinator.get_device.return_value = _vacuum_payload()
    coordinator.async_control_device = AsyncMock(side_effect=_sensitive_error())
    vacuum = YeelightProVacuum(coordinator, 12345)

    with pytest.raises(HomeAssistantError) as exc_info:
        await vacuum.async_start()

    _assert_redacted(exc_info.value, action="vacuum.start")


@pytest.mark.asyncio
async def test_vacuum_invalid_fan_speed_error_is_redacted() -> None:
    """Vacuum fan speed validation errors should not echo user input."""
    coordinator = MagicMock()
    coordinator.get_device.return_value = _vacuum_payload()
    coordinator.async_control_device = AsyncMock()
    vacuum = YeelightProVacuum(coordinator, 12345)
    fan_speed = "secret-token api.yeelight.com 12345"

    with pytest.raises(HomeAssistantError) as exc_info:
        await vacuum.async_set_fan_speed(fan_speed)

    message = str(exc_info.value)
    formatted = "".join(
        traceback.format_exception(
            type(exc_info.value),
            exc_info.value,
            exc_info.value.__traceback__,
        )
    )
    assert ERROR_INVALID_VACUUM_FAN_SPEED in message
    assert "secret-token" not in message
    assert "api.yeelight.com" not in message
    assert "secret-token" not in formatted
    assert "api.yeelight.com" not in formatted
    coordinator.async_control_device.assert_not_awaited()
