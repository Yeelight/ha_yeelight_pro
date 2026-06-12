"""Unsupported HA platform projection boundaries."""

from __future__ import annotations

from custom_components.yeelight_pro.capabilities.mapping import platform_for_category
from custom_components.yeelight_pro.capabilities.registry import is_iot_category
from custom_components.yeelight_pro.entity_lifecycle import collect_active_entity_keys
from custom_components.yeelight_pro.projector.binary_sensor import project_binary_sensors
from custom_components.yeelight_pro.projector.event import project_events
from custom_components.yeelight_pro.projector.light import project_light
from custom_components.yeelight_pro.projector.sensor import project_sensors
from custom_components.yeelight_pro.projector.switch import project_switches

from .projection_helpers import DOMAIN, LifecycleCoordinator, projection_payload

CORE_IOT_DEVICE_CATEGORIES = {
    "light",
    "contact_sensor",
    "human_sensor",
    "light_sensor",
    "curtain",
    "temp_control",
    "relay_switch",
    "scene_panel",
    "gateway",
    "other",
}
HA_ENTITY_PLATFORMS_NOT_IOT_CATEGORIES = {
    "event",
    "scene",
    "button",
    "select",
    "number",
    "text",
}


def test_ha_entity_platforms_are_not_yeelight_iot_device_categories() -> None:
    """scene/button/select/number/text 是 HA 表达，不是后台 IoT 品类。"""
    for platform in HA_ENTITY_PLATFORMS_NOT_IOT_CATEGORIES:
        assert not is_iot_category(platform)
        assert platform_for_category(platform) is None

    assert not is_iot_category("vacuum")
    assert platform_for_category("vacuum") is None


def test_unsupported_vacuum_payload_does_not_project_entities() -> None:
    """无易来文档/接口支撑的 vacuum-like payload 不应生成 HA 实体。"""
    device = projection_payload(
        device_id="vacuum-1",
        category="other",
        component_id="vacuum",
        state={"status": "cleaning", "bl": 88},
        component_category="vacuum",
    )
    device["type"] = "vacuum"

    assert project_light(device, domain=DOMAIN) is None
    assert project_switches(device, domain=DOMAIN) == []
    assert project_binary_sensors(device, domain=DOMAIN) == []
    assert project_sensors(device, domain=DOMAIN) == []
    assert project_events(device, domain=DOMAIN) == []
    assert collect_active_entity_keys(LifecycleCoordinator(data={"vacuum": device})) == set()
    assert len(CORE_IOT_DEVICE_CATEGORIES) == 10
    assert "vacuum" not in CORE_IOT_DEVICE_CATEGORIES
