"""Capability registry production contract tests."""

from __future__ import annotations

import pytest

from custom_components.yeelight_pro.capabilities.events import normalize_event_type
from custom_components.yeelight_pro.capabilities.mapping import platform_for_category
from custom_components.yeelight_pro.capabilities.properties import property_capability


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("click", "click"),
        ("hold", "hold"),
        ("release after hold", "release_after_hold"),
        ("door open", "door_open"),
        ("door close", "door_close"),
        ("door alarm", "door_alarm"),
        ("door normal", "door_normal"),
        ("knob spin", "knob_spin"),
        ("human enter", "human_enter"),
        ("human leave", "human_leave"),
        ("motion detected", "motion_detected"),
        ("motion undetected", "motion_undetected"),
        ("power.alarm", "power_alarm"),
        ("power.normal", "power_normal"),
    ],
)
def test_event_aliases_cover_backend_event_types(source: str, expected: str) -> None:
    """用户提供的易来后台事件类型必须归一化为稳定事件名."""
    assert normalize_event_type(source) == expected


def test_capability_registry_maps_core_categories_and_properties() -> None:
    """轻量能力表集中维护核心品类和属性语义."""
    assert platform_for_category("light") == "light"
    assert platform_for_category("relay_switch") == "switch"
    assert platform_for_category("contact_sensor") == "binary_sensor"
    assert platform_for_category("light_sensor") == "sensor"
    brightness_capability = property_capability("l")
    color_temp_capability = property_capability("ct")
    luminance_capability = property_capability("luminance")
    assert brightness_capability is not None
    assert color_temp_capability is not None
    assert luminance_capability is not None
    assert brightness_capability.control_key == "brightness"
    assert color_temp_capability.unit == "K"
    assert luminance_capability.device_class == "illuminance"
