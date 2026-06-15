"""OpenAPI subDeviceList event projection regressions."""

from __future__ import annotations

from custom_components.yeelight_pro.const import DOMAIN
from custom_components.yeelight_pro.entity_candidates import iter_device_entity_candidates
from custom_components.yeelight_pro.projector.event import (
    project_device_triggers,
    project_events,
)
from custom_components.yeelight_pro.projector.switch import project_switches
from homeassistant.components.event import EventDeviceClass

from .openapi_subdevice_helpers import build_openapi_device as _build_device
from .openapi_subdevice_helpers import openapi_prop as _prop


def test_openapi_user_component_name_does_not_override_relay_switch_category() -> None:
    """runtime 子设备显示名不能把 relay_switch 误识别为事件输入组件。"""
    device = _build_device(
        {
            "id": 9022,
            "name": "玄关开关",
            "category": "relay_switch",
            "subDeviceList": [
                {
                    "index": 1,
                    "name": "情景按键",
                    "desc": "scene control button",
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

    assert device["ha_product_model"]["schema_version"] == "runtime-v1"
    assert candidates == [("switch", "switch_1", "回路 1")]
    assert project_events(device, domain=DOMAIN) == []


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
    assert by_component["scene_panel_1"].name == "左键事件"
    assert by_component["scene_panel_2"].name == "右键事件"


def test_openapi_eight_key_scene_panel_uses_friendly_event_names() -> None:
    """开放平台八键面板示例应显示按键 N 事件，不暴露裸数字或组件英文名."""
    device = _build_device(
        {
            "id": 9008,
            "name": "公开测试八键情景开关",
            "category": "scene_panel",
            "subDeviceList": [
                {
                    "index": index,
                    "name": "scene control button",
                    "desc": "情景按键",
                    "category": "scene_panel",
                }
                for index in range(1, 9)
            ],
            "events": [
                *(
                    {
                        "id": str(65537 + index * 256),
                        "name": f"key{index} click",
                        "desc": f"按钮{index}点击事件",
                    }
                    for index in range(1, 9)
                ),
                *(
                    {
                        "id": str(index * 256 + 2),
                        "name": f"key{index} hold",
                        "desc": f"按钮{index}长按事件",
                    }
                    for index in range(1, 9)
                ),
            ],
        }
    )

    events = project_events(device, domain=DOMAIN)

    assert [event.component_id for event in events] == [
        f"scene_panel_{index}" for index in range(1, 9)
    ]
    assert [event.name for event in events] == [
        f"按键 {index} 事件" for index in range(1, 9)
    ]
    assert all(event.event_types == ["click", "hold"] for event in events)


def test_openapi_scene_panel_projects_events_and_battery_without_switch_leak() -> None:
    """八键面板按文档生成事件和诊断实体，顶层 p 不能泄漏成普通开关。"""
    device = _build_device(
        {
            "id": 9010,
            "name": "八键面板",
            "category": "scene_panel",
            "properties": [
                _prop("bc", False, "是否可充电", "boolean"),
                _prop("bcg", False, "电池正在充电", "boolean"),
                _prop("bl", 88, "电量", "uint8", unit="%"),
                _prop("o", True, "在线", "boolean"),
                _prop("p", False, "开关", "boolean", operators=["set", "toggle"]),
            ],
            "subDeviceList": [
                {
                    "index": index,
                    "name": "scene control button",
                    "desc": "情景按键",
                    "category": "scene_panel",
                }
                for index in range(1, 9)
            ],
            "events": [
                *(
                    {
                        "id": str(65537 + index * 256),
                        "name": f"key{index} click",
                        "desc": f"按钮{index}点击事件",
                    }
                    for index in range(1, 9)
                ),
                *(
                    {
                        "id": str(index * 256 + 2),
                        "name": f"key{index} hold",
                        "desc": f"按钮{index}长按事件",
                    }
                    for index in range(1, 9)
                ),
            ],
        }
    )

    candidates = [
        (item.platform, item.component_id, item.name, item.entity_category)
        for item in iter_device_entity_candidates(device)
    ]

    assert device["category"] == "scene_panel"
    assert device["effective_category"] == "scene_panel"
    assert project_switches(device, domain=DOMAIN) == []
    assert candidates[:3] == [
        ("sensor", "battery", "电量", "diagnostic"),
        ("binary_sensor", "battery_chargeable", "电池可充电", "diagnostic"),
        ("binary_sensor", "battery_charging", "电池充电", "diagnostic"),
    ]
    assert candidates[3:] == [
        ("event", f"scene_panel_{index}", f"按键 {index} 事件", None)
        for index in range(1, 9)
    ]


def test_openapi_occupancy_subdevice_uses_registry_events_without_payload_events() -> None:
    """OpenAPI 缺少 events 行时，cid=9 的人在传感器仍应暴露官方 motion 事件。"""
    device = _build_device(
        {
            "id": 9031,
            "name": "用户自定义烟雾传感器",
            "category": "human_sensor",
            "subDeviceList": [
                {
                    "index": 1,
                    "cid": 9,
                    "name": "用户自定义组件名",
                    "category": "human_sensor",
                    "properties": [_prop("mv", True, "有人经过", "boolean")],
                },
            ],
        }
    )

    events = project_events(device, domain=DOMAIN)

    assert len(events) == 1
    assert events[0].component_id == "binary_sensor_1"
    assert events[0].event_types == ["motion_detected", "motion_undetected"]
    assert events[0].device_class == EventDeviceClass.MOTION
    assert events[0].icon == "mdi:motion-sensor"
    assert [trigger.subtype for trigger in project_device_triggers(device)] == [
        "motion_detected",
        "motion_undetected",
    ]


def test_openapi_contact_subdevice_uses_unique_registry_category_events() -> None:
    """门磁 category+属性唯一命中官方组件时，应补齐接触/告警事件。"""
    device = _build_device(
        {
            "id": 9032,
            "name": "门磁",
            "category": "contact_sensor",
            "subDeviceList": [
                {
                    "index": 1,
                    "name": "用户自定义组件名",
                    "category": "contact_sensor",
                    "properties": [
                        _prop("dc", False, "是否接触", "boolean"),
                        _prop("alm", False, "告警", "boolean"),
                    ],
                },
            ],
        }
    )

    events = project_events(device, domain=DOMAIN)

    assert len(events) == 1
    assert events[0].event_types == [
        "door_open",
        "door_close",
        "door_alarm",
        "door_normal",
    ]
    assert events[0].icon == "mdi:door"


def test_openapi_human_category_without_component_identity_does_not_guess_events() -> None:
    """human_sensor 大类存在多个官方事件组件，缺少 cid 时不能靠大类猜事件。"""
    device = _build_device(
        {
            "id": 9033,
            "name": "人体传感器",
            "category": "human_sensor",
            "subDeviceList": [
                {
                    "index": 1,
                    "name": "用户写的人在传感器",
                    "category": "human_sensor",
                    "properties": [_prop("mv", True, "有人经过", "boolean")],
                },
            ],
        }
    )

    assert project_events(device, domain=DOMAIN) == []
