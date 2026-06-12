"""Yeelight Pro event projector boundary tests."""

from __future__ import annotations

from homeassistant.components.event import EventDeviceClass

from custom_components.yeelight_pro.projector.event import (
    project_device_triggers,
    project_events,
)
from custom_components.yeelight_pro.projector.switch import project_switches

from .projection_helpers import DOMAIN, projection_payload


def test_switch_control_with_declared_panel_events_projects_switch_and_events() -> None:
    """开关组件声明 click/hold 时应同时保留 switch 控制和事件入口。"""
    device = projection_payload(
        device_id="switch-event-1",
        category="relay_switch",
        component_id="relay_switch_1",
        state={"p": True},
        component_category="relay_switch",
        product_events=[
            {"event_id": 1, "name": "panel.click"},
            {"event_id": 2, "name": "panel.hold"},
        ],
    )
    component = device["ha_product_model"]["components"][0]
    component["cid"] = 20
    component["name"] = "switch control"

    switches = project_switches(device, domain=DOMAIN)
    events = project_events(device, domain=DOMAIN)
    triggers = project_device_triggers(device)

    assert [item.component_id for item in switches] == ["relay_switch_1"]
    assert switches[0].control_key == "1-p"
    assert len(events) == 1
    assert events[0].component_id == "relay_switch_1"
    assert events[0].event_types == ["click", "hold"]
    assert events[0].device_class == EventDeviceClass.BUTTON
    assert events[0].icon == "mdi:gesture-tap-button"
    assert [(trigger.type, trigger.subtype) for trigger in triggers] == [
        ("relay_switch_1", "click"),
        ("relay_switch_1", "hold"),
    ]


def test_wireless_switch_channel_with_declared_panel_events_projects_both() -> None:
    """无线开关通道声明 click/hold 时也应生成事件入口。"""
    device = projection_payload(
        device_id="wireless-switch-event-1",
        category="relay_switch",
        component_id="relay_switch_1",
        state={"sp": False, "l": 30},
        component_category="relay_switch",
        product_events=[
            {"event_id": 1, "name": "panel.click"},
            {"event_id": 2, "name": "panel.hold"},
        ],
    )
    component = device["ha_product_model"]["components"][0]
    component["cid"] = 16
    component["name"] = "wireless switch channel"

    switches = project_switches(device, domain=DOMAIN)
    events = project_events(device, domain=DOMAIN)

    assert [item.component_id for item in switches] == ["relay_switch_1"]
    assert switches[0].control_key == "1-sp"
    assert switches[0].is_on is False
    assert len(events) == 1
    assert events[0].event_types == ["click", "hold"]


def test_schema_declared_sensor_events_project_event_and_trigger() -> None:
    """schema 明确声明的传感器事件应进入 event entity 和 device trigger。"""
    device = projection_payload(
        device_id="human-approach-1",
        category="human_sensor",
        component_id="human_body_infrared_sensor",
        state={"mv": True, "luminance": 20},
        component_category="human body infrared sensor",
        product_events=[
            {"event_id": 8, "name": "motion.true"},
            {"event_id": 9, "name": "motion.false"},
            {"event_id": 22, "name": "approach.true"},
            {"event_id": 23, "name": "approach.false"},
        ],
    )

    events = project_events(device, domain=DOMAIN)
    triggers = project_device_triggers(device)

    assert len(events) == 1
    assert events[0].component_id == "human_body_infrared_sensor"
    assert events[0].event_types == [
        "motion_detected",
        "motion_undetected",
        "human_enter",
        "human_leave",
    ]
    assert [trigger.subtype for trigger in triggers] == events[0].event_types


def test_occupancy_sensor_motion_events_project_event_and_trigger() -> None:
    """人在传感器 schema 明确声明 motion 事件时应暴露自动化入口。"""
    device = projection_payload(
        device_id="occupancy-event-1",
        category="human_sensor",
        component_id="human_occupancy_sensor",
        state={"mv": True},
        component_category="human occupancy sensor",
        product_events=[
            {"event_id": 8, "name": "motion.true"},
            {"event_id": 9, "name": "motion.false"},
        ],
    )

    events = project_events(device, domain=DOMAIN)

    assert len(events) == 1
    assert events[0].component_id == "human_occupancy_sensor"
    assert events[0].event_types == ["motion_detected", "motion_undetected"]
    assert events[0].device_class == EventDeviceClass.MOTION
    assert [trigger.subtype for trigger in project_device_triggers(device)] == [
        "motion_detected",
        "motion_undetected",
    ]


