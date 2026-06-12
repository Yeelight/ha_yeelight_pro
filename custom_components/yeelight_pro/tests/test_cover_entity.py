"""Cover entity service behavior tests."""
from __future__ import annotations

import traceback
from unittest.mock import AsyncMock

import pytest

from homeassistant.exceptions import HomeAssistantError

from custom_components.yeelight_pro.core.exceptions import YeelightProError
from custom_components.yeelight_pro.cover import YeelightProCover

from .test_cover_multi_component_projection import multi_curtain_payload
from .projection_helpers import DOMAIN, projection_payload

SENSITIVE_VALUES = ("secret-token", "api.yeelight.com", "12345", "67890")


def _cover_payload(
    *,
    device_id: str = "12345",
    state: dict | None = None,
) -> dict:
    """构造 schema-aware curtain payload."""
    return projection_payload(
        device_id=device_id,
        category="curtain",
        component_id="curtain",
        component_category="curtain",
        state=state or {"cp": 20, "tp": 80},
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


def test_cover_reads_projection_state(mock_coordinator) -> None:
    """Cover 实体状态应来自 curtain 投影."""
    mock_coordinator.get_device.return_value = _cover_payload()
    cover = YeelightProCover(mock_coordinator, 12345)

    assert cover.available is True
    assert cover.current_cover_position == 20
    assert cover.is_closed is False
    assert cover.device_info is not None
    assert (DOMAIN, "12345") in cover.device_info["identifiers"]


def test_cover_handles_missing_device_payload(mock_coordinator) -> None:
    """设备拓扑短暂缺失时 cover 不能向 projector 传 None."""
    mock_coordinator.get_device.return_value = None

    cover = YeelightProCover(mock_coordinator, 12345)

    assert cover.available is False
    assert cover.current_cover_position is None
    assert cover.device_info is None


@pytest.mark.asyncio
async def test_open_cover_sends_target_position(mock_coordinator) -> None:
    """打开窗帘应下发目标开合度 100."""
    mock_coordinator.get_device.return_value = _cover_payload()
    cover = YeelightProCover(mock_coordinator, 12345)

    await cover.async_open_cover()

    mock_coordinator.async_control_device.assert_awaited_once_with(
        12345,
        {"tp": 100},
    )


@pytest.mark.asyncio
async def test_close_cover_sends_target_position(mock_coordinator) -> None:
    """关闭窗帘应下发目标开合度 0."""
    mock_coordinator.get_device.return_value = _cover_payload()
    cover = YeelightProCover(mock_coordinator, 12345)

    await cover.async_close_cover()

    mock_coordinator.async_control_device.assert_awaited_once_with(
        12345,
        {"tp": 0},
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("requested", "expected"),
    [
        (150, 100),
        (-10, 0),
        (42, 42),
    ],
)
async def test_set_cover_position_clamps_target_position(
    mock_coordinator,
    requested: int,
    expected: int,
) -> None:
    """设置开合度应钳制到 Home Assistant cover 百分比范围."""
    mock_coordinator.get_device.return_value = _cover_payload()
    cover = YeelightProCover(mock_coordinator, 12345)

    await cover.async_set_cover_position(position=requested)

    mock_coordinator.async_control_device.assert_awaited_once_with(
        12345,
        {"tp": expected},
    )


@pytest.mark.asyncio
async def test_multi_component_cover_sends_component_target_key(mock_coordinator) -> None:
    """多组件窗帘控制应写入对应组件的 tp key。"""
    mock_coordinator.get_device.return_value = multi_curtain_payload()
    cover = YeelightProCover(
        mock_coordinator,
        "curtain-dual-1",
        component_id="curtain_2",
    )

    await cover.async_set_cover_position(position=55)

    mock_coordinator.async_control_device.assert_awaited_once_with(
        "curtain-dual-1",
        {"2-tp": 55},
    )


@pytest.mark.asyncio
async def test_open_cover_control_error_is_redacted(mock_coordinator) -> None:
    """Cover 控制错误不得泄露 token、URL 或设备标识."""
    mock_coordinator.get_device.return_value = _cover_payload()
    mock_coordinator.async_control_device = AsyncMock(side_effect=_sensitive_error())
    cover = YeelightProCover(mock_coordinator, 12345)

    with pytest.raises(HomeAssistantError) as exc_info:
        await cover.async_open_cover()

    _assert_redacted(exc_info.value, action="cover.open_cover")
