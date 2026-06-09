"""Group number control-key tests."""
from __future__ import annotations

import pytest

from custom_components.yeelight_pro.number import (
    YeelightProGroupBrightness,
    YeelightProGroupColorTemp,
)


@pytest.mark.asyncio
async def test_group_brightness_number_uses_iot_property_key(mock_coordinator) -> None:
    """灯组亮度控制必须发送 Yeelight IoT 属性缩写 l."""
    entity = YeelightProGroupBrightness(mock_coordinator, "group_1", "一楼灯组")
    entity.async_write_ha_state = lambda: None

    await entity.async_set_native_value(42)

    mock_coordinator.async_control_group.assert_awaited_once_with(
        "group_1",
        {"l": 42},
    )


@pytest.mark.asyncio
async def test_group_color_temp_number_uses_iot_property_key(mock_coordinator) -> None:
    """灯组色温控制必须发送 Yeelight IoT 属性缩写 ct."""
    entity = YeelightProGroupColorTemp(mock_coordinator, "group_1", "一楼灯组")
    entity.async_write_ha_state = lambda: None

    await entity.async_set_native_value(4100)

    mock_coordinator.async_control_group.assert_awaited_once_with(
        "group_1",
        {"ct": 4100},
    )