def test_contact_sensor_declared_events_project_event_and_trigger() -> None:
    """门磁 schema 声明的 open/close/alarm/normal 应暴露自动化入口。"""
    device = projection_payload(
        device_id="contact-event-1",
        category="contact_sensor",
        component_id="contact_sensor",
        state={"dc": False, "alm": True},
        component_category="contact sensor",
        product_events=[
            {"event_id": 4, "name": "contact.open"},
            {"event_id": 5, "name": "contact.close"},
            {"event_id": 6, "name": "contact.alarm"},
            {"event_id": 7, "name": "contact.normal"},
        ],
    )

    events = project_events(device, domain=DOMAIN)

    assert len(events) == 1
    assert events[0].event_types == [
        "door_open",
        "door_close",
        "door_alarm",
        "door_normal",
    ]
    assert [trigger.subtype for trigger in project_device_triggers(device)] == (
        events[0].event_types
    )


def test_scene_panel_fallback_event_uses_panel_name() -> None:
    """缺少显式 schema events 时，事件实体也不能显示为泛泛的“事件”."""
    device = projection_payload(
        device_id="scene-panel-fallback-1",
        category="scene_panel",
        component_id="scene_panel",
        state={},
        component_category="scene_panel",
    )
    device["ha_product_model"]["components"][0]["events"] = []
    device["name"] = "客厅智能面板"

    events = project_events(device, domain=DOMAIN)

    assert len(events) == 1
    assert events[0].name == "面板事件"


def test_power_alarm_schema_events_project_without_static_component_claim() -> None:
    """power 告警类事件仅在产品 schema 显式声明时暴露自动化入口。"""
    device = projection_payload(
        device_id="power-alarm-1",
        category="other",
        component_id="vendor_power_alarm",
        state={},
        component_category="vendor power alarm",
        product_events=[
            {"event_id": 14, "name": "power.alarm"},
            {"event_id": 15, "name": "power.normal"},
        ],
    )

    events = project_events(device, domain=DOMAIN)

    assert len(events) == 1
    assert events[0].event_types == ["power_alarm", "power_normal"]
    assert [trigger.subtype for trigger in project_device_triggers(device)] == [
        "power_alarm",
        "power_normal",
    ]


def test_safety_name_without_schema_events_does_not_project_alarm_fallback() -> None:
    """设备名称不能作为安全事件能力证据。"""
    device = projection_payload(
        device_id="smoke-event-1",
        category="other",
        component_id="basic",
        state={},
        component_category="basic",
    )
    device["name"] = "厨房烟雾传感器"
    device["ha_product_model"]["components"][0]["events"] = []

    assert project_events(device, domain=DOMAIN) == []
    assert project_device_triggers(device) == []


def test_plain_other_without_events_does_not_project_alarm_fallback() -> None:
    """普通 other 设备不能仅凭无 schema 状态生成告警事件。"""
    device = projection_payload(
        device_id="plain-other-1",
        category="other",
        component_id="basic",
        state={},
        component_category="basic",
    )
    device["name"] = "普通扩展设备"
    device["ha_product_model"]["components"][0]["events"] = []

    assert project_events(device, domain=DOMAIN) == []
    assert project_device_triggers(device) == []


def test_relay_switch_without_declared_events_does_not_project_event() -> None:
    """普通继电器没有 product events 时不能仅凭品类生成 event。"""
    device = projection_payload(
        device_id="switch-no-event-1",
        category="relay_switch",
        component_id="relay_switch_1",
        state={"p": True},
        component_category="relay_switch",
    )
    component = device["ha_product_model"]["components"][0]
    component["cid"] = 20
    component["name"] = "switch control"

    assert [item.component_id for item in project_switches(device, domain=DOMAIN)] == [
        "relay_switch_1"
    ]
    assert project_events(device, domain=DOMAIN) == []
    assert project_device_triggers(device) == []
