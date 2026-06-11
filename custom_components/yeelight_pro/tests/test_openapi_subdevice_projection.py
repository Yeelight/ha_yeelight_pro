"""OpenAPI subDeviceList projection regressions."""

from __future__ import annotations

import pytest

from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode

from custom_components.yeelight_pro.const import DOMAIN
from custom_components.yeelight_pro.entity_candidates import iter_device_entity_candidates
from .openapi_subdevice_helpers import build_openapi_device as _build_device
from .openapi_subdevice_helpers import openapi_prop as _prop
from custom_components.yeelight_pro.light import YeelightProLight
from custom_components.yeelight_pro.projector.event import project_events
from custom_components.yeelight_pro.projector.light import project_lights


def test_openapi_subdevice_lights_project_multiple_light_entities() -> None:
    """多路 OpenAPI light 子设备必须生成多个 light，并保留控制能力。"""
    device = _build_device(
        {
            "id": 9001,
            "name": "客厅多路灯",
            "category": "light",
            "roomId": "room-1",
            "subDeviceList": [
                {
                    "index": 1,
                    "name": "color temperature light",
                    "category": "light",
                    "desc": "主灯",
                    "properties": [
                        _prop("p", True, "开关", "boolean", operators=["set", "toggle"]),
                        _prop("l", 80, "亮度", "uint8", unit="%", operators=["set", "adjust"]),
                        _prop(
                            "ct",
                            4000,
                            "色温",
                            "uint16",
                            unit="k",
                            range_={"min": 2700, "max": 6500, "step": 1},
                            operators=["set", "adjust"],
                        ),
                    ],
                },
                {
                    "index": 2,
                    "name": "color light",
                    "category": "light",
                    "desc": "氛围灯",
                    "properties": [
                        _prop("p", False, "开关", "boolean", operators=["set"]),
                        _prop("l", 30, "亮度", "uint8", unit="%", operators=["set"]),
                        _prop("c", 0x336699, "颜色", "uint32", operators=["set"]),
                    ],
                },
            ],
        }
    )

    lights = project_lights(device, domain=DOMAIN)
    candidates = {
        (item.platform, item.unique_id)
        for item in iter_device_entity_candidates(device)
    }

    assert [light.component_id for light in lights] == ["light_1", "light_2"]
    assert [light.name for light in lights] == ["主灯", "氛围灯"]
    assert lights[0].supported_color_modes == {ColorMode.COLOR_TEMP}
    assert lights[0].brightness == 203
    assert lights[0].color_temp == 250
    assert lights[0].power_key == "1-p"
    assert lights[0].brightness_key == "1-l"
    assert lights[0].color_temp_key == "1-ct"
    assert lights[0].device_info is not None
    assert lights[0].device_info["suggested_area"] == "客厅"
    assert lights[1].supported_color_modes == {ColorMode.RGB}
    assert lights[1].rgb_color == (0x33, 0x66, 0x99)
    assert ("light", "yeelight_pro_9001_light_1") in candidates
    assert ("light", "yeelight_pro_9001_light_2") in candidates


def test_openapi_subdevice_lights_use_channel_names_without_component_desc() -> None:
    """多路 light 没有组件描述时，应显示友好的第 N 路而不是照明/裸数字."""
    device = _build_device(
        {
            "id": 9018,
            "name": "走廊双路灯",
            "category": "light",
            "subDeviceList": [
                {
                    "index": 1,
                    "category": "light",
                    "properties": [
                        _prop("p", True, "开关", "boolean", operators=["set"]),
                    ],
                },
                {
                    "index": 2,
                    "category": "light",
                    "properties": [
                        _prop("p", False, "开关", "boolean", operators=["set"]),
                    ],
                },
            ],
        }
    )

    lights = project_lights(device, domain=DOMAIN)

    assert [light.component_id for light in lights] == ["light_1", "light_2"]
    assert [light.name for light in lights] == ["第 1 路", "第 2 路"]


def test_openapi_subdevice_component_metadata_reaches_runtime_instance() -> None:
    """子设备名称、描述和 index 必须保留给 HA 实体命名和控制键解析."""
    device = _build_device(
        {
            "id": 9017,
            "name": "玄关双键开关",
            "category": "relay_switch",
            "subDeviceList": [
                {
                    "index": 1,
                    "name": "left key",
                    "desc": "左键",
                    "category": "relay_switch",
                    "properties": [_prop("p", True, "开关", "boolean", operators=["set"])],
                },
                {
                    "index": 2,
                    "name": "right key",
                    "desc": "右键",
                    "category": "relay_switch",
                    "properties": [_prop("p", False, "开关", "boolean", operators=["set"])],
                },
            ],
        }
    )

    components = device["ha_device_instance"]["components"]
    candidates = {
        (item.platform, item.component_id, item.name)
        for item in iter_device_entity_candidates(device)
    }

    assert [
        (item["component_id"], item["name"], item["desc"], item["index"])
        for item in components
    ] == [
        ("switch_1", "left key", "左键", 1),
        ("switch_2", "right key", "右键", 2),
    ]
    assert candidates == {
        ("switch", "switch_1", "左键"),
        ("switch", "switch_2", "右键"),
    }


