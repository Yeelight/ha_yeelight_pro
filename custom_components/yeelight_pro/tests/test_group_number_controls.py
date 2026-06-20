"""Group number control-key tests."""
from __future__ import annotations

from types import MethodType

import pytest

from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.core.coordinator import YeelightProCoordinator
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


@pytest.mark.asyncio
async def test_group_number_entities_refresh_from_group_push(hass: HomeAssistant) -> None:
    """灯组亮度/色温 number 应随 WebSocket 灯组推送即时刷新."""
    coordinator = YeelightProCoordinator(hass=hass, client=None, house_id=12345)
    coordinator.groups = [
        {"id": 8001, "name": "客厅灯组", "params": {"l": 20, "ct": 3000}},
    ]
    brightness = YeelightProGroupBrightness(coordinator, "8001", "客厅灯组")
    color_temp = YeelightProGroupColorTemp(coordinator, "8001", "客厅灯组")
    updates = 0

    def _handle_update(_self: YeelightProGroupBrightness) -> None:
        nonlocal updates
        updates += 1

    brightness._handle_coordinator_update = MethodType(_handle_update, brightness)
    remove_listener = coordinator.async_add_listener(
        brightness._handle_coordinator_update,
        brightness.coordinator_context,
    )

    try:
        assert brightness.native_value == 20
        assert color_temp.native_value == 3000

        await coordinator.async_handle_push_payload(
            {
                "type": "prop",
                "nodes": [
                    {
                        "id": 8001,
                        "nt": 4,
                        "params": {"l": 45, "ct": 4200},
                    }
                ],
            }
        )

        assert updates == 1
        assert brightness.native_value == 45
        assert color_temp.native_value == 4200
        assert coordinator.last_push_property_summary.affected_contexts == (
            ("group", "8001"),
        )
    finally:
        remove_listener()
