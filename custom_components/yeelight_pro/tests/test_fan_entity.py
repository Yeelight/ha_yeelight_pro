"""Fan entity service behavior tests."""
from __future__ import annotations

import traceback

import pytest

from homeassistant.components.fan import DIRECTION_FORWARD, DIRECTION_REVERSE
from homeassistant.exceptions import HomeAssistantError

from custom_components.yeelight_pro.const import DOMAIN
from custom_components.yeelight_pro.fan import (
    ERROR_FAN_DIRECTION_PROJECTION_UNAVAILABLE,
    ERROR_FAN_MODE_PROJECTION_UNAVAILABLE,
    ERROR_FAN_PROJECTION_UNAVAILABLE,
    ERROR_FAN_SPEED_PROJECTION_UNAVAILABLE,
    YeelightProFan,
)


def _fan_payload() -> dict:
    """构造 schema-aware fan payload，覆盖 indexed control key."""
    return {
        "id": "12345",
        "device_id": "12345",
        "name": "吊扇",
        "category": "temp_control",
        "type": "fan",
        "online": True,
        "params": {
            "1-p": True,
            "1-lv": 3,
            "1-m": "sleep",
            "1-dir": 0,
        },
        "ha_device_instance": {
            "device_id": "12345",
            "name": "吊扇",
            "online": True,
            "device_info": {
                "identifiers": [[DOMAIN, "12345"]],
                "manufacturer": "Yeelight",
                "model": "ceiling-fan",
                "name": "吊扇",
            },
            "components": [
                {
                    "component_id": "fan_1",
                    "category": "fan",
                    "available": True,
                    "instance_capabilities": {
                        "constraints": {
                            "mode": {
                                "values": [
                                    {"code": "sleep"},
                                    {"code": "natural"},
                                ]
                            },
                            "direction": {
                                "values": [
                                    {"code": 0, "desc": "forward"},
                                    {"code": 1, "desc": "reverse"},
                                ]
                            },
                        }
                    },
                    "state": {
                        "p": True,
                        "lv": 3,
                        "m": "sleep",
                        "dir": 0,
                    },
                }
            ],
        },
        "ha_product_model": {
            "schema_version": "v1",
            "product": {
                "model_id": "fan-model",
                "manufacturer": "Yeelight",
                "model": "ceiling-fan",
                "category": "temp_control",
            },
            "components": [
                {
                    "component_id": "fan_1",
                    "category": "fan",
                    "properties": [
                        {"prop_id": "p"},
                        {
                            "prop_id": "lv",
                            "value_range": {"min": 1, "max": 6, "step": 1},
                        },
                        {
                            "prop_id": "m",
                            "value_list": [
                                {"code": "sleep"},
                                {"code": "natural"},
                            ],
                        },
                        {
                            "prop_id": "dir",
                            "value_list": [
                                {"code": 0, "desc": "forward"},
                                {"code": 1, "desc": "reverse"},
                            ],
                        },
                    ],
                }
            ],
        },
    }


def _assert_not_echoed(
    error: HomeAssistantError,
    *,
    expected: str,
    sensitive: str,
) -> None:
    """断言 HA service 错误不回显设备组件上下文."""
    message = str(error)
    formatted = "".join(
        traceback.format_exception(type(error), error, error.__traceback__)
    )

    assert expected in message
    assert sensitive not in message
    assert sensitive not in formatted


@pytest.mark.asyncio
async def test_turn_on_sends_power_speed_and_preset(mock_coordinator) -> None:
    """开启风扇时应按投影 key 下发电源、档位和模式."""
    mock_coordinator.get_device.return_value = _fan_payload()
    fan = YeelightProFan(mock_coordinator, "12345", component_id="fan_1")

    await fan.async_turn_on(percentage=50, preset_mode="natural")

    mock_coordinator.async_control_device.assert_awaited_once_with(
        "12345",
        {"1-p": True, "1-lv": 3, "1-m": "natural"},
    )


