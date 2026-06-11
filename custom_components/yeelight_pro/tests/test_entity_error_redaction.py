"""Entity service error redaction tests."""

from __future__ import annotations

import traceback
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from homeassistant.exceptions import HomeAssistantError

from custom_components.yeelight_pro.button import YeelightProSceneButton
from custom_components.yeelight_pro.core.exceptions import YeelightProError
from custom_components.yeelight_pro.light import YeelightProLight
from custom_components.yeelight_pro.number import YeelightProGroupBrightness
from custom_components.yeelight_pro.switch import YeelightProSwitch


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


def _switch_payload() -> dict[str, Any]:
    """Build a minimal relay-switch payload."""
    return {
        "device_id": 12345,
        "name": "Leaky 67890 Switch",
        "category": "relay_switch",
        "type": "switch",
        "online": True,
        "params": {"1-p": False},
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
async def test_scene_button_error_is_redacted() -> None:
    """Cloud-scene button errors should not expose scene names, IDs, or raw details."""
    coordinator = MagicMock()
    coordinator.house_id = 12345
    coordinator.async_execute_scene = AsyncMock(side_effect=_sensitive_error())
    button = YeelightProSceneButton(
        coordinator,
        {
            "id": "67890",
            "name": "Secret Scene secret-token api.yeelight.com 12345",
        },
    )

    with pytest.raises(HomeAssistantError) as exc_info:
        await button.async_press()

    _assert_redacted(exc_info.value, action="button.execute_scene")


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
async def test_switch_control_error_is_redacted() -> None:
    """Switch control errors should hide device vendor details."""
    coordinator = MagicMock()
    coordinator.get_device.return_value = _switch_payload()
    coordinator.async_control_device = AsyncMock(side_effect=_sensitive_error())
    switch = YeelightProSwitch(coordinator, 12345, component_id="switch_1")

    with pytest.raises(HomeAssistantError) as exc_info:
        await switch.async_turn_on()

    _assert_redacted(exc_info.value, action="switch.turn_on")
