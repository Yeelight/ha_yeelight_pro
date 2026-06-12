"""Fan entity service behavior tests."""
from __future__ import annotations

import traceback

import pytest

from homeassistant.components.fan import DIRECTION_FORWARD
from homeassistant.exceptions import HomeAssistantError

from custom_components.yeelight_pro.const import DOMAIN
from custom_components.yeelight_pro.fan import (
    ERROR_FAN_DIRECTION_PROJECTION_UNAVAILABLE,
    ERROR_FAN_MODE_PROJECTION_UNAVAILABLE,
    ERROR_FAN_PROJECTION_UNAVAILABLE,
    ERROR_FAN_SPEED_PROJECTION_UNAVAILABLE,
    YeelightProFan,
)


def _fresh_air_payload() -> dict:
    """构造易来新风 payload，覆盖官方 vmcp/vmcf 控制属性."""
    return {
        "id": "fresh-air-1",
        "device_id": "fresh-air-1",
        "name": "新风",
        "category": "temp_control",
        "type": "temp_control",
        "online": True,
        "params": {
            "1-vmcp": True,
            "1-vmcf": 20,
        },
        "ha_device_instance": {
            "device_id": "fresh-air-1",
            "name": "新风",
            "online": True,
            "device_info": {
                "identifiers": [[DOMAIN, "fresh-air-1"]],
                "manufacturer": "Yeelight",
                "model": "fresh-air",
                "name": "新风",
            },
            "extensions": {
                "component_state_keys": {
                    "fresh_air": {"vmcp": "1-vmcp", "vmcf": "1-vmcf"}
                }
            },
            "components": [
                {
                    "component_id": "fresh_air",
                    "category": "fresh air",
                    "available": True,
                    "state": {
                        "vmcp": True,
                        "vmcf": 20,
                    },
                }
            ],
        },
        "ha_product_model": {
            "schema_version": "v1",
            "product": {
                "model_id": "fresh-air-model",
                "manufacturer": "Yeelight",
                "model": "fresh-air",
                "category": "temp_control",
            },
            "components": [
                {
                    "component_id": "fresh_air",
                    "category": "fresh air",
                    "properties": [
                        {"prop_id": "vmcp"},
                        {
                            "prop_id": "vmcf",
                            "value_range": {"min": 1, "max": 100, "step": 1},
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
    """开启新风时只下发易来官方 vmcp/vmcf 控制属性。"""
    mock_coordinator.get_device.return_value = _fresh_air_payload()
    fan = YeelightProFan(mock_coordinator, "fresh-air-1", component_id="fresh_air")

    await fan.async_turn_on(percentage=50, preset_mode="natural")

    mock_coordinator.async_control_device.assert_awaited_once_with(
        "fresh-air-1",
        {"1-vmcp": True, "1-vmcf": 50},
    )


@pytest.mark.asyncio
async def test_turn_off_prefers_power_key(mock_coordinator) -> None:
    """关闭新风优先使用 vmcp，而不是只把风量写 0。"""
    mock_coordinator.get_device.return_value = _fresh_air_payload()
    fan = YeelightProFan(mock_coordinator, "fresh-air-1", component_id="fresh_air")

    await fan.async_turn_off()

    mock_coordinator.async_control_device.assert_awaited_once_with(
        "fresh-air-1",
        {"1-vmcp": False},
    )


@pytest.mark.asyncio
async def test_set_percentage_turns_off_at_zero(mock_coordinator) -> None:
    """百分比为 0 时应关闭新风开关，避免只写入无效风量。"""
    mock_coordinator.get_device.return_value = _fresh_air_payload()
    fan = YeelightProFan(mock_coordinator, "fresh-air-1", component_id="fresh_air")

    await fan.async_set_percentage(0)

    mock_coordinator.async_control_device.assert_awaited_once_with(
        "fresh-air-1",
        {"1-vmcp": False},
    )


@pytest.mark.asyncio
async def test_set_percentage_turns_on_and_maps_range(mock_coordinator) -> None:
    """非 0 百分比应开启新风并写入 vmcf。"""
    mock_coordinator.get_device.return_value = _fresh_air_payload()
    fan = YeelightProFan(mock_coordinator, "fresh-air-1", component_id="fresh_air")

    await fan.async_set_percentage(100)

    mock_coordinator.async_control_device.assert_awaited_once_with(
        "fresh-air-1",
        {"1-vmcf": 100, "1-vmcp": True},
    )


@pytest.mark.asyncio
async def test_fresh_air_uses_documented_vmcp_vmcf_control_keys(
    mock_coordinator,
) -> None:
    """新风 fan 实体必须下发易来官方 vmcp/vmcf 属性."""
    mock_coordinator.get_device.return_value = _fresh_air_payload()
    fan = YeelightProFan(mock_coordinator, "fresh-air-1", component_id="fresh_air")

    await fan.async_set_percentage(55)
    await fan.async_turn_off()

    assert mock_coordinator.async_control_device.await_args_list == [
        (("fresh-air-1", {"1-vmcf": 55, "1-vmcp": True}),),
        (("fresh-air-1", {"1-vmcp": False}),),
    ]


@pytest.mark.asyncio
async def test_fresh_air_rejects_unsupported_preset_mode(mock_coordinator) -> None:
    """易来新风文档只有 vmcp/vmcf，不应暴露旧 fan 模式写入。"""
    mock_coordinator.get_device.return_value = _fresh_air_payload()
    fan = YeelightProFan(mock_coordinator, "fresh-air-1", component_id="fresh_air")

    with pytest.raises(HomeAssistantError) as exc_info:
        await fan.async_set_preset_mode("natural")

    assert str(exc_info.value) == ERROR_FAN_MODE_PROJECTION_UNAVAILABLE
    mock_coordinator.async_control_device.assert_not_awaited()


@pytest.mark.asyncio
async def test_fresh_air_rejects_unsupported_direction(mock_coordinator) -> None:
    """易来新风文档没有 direction 属性，不应暴露旧 fan 方向写入。"""
    mock_coordinator.get_device.return_value = _fresh_air_payload()
    fan = YeelightProFan(mock_coordinator, "fresh-air-1", component_id="fresh_air")

    with pytest.raises(HomeAssistantError) as exc_info:
        await fan.async_set_direction(DIRECTION_FORWARD)

    assert str(exc_info.value) == ERROR_FAN_DIRECTION_PROJECTION_UNAVAILABLE
    mock_coordinator.async_control_device.assert_not_awaited()


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
