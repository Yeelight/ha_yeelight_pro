"""Cover entity service behavior tests."""
from __future__ import annotations

import traceback
from unittest.mock import AsyncMock, MagicMock

import pytest

from homeassistant.components.cover import CoverEntityFeature
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
    component_category: str = "curtain",
) -> dict:
    """构造 schema-aware curtain payload."""
    return projection_payload(
        device_id=device_id,
        category="curtain",
        component_id="curtain",
        component_category=component_category,
        state=state or {"cp": 20, "tp": 80},
    )


def _zebra_blind_payload() -> dict:
    """构造带旋转角的梦幻帘 payload."""
    return _cover_payload(
        state={"cp": 20, "tp": 80, "cra": 90, "tra": 135},
        component_category="zebra blinds",
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


def test_zebra_blind_reads_cover_tilt_state(mock_coordinator) -> None:
    """梦幻帘旋转角应映射为 HA cover tilt 百分比."""
    mock_coordinator.get_device.return_value = _zebra_blind_payload()
    cover = YeelightProCover(mock_coordinator, 12345)

    assert cover.current_cover_tilt_position == 50
    assert cover.supported_features & CoverEntityFeature.SET_TILT_POSITION


def test_cover_handles_missing_device_payload(mock_coordinator) -> None:
    """设备拓扑短暂缺失时 cover 不能向 projector 传 None."""
    mock_coordinator.get_device.return_value = None

    cover = YeelightProCover(mock_coordinator, 12345)

    assert cover.available is False
    assert cover.current_cover_position is None
    assert cover.device_info is None


def test_cover_stop_feature_is_hidden_without_strict_lan_action_capability(
    mock_coordinator,
) -> None:
    """未确认 LAN action 可用时，不向 HA 暴露 STOP。"""
    mock_coordinator.get_device.return_value = _cover_payload()
    cover = YeelightProCover(mock_coordinator, 12345)

    assert not cover.supported_features & CoverEntityFeature.STOP


def test_cover_stop_feature_is_exposed_when_lan_action_is_available(
    mock_coordinator,
) -> None:
    """LAN action 可用时，HA cover 才显示停止按钮。"""
    mock_coordinator.get_device.return_value = _cover_payload()
    mock_coordinator.can_control_device_action = MagicMock(return_value=True)
    cover = YeelightProCover(mock_coordinator, 12345)

    assert cover.supported_features & CoverEntityFeature.STOP


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
async def test_zebra_blind_tilt_sends_target_angle(mock_coordinator) -> None:
    """HA tilt 百分比应转换为 Yeelight tra 旋转角."""
    mock_coordinator.get_device.return_value = _zebra_blind_payload()
    cover = YeelightProCover(mock_coordinator, 12345)

    await cover.async_set_cover_tilt_position(tilt_position=75)

    mock_coordinator.async_control_device.assert_awaited_once_with(
        12345,
        {"tra": 135},
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("requested", "expected"),
    [
        (150, 180),
        (-10, 0),
    ],
)
async def test_zebra_blind_tilt_clamps_target_angle(
    mock_coordinator,
    requested: int,
    expected: int,
) -> None:
    """Tilt 写入应先钳制 HA 百分比，再映射为 Yeelight 角度."""
    mock_coordinator.get_device.return_value = _zebra_blind_payload()
    cover = YeelightProCover(mock_coordinator, 12345)

    await cover.async_set_cover_tilt_position(tilt_position=requested)

    mock_coordinator.async_control_device.assert_awaited_once_with(
        12345,
        {"tra": expected},
    )


@pytest.mark.asyncio
async def test_multi_component_zebra_blind_tilt_sends_component_key(
    mock_coordinator,
) -> None:
    """多组件梦幻帘 tilt 控制应写入对应组件的 tra key."""
    mock_coordinator.get_device.return_value = multi_curtain_payload()
    cover = YeelightProCover(
        mock_coordinator,
        "curtain-dual-1",
        component_id="curtain_2",
    )

    await cover.async_set_cover_tilt_position(tilt_position=75)

    mock_coordinator.async_control_device.assert_awaited_once_with(
        "curtain-dual-1",
        {"2-tra": 135},
    )


@pytest.mark.asyncio
async def test_stop_cover_sends_documented_lan_motor_pause_action(
    mock_coordinator,
) -> None:
    """停止窗帘应使用 LAN action.motorAdjust.pause。"""
    mock_coordinator.get_device.return_value = _cover_payload()
    mock_coordinator.async_action_device = AsyncMock()
    cover = YeelightProCover(mock_coordinator, 12345)

    await cover.async_stop_cover()

    mock_coordinator.async_action_device.assert_awaited_once_with(
        12345,
        {"motorAdjust": {"type": "pause"}},
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


@pytest.mark.asyncio
async def test_stop_cover_control_error_is_redacted(mock_coordinator) -> None:
    """Cover 停止错误也必须走统一脱敏出口。"""
    mock_coordinator.get_device.return_value = _cover_payload()
    mock_coordinator.async_action_device = AsyncMock(side_effect=_sensitive_error())
    cover = YeelightProCover(mock_coordinator, 12345)

    with pytest.raises(HomeAssistantError) as exc_info:
        await cover.async_stop_cover()

    _assert_redacted(exc_info.value, action="cover.stop_cover")
