"""Yeelight IoT 投影边界回归测试."""
from __future__ import annotations

from custom_components.yeelight_pro.entity_lifecycle import collect_active_entity_keys
from custom_components.yeelight_pro.projector.binary_sensor import project_binary_sensors
from custom_components.yeelight_pro.projector.climate import project_climate
from custom_components.yeelight_pro.projector.cover import project_cover
from custom_components.yeelight_pro.projector.event import project_events
from custom_components.yeelight_pro.projector.fan import project_fans
from custom_components.yeelight_pro.projector.light import project_light
from custom_components.yeelight_pro.projector.sensor import project_sensors
from custom_components.yeelight_pro.projector.switch import project_switches

from .projection_helpers import DOMAIN, LifecycleCoordinator, projection_payload

def test_unknown_capability_hidden_by_default_from_ordinary_platforms() -> None:
    """默认隐藏未知能力，不应从未知组合生成普通实体。"""
    device = projection_payload(
        device_id="unknown-hidden-1",
        category="other",
        component_id="vendor_private_component",
        state={"vendor_private": 7, "vendor_flag": True},
        params={"vendor_private": 7, "vendor_flag": True},
        component_category="vendor private component",
    )

    assert project_light(device, domain=DOMAIN) is None
    assert project_switches(device, domain=DOMAIN) == []
    assert project_binary_sensors(device, domain=DOMAIN) == []
    assert project_sensors(device, domain=DOMAIN) == []
    assert project_events(device, domain=DOMAIN) == []
    assert collect_active_entity_keys(LifecycleCoordinator(data={"unknown": device})) == set()


def test_unknown_power_like_component_hidden_from_switch_when_hiding_enabled() -> None:
    """未知 component 即使带 p，也不能在隐藏开启时被泛化为 switch。"""
    device = projection_payload(
        device_id="unknown-switch-like-1",
        category="other",
        component_id="vendor_private_output",
        state={"p": True},
        params={"p": True},
        component_category="vendor private output",
    )

    assert project_switches(device, domain=DOMAIN) == []
    assert collect_active_entity_keys(LifecycleCoordinator(data={"unknown": device})) == set()


def test_component_labels_do_not_create_main_platform_entities() -> None:
    """组件名称/描述不能越过易来 category 和属性证据生成主平台实体。"""
    device = projection_payload(
        device_id="misleading-labels-1",
        category="other",
        component_id="vendor_private_component",
        state={"vendor_private": 7},
        params={"vendor_private": 7},
        component_category="other",
    )
    component = device["ha_device_instance"]["components"][0]
    component["name"] = "空调窗帘新风开关彩光灯"
    component["desc"] = "空调窗帘新风开关彩光灯"
    schema_component = device["ha_product_model"]["components"][0]
    schema_component["name"] = "空调窗帘新风开关彩光灯"
    schema_component["desc"] = "空调窗帘新风开关彩光灯"

    assert project_light(device, domain=DOMAIN) is None
    assert project_switches(device, domain=DOMAIN) == []
    assert project_cover(device, domain=DOMAIN) is None
    assert project_climate(device, domain=DOMAIN) is None
    assert project_fans(device, domain=DOMAIN) == []


def test_official_properties_override_misleading_component_labels() -> None:
    """属性能力优先于名称；用户把灯命名成烟雾/空调也仍按 light 投影。"""
    device = projection_payload(
        device_id="light-misnamed-1",
        category="light",
        component_id="color_light",
        state={"p": True, "l": 60, "ct": 4000},
        params={"p": True, "l": 60, "ct": 4000},
        component_category="light",
    )
    device["name"] = "厨房烟雾传感器空调"
    device["ha_device_instance"]["name"] = "厨房烟雾传感器空调"
    device["ha_device_instance"]["components"][0]["name"] = "空调"
    device["ha_product_model"]["components"][0]["name"] = "空调"

    assert project_light(device, domain=DOMAIN) is not None
    assert project_climate(device, domain=DOMAIN) is None
    assert project_switches(device, domain=DOMAIN) == []


def test_non_light_sensor_payload_does_not_fallback_to_light() -> None:
    """云端粗 type=light 不能把传感器 payload 误投成灯."""
    for device in (
        projection_payload(
            device_id="contact-light-fallback",
            category="contact_sensor",
            component_id="contact_sensor",
            state={"dc": True, "alm": False},
            component_category="contact sensor",
        ),
        projection_payload(
            device_id="human-light-fallback",
            category="human_sensor",
            component_id="human_sensor",
            state={"mv": True, "luminance": 80},
            component_category="human detection sensor",
        ),
    ):
        device["type"] = "light"

        assert project_light(device, domain=DOMAIN) is None


def test_legacy_type_light_power_only_payload_does_not_project_light() -> None:
    """仅有 type=light 和开关状态不足以证明设备是灯。"""
    device = {
        "device_id": "legacy-power-only",
        "type": "light",
        "online": True,
        "params": {"p": True},
    }

    assert project_light(device, domain=DOMAIN) is None


def test_unknown_indexed_power_keys_do_not_project_writable_switches() -> None:
    """未知 indexed p/sp 不能绕过 raw fallback 生成可写 switch。"""
    device = {
        "device_id": "unknown-indexed-switch-1",
        "name": "未知多路设备",
        "category": "other",
        "type": "sensor",
        "online": True,
        "params": {"1-p": True, "2-sp": False},
        "hide_unknown_entities": False,
    }

    assert project_switches(device, domain=DOMAIN) == []
    coordinator = LifecycleCoordinator(
        data={"unknown": device},
        hide_unknown_entities=False,
    )
    assert collect_active_entity_keys(coordinator) == set()


def test_unsupported_outlet_on_payload_does_not_project_switch() -> None:
    """outlet/on 不是易来官方品类/属性，不能泛化为 switch。"""
    device = {
        "device_id": "unsupported-outlet-1",
        "name": "未知插座",
        "type": "outlet",
        "online": True,
        "params": {"on": True},
    }

    assert project_switches(device, domain=DOMAIN) == []


def test_non_switch_parent_category_blocks_indexed_switch_fallback() -> None:
    """父级已规范为其他品类时，type=switch 不能覆盖生成 switch。"""
    for category, params in (
        ("light", {"1-p": True, "2-p": False}),
        ("curtain", {"1-p": True, "2-p": True, "cp": 40, "tp": 90}),
        ("temp_control", {"1-p": True, "2-p": False, "aco": True}),
        ("scene_panel", {"1-p": True, "2-p": True, "3-p": False}),
        ("other", {"1-p": True, "2-sp": False}),
    ):
        device = {
            "device_id": f"{category}-indexed-switch",
            "name": category,
            "iot_category": category,
            "category": category,
            "type": "switch",
            "online": True,
            "params": params,
        }

        assert project_switches(device, domain=DOMAIN) == []


