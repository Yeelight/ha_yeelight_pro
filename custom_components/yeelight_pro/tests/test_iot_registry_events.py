"""Yeelight IoT registry event alias and component-scope tests."""

from __future__ import annotations

import pytest

from custom_components.yeelight_pro.capabilities import iot_registry
from custom_components.yeelight_pro.capabilities.registry import normalize_event_type


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("contact.open", "door_open"),
        ("contact.close", "door_close"),
        ("contact.alarm", "door_alarm"),
        ("motion.true", "motion_detected"),
        ("motion.false", "motion_undetected"),
        ("panel.click", "click"),
        ("panel.hold", "hold"),
        ("power.alarm", "power_alarm"),
        ("human enter", "human_enter"),
        ("有人进入", "human_enter"),
        (8, "motion_detected"),
    ],
)
def test_event_aliases_cover_backend_events(source: object, expected: str) -> None:
    """后台事件文本、点分别名和事件 id 应归一化为稳定事件名."""
    assert normalize_event_type(source) == expected


def test_panel_click_and_hold_event_component_matrix_matches_iot_docs() -> None:
    """panel.click/panel.hold 支持面应覆盖本地事件梳理中明确列出的组件."""
    registry = iot_registry()
    expected_components = {
        "wireless switch channel",
        "scene control button",
        "switch control",
        "dali scene control button",
    }
    events = {event.normalized: event for event in registry.events}

    assert set(events["click"].components) == expected_components
    assert set(events["hold"].components) == expected_components

    for component_alias in expected_components:
        component = registry.component_map[component_alias]
        assert {"click", "hold"}.issubset(component.events)


def test_release_after_hold_remains_unassigned_until_docs_confirm_components() -> None:
    """按住后松开目前缺少明确组件归属，不能提前扩大事件投影面。"""
    registry = iot_registry()
    events = {event.normalized: event for event in registry.events}

    assert events["release_after_hold"].components == ()


def test_dali_knob_spin_remains_unassigned_until_docs_confirm_components() -> None:
    """DALI 旋钮没有事件梳理直证，静态 registry 不能提前声明 knob_spin。"""
    registry = iot_registry()
    events = {event.normalized: event for event in registry.events}

    assert events["knob_spin"].components == ("knob switch",)
    assert "knob_spin" in registry.component_map["knob switch"].events
    assert registry.component_map["dali knob switch"].events == ()


def test_approach_events_are_scoped_to_infrared_sensor_docs() -> None:
    """approach 事件只绑定局域网协议明确列出的迈睿人体传感器。"""
    registry = iot_registry()
    events = {event.normalized: event for event in registry.events}

    assert events["human_enter"].components == ("human body infrared sensor",)
    assert events["human_leave"].components == ("human body infrared sensor",)
    infrared_events = registry.component_map["human body infrared sensor"].events
    assert {"human_enter", "human_leave"}.issubset(infrared_events)
    assert "human_enter" not in registry.component_map["human detection sensor"].events
