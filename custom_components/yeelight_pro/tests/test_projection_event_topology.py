"""Yeelight IoT 事件输入与网关拓扑投影回归测试."""

from __future__ import annotations

from custom_components.yeelight_pro.canonical.models import HADeviceInstanceModel
from custom_components.yeelight_pro.entity_lifecycle import collect_active_entity_keys
from custom_components.yeelight_pro.projector.binary_sensor import project_binary_sensors
from custom_components.yeelight_pro.projector.climate import project_climate
from custom_components.yeelight_pro.projector.cover import project_cover
from custom_components.yeelight_pro.projector.device import project_device_info
from custom_components.yeelight_pro.projector.event import (
    project_device_triggers,
    project_events,
)
from custom_components.yeelight_pro.projector.light import project_light
from custom_components.yeelight_pro.projector.sensor import project_sensors
from custom_components.yeelight_pro.projector.switch import project_switches

from .projection_helpers import DOMAIN, LifecycleCoordinator, projection_payload


def test_scene_panel_projects_events_not_sensors() -> None:
    """情景面板应投影为 event/device trigger，不应误投影 sensor/binary_sensor。"""
    device = projection_payload(
        device_id="panel-1",
        category="scene_panel",
        component_id="scene_panel",
        state={"alm": True, "mv": True, "dc": True, "luminance": 88},
        product_type=128,
        component_category="scene_panel",
        product_events=[
            {"event_id": 1, "name": "click"},
            {"event_id": 2, "name": "hold"},
            {"event_id": 10, "name": "knob spin"},
        ],
    )

    events = project_events(device, domain=DOMAIN)
    triggers = project_device_triggers(device)

    assert len(events) == 1
    assert events[0].event_types == ["click", "hold", "knob_spin"]
    assert [trigger.subtype for trigger in triggers] == ["click", "hold", "knob_spin"]
    assert project_binary_sensors(device, domain=DOMAIN) == []
    assert project_sensors(device, domain=DOMAIN) == []


def test_scene_panel_button_property_does_not_project_as_switch() -> None:
    """情景按键的 p/m 属性属于事件输入，不应显示成普通开关控制。"""
    device = projection_payload(
        device_id="panel-button-1",
        category="scene_panel",
        component_id="button_1",
        state={"p": True, "m": 1},
        product_type=128,
        component_category="scene control button",
        product_events=[
            {"event_id": 1, "name": "click"},
            {"event_id": 2, "name": "hold"},
        ],
    )

    events = project_events(device, domain=DOMAIN)

    assert len(events) == 1
    assert events[0].name == "第 1 键事件"
    assert events[0].event_types == ["click", "hold"]
    assert project_switches(device, domain=DOMAIN) == []


def test_three_key_scene_panel_event_names_use_positions() -> None:
    """三键情景面板事件应显示左中右，不应继续暴露第 1/2/3 键。"""
    device = projection_payload(
        device_id="panel-button-3",
        category="scene_panel",
        component_id="scene_control_button_2",
        state={"p": True},
        product_type=128,
        component_category="scene control button",
        product_events=[{"event_id": 1, "name": "click"}],
    )
    device["name"] = "玄关三键情景面板"
    device["ha_device_instance"]["name"] = "玄关三键情景面板"
    device["ha_device_instance"]["device_info"]["name"] = "玄关三键情景面板"

    events = project_events(device, domain=DOMAIN)

    assert len(events) == 1
    assert events[0].name == "中键事件"
    assert project_switches(device, domain=DOMAIN) == []


def test_gateway_only_provides_topology_device_info() -> None:
    """网关类应作为拓扑父设备存在，不生成普通控制实体。"""
    device = projection_payload(
        device_id="gateway-1",
        category="gateway",
        component_id="gateway",
        state={},
        component_category="gateway",
    )
    device["is_gateway"] = True
    device["type"] = "gateway"
    assert project_light(device, domain=DOMAIN) is None
    assert project_switches(device, domain=DOMAIN) == []
    assert project_cover(device, domain=DOMAIN) is None
    assert project_climate(device, domain=DOMAIN) is None
    assert project_binary_sensors(device, domain=DOMAIN) == []
    assert project_sensors(device, domain=DOMAIN) == []
    assert project_events(device, domain=DOMAIN) == []
    instance = HADeviceInstanceModel.from_dict(device["ha_device_instance"])
    device_info = project_device_info(instance)
    assert device_info is not None
    assert device_info["identifiers"] == {(DOMAIN, "gateway-1")}
    coordinator = LifecycleCoordinator(data={"gateway-1": device})
    assert collect_active_entity_keys(coordinator) == set()


def test_knob_switch_projects_event_only_and_not_sensors() -> None:
    """旋钮是事件输入设备，不应因 alm/p 等状态误投影为 sensor/binary_sensor/switch。"""
    device = projection_payload(
        device_id="knob-1",
        category="knob_switch",
        component_id="knob_switch",
        state={"alm": True, "mv": True, "dc": True, "luminance": 88, "p": True},
        product_type=132,
        component_category="knob_switch",
        product_events=[
            {"event_id": 10, "name": "knob spin"},
            {"event_id": 11, "name": "multi spin"},
            {"event_id": 12, "name": "absolut spin"},
        ],
    )
    events = project_events(device, domain=DOMAIN)
    assert len(events) == 1
    assert events[0].event_types == ["knob_spin", "multi_spin", "absolut_spin"]
    assert project_binary_sensors(device, domain=DOMAIN) == []
    assert project_sensors(device, domain=DOMAIN) == []
    assert project_switches(device, domain=DOMAIN) == []
