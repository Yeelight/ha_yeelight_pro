"""Lock entity service behavior tests."""
from __future__ import annotations

import traceback
from unittest.mock import AsyncMock

import pytest

from homeassistant.exceptions import HomeAssistantError

from custom_components.yeelight_pro.core.exceptions import YeelightProError
from custom_components.yeelight_pro.lock import (
    ERROR_LOCK_PROJECTION_UNAVAILABLE,
    YeelightProLock,
)

from .projection_helpers import DOMAIN, projection_payload

SENSITIVE_VALUES = ("secret-token", "api.yeelight.com", "12345", "67890")


def _lock_payload(
    *,
    device_id: str = "12345",
    state: dict | None = None,
) -> dict:
    """构造 schema-aware lock payload."""
    return projection_payload(
        device_id=device_id,
        category="other",
        component_id="lock",
        component_category="lock",
        state=state or {"locked": True},
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


def test_lock_reads_projection_state(mock_coordinator) -> None:
    """Lock 实体状态应来自投影，而不是硬编码默认值."""
    mock_coordinator.get_device.return_value = _lock_payload()
    lock = YeelightProLock(mock_coordinator, "12345")

    assert lock.available is True
    assert lock.is_locked is True
    assert lock.icon == "mdi:lock"
    assert lock.device_info is not None
    assert (DOMAIN, "12345") in lock.device_info["identifiers"]


@pytest.mark.asyncio
async def test_lock_sends_projected_control_key(mock_coordinator) -> None:
    """锁定时应下发投影出的控制 key."""
    mock_coordinator.get_device.return_value = _lock_payload(state={"locked": False})
    lock = YeelightProLock(mock_coordinator, "12345")

    await lock.async_lock()

    mock_coordinator.async_control_device.assert_awaited_once_with(
        "12345",
        {"locked": True},
    )


@pytest.mark.asyncio
async def test_unlock_sends_projected_control_key(mock_coordinator) -> None:
    """解锁时应下发投影出的控制 key."""
    mock_coordinator.get_device.return_value = _lock_payload(state={"locked": True})
    lock = YeelightProLock(mock_coordinator, "12345")

    await lock.async_unlock()

    mock_coordinator.async_control_device.assert_awaited_once_with(
        "12345",
        {"locked": False},
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("method_name", ["async_lock", "async_unlock"])
async def test_lock_service_without_projection_raises_ha_error(
    mock_coordinator,
    method_name: str,
) -> None:
    """缺少 lock 投影时，服务调用应显式失败且不下发未知控制 key."""
    mock_coordinator.get_device.return_value = {"type": "light", "params": {}}
    lock = YeelightProLock(mock_coordinator, "secret-token-12345")
    method = getattr(lock, method_name)

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
    assert ERROR_LOCK_PROJECTION_UNAVAILABLE in message
    assert "secret-token-12345" not in message
    assert "secret-token-12345" not in formatted
    mock_coordinator.async_control_device.assert_not_awaited()


@pytest.mark.asyncio
async def test_lock_control_error_is_redacted(mock_coordinator) -> None:
    """Lock 控制错误不得泄露 token、URL 或设备标识."""
    mock_coordinator.get_device.return_value = _lock_payload()
    mock_coordinator.async_control_device = AsyncMock(side_effect=_sensitive_error())
    lock = YeelightProLock(mock_coordinator, "12345")

    with pytest.raises(HomeAssistantError) as exc_info:
        await lock.async_lock()

    _assert_redacted(exc_info.value, action="lock.lock")
