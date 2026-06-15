"""Yeelight Pro 灯组 light entity tests."""
from __future__ import annotations

import pytest

from homeassistant.components.light import ATTR_TRANSITION, ColorMode

from custom_components.yeelight_pro.light_group import YeelightProGroupLight


@pytest.mark.asyncio
async def test_group_light_turn_on_maps_ha_brightness_to_iot_percent(mock_coordinator) -> None:
    """灯组 light 开灯时应把 HA 亮度转换为 Yeelight l 百分比。"""
    mock_coordinator.groups = [
        {
            "id": "group_1",
            "name": "客厅灯组",
            "online": True,
            "params": {"p": False, "l": 50, "ct": 4000},
        }
    ]
    entity = YeelightProGroupLight(mock_coordinator, "group_1")

    await entity.async_turn_on(brightness=128, color_temp_kelvin=4100)

    mock_coordinator.async_control_group.assert_awaited_once_with(
        "group_1",
        {"p": True, "l": 50, "ct": 4100},
    )


@pytest.mark.asyncio
async def test_group_light_turn_off_uses_group_control(mock_coordinator) -> None:
    """灯组 light 关灯应通过灯组控制 API 下发 p=false。"""
    mock_coordinator.groups = [{"id": "group_1", "name": "客厅灯组"}]
    entity = YeelightProGroupLight(mock_coordinator, "group_1")

    await entity.async_turn_off()

    mock_coordinator.async_control_group.assert_awaited_once_with(
        "group_1",
        {"p": False},
    )


@pytest.mark.asyncio
async def test_group_light_passes_transition_duration(mock_coordinator) -> None:
    """灯组 light 应把 HA transition 透传为易来 duration。"""
    mock_coordinator.groups = [
        {"id": "group_1", "name": "客厅灯组", "params": {"p": False, "l": 50}}
    ]
    entity = YeelightProGroupLight(mock_coordinator, "group_1")

    await entity.async_turn_on(**{ATTR_TRANSITION: 1.25})
    await entity.async_turn_off(**{ATTR_TRANSITION: 0.5})

    assert mock_coordinator.async_control_group.await_args_list[0].kwargs == {
        "duration": 1250
    }
    assert mock_coordinator.async_control_group.await_args_list[1].kwargs == {
        "duration": 500
    }


def test_group_light_exposes_runtime_state_and_house_device_info(mock_coordinator) -> None:
    """灯组 light 应展示灯组状态，并挂到 LAN 整屋辅助设备下。"""
    mock_coordinator.entry_data = {"house_name": "House 12345"}
    mock_coordinator.houses = [{"id": 5001, "name": "绿地中央公园"}]
    mock_coordinator.groups = [
        {
            "id": "group_1",
            "name": "客厅灯组",
            "online": True,
            "params": {"p": True, "l": 50, "ct": 4100},
        }
    ]
    entity = YeelightProGroupLight(mock_coordinator, "group_1")

    assert entity.name == "客厅灯组"
    assert entity.available is True
    assert entity.is_on is True
    assert entity.brightness == 128
    assert entity.color_temp_kelvin == 4100
    assert entity.supported_color_modes == {ColorMode.COLOR_TEMP}
    assert entity.device_info["name"] == "绿地中央公园 灯组"


@pytest.mark.asyncio
async def test_group_light_supports_rgb_only_with_color_param(mock_coordinator) -> None:
    """灯组只有在 params 含 c 时才暴露并控制 RGB。"""
    mock_coordinator.groups = [
        {
            "id": "group_1",
            "name": "客厅灯组",
            "online": True,
            "params": {"p": True, "l": 50, "ct": 4100, "c": 0x112233, "m": 1},
        }
    ]
    entity = YeelightProGroupLight(mock_coordinator, "group_1")

    assert entity.rgb_color == (0x11, 0x22, 0x33)
    assert entity.supported_color_modes == {ColorMode.COLOR_TEMP, ColorMode.RGB}
    assert entity.color_mode == ColorMode.RGB

    await entity.async_turn_on(rgb_color=(0x44, 0x55, 0x66))

    mock_coordinator.async_control_group.assert_awaited_once_with(
        "group_1",
        {"p": True, "c": 0x445566},
    )
