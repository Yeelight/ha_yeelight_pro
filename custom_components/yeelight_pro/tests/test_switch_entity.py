"""Switch entity service behavior tests."""
from __future__ import annotations

import traceback
from unittest.mock import AsyncMock

import pytest

from homeassistant.exceptions import HomeAssistantError

from custom_components.yeelight_pro.core.exceptions import YeelightProError
from custom_components.yeelight_pro.switch import (
    ERROR_SWITCH_PROJECTION_UNAVAILABLE,
    YeelightProSwitch,
)

from .projection_helpers import DOMAIN, projection_payload

SENSITIVE_VALUES = ("secret-token", "api.yeelight.com", "12345", "67890")


def _switch_payload(
    *,
    device_id: str = "12345",
    component_id: str = "switch_control",
    state: dict | None = None,
    params: dict | None = None,
) -> dict:
    """构造 schema-aware relay switch payload."""
    return projection_payload(
        device_id=device_id,
        category="relay_switch",
        component_id=component_id,
        component_category="switch control",
        state=state or {"p": True},
        params=params,
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


def test_switch_reads_projection_state(mock_coordinator) -> None:
    """Switch 实体状态应来自投影，而不是硬编码默认值."""
    payload = _switch_payload()
    mock_coordinator.get_device.return_value = payload
    switch = YeelightProSwitch(
        mock_coordinator,
        12345,
        component_id="switch_control",
    )

    assert switch.available is True
    assert switch.is_on is True
    assert switch.icon == "mdi:light-switch"
    assert switch.device_info is not None
    assert (DOMAIN, "12345") in switch.device_info["identifiers"]


@pytest.mark.asyncio
async def test_turn_on_sends_projected_control_key(mock_coordinator) -> None:
    """打开 switch 应下发投影出的控制 key."""
    mock_coordinator.get_device.return_value = _switch_payload(state={"p": False})
    switch = YeelightProSwitch(
        mock_coordinator,
        12345,
        component_id="switch_control",
    )

    await switch.async_turn_on()

    mock_coordinator.async_control_device.assert_awaited_once_with(
        12345,
        {"p": True},
    )


@pytest.mark.asyncio
async def test_turn_off_sends_projected_control_key(mock_coordinator) -> None:
    """关闭 switch 应下发投影出的控制 key."""
    mock_coordinator.get_device.return_value = _switch_payload(state={"p": True})
    switch = YeelightProSwitch(
        mock_coordinator,
        12345,
        component_id="switch_control",
    )

    await switch.async_turn_off()

    mock_coordinator.async_control_device.assert_awaited_once_with(
        12345,
        {"p": False},
    )


@pytest.mark.asyncio
async def test_turn_on_uses_indexed_component_control_key(mock_coordinator) -> None:
    """组件索引开关必须下发 N-p 控制 key."""
    mock_coordinator.get_device.return_value = _switch_payload(
        component_id="switch_1",
        state={"p": False},
        params={"1-p": False},
    )
    switch = YeelightProSwitch(
        mock_coordinator,
        12345,
        component_id="switch_1",
    )

    await switch.async_turn_on()

    mock_coordinator.async_control_device.assert_awaited_once_with(
        12345,
        {"1-p": True},
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("method_name", ["async_turn_on", "async_turn_off"])
async def test_service_without_projection_raises_ha_error_without_echoing_component(
    mock_coordinator,
    method_name: str,
) -> None:
    """缺少 switch 投影时，服务调用应显式失败."""
    mock_coordinator.get_device.return_value = {"type": "light", "params": {}}
    switch = YeelightProSwitch(
        mock_coordinator,
        12345,
        component_id="secret-token-switch-control",
    )
    method = getattr(switch, method_name)

    with pytest.raises(HomeAssistantError) as exc_info:
        await method()

    message = str(exc_info.value)
    formatted = "".join(
        traceback.format_exception(
            type(exc_info.value),
            exc_info.value,
            exc_info.value.__traceback__,
        )
    )
    assert ERROR_SWITCH_PROJECTION_UNAVAILABLE in message
    assert "secret-token-switch-control" not in message
    assert "secret-token-switch-control" not in formatted
    mock_coordinator.async_control_device.assert_not_awaited()


@pytest.mark.asyncio
async def test_turn_on_control_error_is_redacted(mock_coordinator) -> None:
    """Switch 控制错误不得泄露 token、URL 或设备标识."""
    mock_coordinator.get_device.return_value = _switch_payload()
    mock_coordinator.async_control_device = AsyncMock(side_effect=_sensitive_error())
    switch = YeelightProSwitch(
        mock_coordinator,
        12345,
        component_id="switch_control",
    )

    with pytest.raises(HomeAssistantError) as exc_info:
        await switch.async_turn_on()

    _assert_redacted(exc_info.value, action="switch.turn_on")