@pytest.mark.asyncio
async def test_turn_off_prefers_power_key(mock_coordinator) -> None:
    """关闭风扇优先使用电源 key，而不是只把档位写 0."""
    mock_coordinator.get_device.return_value = _fan_payload()
    fan = YeelightProFan(mock_coordinator, "12345", component_id="fan_1")

    await fan.async_turn_off()

    mock_coordinator.async_control_device.assert_awaited_once_with(
        "12345",
        {"1-p": False},
    )


@pytest.mark.asyncio
async def test_set_percentage_turns_off_at_zero(mock_coordinator) -> None:
    """百分比为 0 时应关闭电源，避免只写入无效档位。"""
    mock_coordinator.get_device.return_value = _fan_payload()
    fan = YeelightProFan(mock_coordinator, "12345", component_id="fan_1")

    await fan.async_set_percentage(0)

    mock_coordinator.async_control_device.assert_awaited_once_with(
        "12345",
        {"1-p": False},
    )


@pytest.mark.asyncio
async def test_set_percentage_turns_on_and_maps_range(mock_coordinator) -> None:
    """非 0 百分比应开机并按设备档位范围换算。"""
    mock_coordinator.get_device.return_value = _fan_payload()
    fan = YeelightProFan(mock_coordinator, "12345", component_id="fan_1")

    await fan.async_set_percentage(100)

    mock_coordinator.async_control_device.assert_awaited_once_with(
        "12345",
        {"1-lv": 6, "1-p": True},
    )


@pytest.mark.asyncio
async def test_set_preset_mode_turns_on_with_mode_key(mock_coordinator) -> None:
    """设置预设模式时应同时确保风扇打开."""
    mock_coordinator.get_device.return_value = _fan_payload()
    fan = YeelightProFan(mock_coordinator, "12345", component_id="fan_1")

    await fan.async_set_preset_mode("natural")

    mock_coordinator.async_control_device.assert_awaited_once_with(
        "12345",
        {"1-m": "natural", "1-p": True},
    )


@pytest.mark.asyncio
async def test_set_direction_uses_raw_vendor_value(mock_coordinator) -> None:
    """方向写入必须使用物模型原始值，不能把 HA 文本直接下发."""
    mock_coordinator.get_device.return_value = _fan_payload()
    fan = YeelightProFan(mock_coordinator, "12345", component_id="fan_1")

    await fan.async_set_direction(DIRECTION_REVERSE)

    assert fan.current_direction == DIRECTION_FORWARD
    mock_coordinator.async_control_device.assert_awaited_once_with(
        "12345",
        {"1-dir": "1"},
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method_name", "args", "expected"),
    [
        ("async_turn_on", (), ERROR_FAN_PROJECTION_UNAVAILABLE),
        ("async_turn_off", (), ERROR_FAN_PROJECTION_UNAVAILABLE),
        ("async_set_percentage", (50,), ERROR_FAN_SPEED_PROJECTION_UNAVAILABLE),
        ("async_set_preset_mode", ("sleep",), ERROR_FAN_MODE_PROJECTION_UNAVAILABLE),
        ("async_set_direction", (DIRECTION_FORWARD,), ERROR_FAN_DIRECTION_PROJECTION_UNAVAILABLE),
    ],
)
async def test_fan_service_without_projection_raises_ha_error_without_echoing_component(
    mock_coordinator,
    method_name: str,
    args: tuple,
    expected: str,
) -> None:
    """缺少风扇投影时错误不能泄露 component_id."""
    mock_coordinator.get_device.return_value = {"type": "light", "params": {}}
    fan = YeelightProFan(
        mock_coordinator,
        "12345",
        component_id="secret-token-fan-component",
    )
    method = getattr(fan, method_name)

    with pytest.raises(HomeAssistantError) as exc_info:
        await method(*args)

    _assert_not_echoed(
        exc_info.value,
        expected=expected,
        sensitive="secret-token-fan-component",
    )
    mock_coordinator.async_control_device.assert_not_awaited()
