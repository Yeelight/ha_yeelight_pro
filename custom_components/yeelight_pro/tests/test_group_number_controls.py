"""Group number control-key tests."""
from __future__ import annotations

import pytest

from custom_components.yeelight_pro.identity import entry_identity_scope, scoped_house_identifier
from custom_components.yeelight_pro.number import (
    YeelightProGroupBrightness,
    YeelightProGroupColorTemp,
)


@pytest.mark.asyncio
async def test_group_brightness_number_uses_iot_property_key(mock_coordinator) -> None:
    """灯组亮度控制必须发送 Yeelight IoT 属性缩写 l."""
    mock_coordinator.entry_data = {"house_name": "House 12345"}
    mock_coordinator.houses = [{"id": 5001, "name": "绿地中央公园"}]
    entity = YeelightProGroupBrightness(mock_coordinator, "group_1", "一楼灯组")
    entity.async_write_ha_state = lambda: None

    await entity.async_set_native_value(42)

    mock_coordinator.async_control_group.assert_awaited_once_with(
        "group_1",
        {"l": 42},
    )
    scope = entry_identity_scope(mock_coordinator.entry_data, mock_coordinator.house_id)
    assert entity.device_info["identifiers"] == {
        ("yeelight_pro", scoped_house_identifier(scope, mock_coordinator.house_id)),
    }
    assert entity.device_info["name"] == "绿地中央公园 灯组"


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