def test_openapi_subdevice_numeric_names_are_humanized() -> None:
    """OpenAPI 子设备名称为 1/2/3 时，HA 设备详情应显示左/中/右键."""
    device = _build_device(
        {
            "id": 9018,
            "name": "玄关三键智能开关",
            "category": "relay_switch",
            "subDeviceList": [
                {
                    "index": 1,
                    "name": "1",
                    "desc": "1",
                    "category": "relay_switch",
                    "properties": [_prop("p", True, "开关", "boolean", operators=["set"])],
                },
                {
                    "index": 2,
                    "name": "2",
                    "desc": "2",
                    "category": "relay_switch",
                    "properties": [_prop("p", False, "开关", "boolean", operators=["set"])],
                },
                {
                    "index": 3,
                    "name": "3",
                    "desc": "3",
                    "category": "relay_switch",
                    "properties": [_prop("p", True, "开关", "boolean", operators=["set"])],
                },
            ],
        }
    )

    candidates = [
        (item.platform, item.component_id, item.name)
        for item in iter_device_entity_candidates(device)
    ]

    assert candidates == [
        ("switch", "switch_1", "左键"),
        ("switch", "switch_2", "中键"),
        ("switch", "switch_3", "右键"),
    ]


def test_openapi_scene_panel_numeric_channels_are_humanized() -> None:
    """设备名只有“按键”时，scene panel 子设备也应按索引显示友好通道名."""
    device = _build_device(
        {
            "id": 9019,
            "name": "按键",
            "category": "scene_panel",
            "subDeviceList": [
                {"index": 1, "name": "1", "desc": "1", "category": "scene_panel"},
                {"index": 2, "name": "2", "desc": "2", "category": "scene_panel"},
                {"index": 3, "name": "3", "desc": "3", "category": "scene_panel"},
            ],
            "events": [
                {"id": "65793", "name": "key1 click", "desc": "按钮1点击事件"},
                {"id": "66049", "name": "key2 click", "desc": "按钮2点击事件"},
                {"id": "66305", "name": "key3 click", "desc": "按钮3点击事件"},
            ],
        }
    )

    candidates = [
        (item.platform, item.component_id, item.name)
        for item in iter_device_entity_candidates(device)
    ]

    assert candidates == [
        ("event", "scene_panel_1", "左键事件"),
        ("event", "scene_panel_2", "中键事件"),
        ("event", "scene_panel_3", "右键事件"),
    ]


@pytest.mark.asyncio
async def test_openapi_subdevice_light_entity_uses_indexed_control_keys(
    mock_coordinator,
) -> None:
    """HA light 子实体控制应使用对应子设备 indexed keys。"""
    device = _build_device(
        {
            "id": 9002,
            "name": "餐厅多路灯",
            "category": "light",
            "subDeviceList": [
                {
                    "index": 2,
                    "category": "light",
                    "properties": [
                        _prop("p", False, "开关", "boolean", operators=["set"]),
                        _prop("l", 30, "亮度", "uint8", unit="%", operators=["set"]),
                    ],
                }
            ],
        }
    )
    mock_coordinator.get_device.return_value = device
    light = YeelightProLight(mock_coordinator, 9002, component_id="light_2")

    await light.async_turn_on(**{ATTR_BRIGHTNESS: 128})

    mock_coordinator.async_control_device.assert_awaited_once_with(
        9002,
        {"2-p": True, "2-l": 51},
    )


def test_openapi_subdevice_scene_panel_events_are_scoped_by_key_index() -> None:
    """顶层 keyN 事件必须归属到对应 scene_panel 子组件。"""
    device = _build_device(
        {
            "id": 9003,
            "name": "八键面板",
            "category": "scene_panel",
            "subDeviceList": [
                {"index": 1, "name": "scene control button", "category": "scene_panel"},
                {"index": 2, "name": "scene control button", "category": "scene_panel"},
            ],
            "events": [
                {"id": "65793", "name": "key1 click", "desc": "按钮1点击事件"},
                {"id": "258", "name": "key1 hold", "desc": "按钮1长按事件"},
                {"id": "66049", "name": "key2 click", "desc": "按钮2点击事件"},
            ],
        }
    )

    events = project_events(device, domain=DOMAIN)
    by_component = {event.component_id: event for event in events}

    assert set(by_component) == {"scene_panel_1", "scene_panel_2"}
    assert by_component["scene_panel_1"].event_types == ["click", "hold"]
    assert by_component["scene_panel_2"].event_types == ["click"]


def test_openapi_subdevice_sensor_properties_create_sensor_entities() -> None:
    """传感器子设备属性应映射为 HA sensor/binary_sensor 候选。"""
    device = _build_device(
        {
            "id": 9004,
            "name": "走廊人体传感器",
            "category": "human_sensor",
            "subDeviceList": [
                {
                    "index": 1,
                    "name": "human body infrared sensor",
                    "category": "human_sensor",
                    "properties": [
                        _prop("mv", True, "人体移动", "boolean"),
                        _prop("luminance", 321, "照度", "uint16", unit="lx"),
                        _prop("bl", 88, "电量", "uint8", unit="%"),
                    ],
                }
            ],
        }
    )

    candidates = {
        (item.platform, item.component_id)
        for item in iter_device_entity_candidates(device)
    }

    assert candidates == {
        ("binary_sensor", "motion"),
        ("sensor", "illuminance"),
        ("sensor", "battery"),
    }
