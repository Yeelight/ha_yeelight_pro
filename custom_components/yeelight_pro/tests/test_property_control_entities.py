"""HA entity behavior for schema-backed writable property controls."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from homeassistant.const import EntityCategory

from custom_components.yeelight_pro.number import YeelightProDeviceNumber
from custom_components.yeelight_pro.device_select import YeelightProDeviceSelect
from custom_components.yeelight_pro.switch import YeelightProSwitch

from .test_property_control_projection import _property_control_payload


def _official_two_key_property_control_payload() -> dict:
    """Build a payload whose channel layout comes from official product evidence."""
    payload = _property_control_payload()
    payload["pid"] = 854018
    payload["ha_device_instance"]["extensions"] = {
        "component_state_keys": {
            "curtain_1": {
                "li": "1-li",
                "rd": "1-rd",
                "rg": "1-rg",
                "tra": "1-tra",
            }
        }
    }
    return payload


def test_device_number_suggests_friendly_object_id(mock_coordinator) -> None:
    """设备级 number 配置实体也应使用设备名和属性名生成 entity_id."""
    payload = _official_two_key_property_control_payload()
    mock_coordinator.get_device.return_value = payload

    number = YeelightProDeviceNumber(
        mock_coordinator,
        "curtain-1",
        component_id="curtain_1_rg_number",
    )

    assert number.suggested_object_id == "厨房双键开关 左键 旋转档位"


def test_device_select_suggests_friendly_object_id(mock_coordinator) -> None:
    """设备级 select 配置实体也应使用设备名和属性名生成 entity_id."""
    payload = _official_two_key_property_control_payload()
    mock_coordinator.get_device.return_value = payload

    select = YeelightProDeviceSelect(
        mock_coordinator,
        "curtain-1",
        component_id="curtain_1_rd_select",
    )

    assert select.suggested_object_id == "厨房双键开关 左键 电机方向"


@pytest.mark.asyncio
async def test_device_number_write_sends_indexed_control_key(mock_coordinator) -> None:
    """设备级 number 写入应下发 schema control key."""
    mock_coordinator.get_device.return_value = _official_two_key_property_control_payload()
    mock_coordinator.async_control_device = AsyncMock()
    number = YeelightProDeviceNumber(
        mock_coordinator,
        12345,
        component_id="curtain_1_rg_number",
    )

    assert number.name == "左键 旋转档位"
    assert number.native_value == 4
    assert number.entity_category == EntityCategory.CONFIG

    await number.async_set_native_value(90)

    mock_coordinator.async_control_device.assert_awaited_once_with(
        12345,
        {"1-rg": 90},
    )


@pytest.mark.asyncio
async def test_device_select_write_sends_raw_option_code(mock_coordinator) -> None:
    """设备级 select 选择标签后应下发对应 raw code."""
    mock_coordinator.get_device.return_value = _official_two_key_property_control_payload()
    mock_coordinator.async_control_device = AsyncMock()
    select = YeelightProDeviceSelect(
        mock_coordinator,
        12345,
        component_id="curtain_1_rd_select",
    )

    assert select.options == ["正向", "反向"]
    assert select.current_option == "正向"
    assert select.entity_category == EntityCategory.CONFIG

    await select.async_select_option("反向")

    mock_coordinator.async_control_device.assert_awaited_once_with(
        12345,
        {"1-rd": "1"},
    )


@pytest.mark.asyncio
async def test_device_switch_write_sends_int_values_for_indicator_switch(
    mock_coordinator,
) -> None:
    """int 型开关语义配置项应按 Yeelight 原始 1/0 写入."""
    payload = _official_two_key_property_control_payload()
    mock_coordinator.get_device.return_value = payload
    mock_coordinator.async_control_device = AsyncMock()
    switch = YeelightProSwitch(
        mock_coordinator,
        12345,
        component_id="curtain_1_li_switch",
    )

    assert switch.name == "左键 指示灯"
    assert switch.is_on is True
    assert switch.entity_category == EntityCategory.CONFIG

    await switch.async_turn_off()
    await switch.async_turn_on()

    assert mock_coordinator.async_control_device.await_args_list == [
        ((12345, {"1-li": 0}),),
        ((12345, {"1-li": 1}),),
    ]
