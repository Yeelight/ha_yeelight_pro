"""Yeelight IoT 投影边界与实验平台回归测试."""
from __future__ import annotations

from custom_components.yeelight_pro.capabilities.mapping import platform_for_category
from custom_components.yeelight_pro.capabilities.registry import is_iot_category
from custom_components.yeelight_pro.const import EXPERIMENTAL_PLATFORMS
from custom_components.yeelight_pro.entity_lifecycle import collect_active_entity_keys
from custom_components.yeelight_pro.projector.binary_sensor import project_binary_sensors
from custom_components.yeelight_pro.projector.event import project_events
from custom_components.yeelight_pro.projector.light import project_light
from custom_components.yeelight_pro.projector.sensor import project_sensors
from custom_components.yeelight_pro.projector.switch import project_switches
from custom_components.yeelight_pro.projector.vacuum import project_vacuum

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
    "vacuum",
    "text",
}


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


def test_relay_switch_legacy_indexed_keys_still_project_switches() -> None:
    """已知继电器旧载荷仍可用 indexed IoT 控制键生成多路 switch。"""
    device = {
        "device_id": "relay-indexed-1",
        "name": "多路继电器",
        "category": "relay_switch",
        "type": "switch",
        "online": True,
        "params": {"1-p": True, "2-sp": False},
    }

    projections = project_switches(device, domain=DOMAIN)

    assert [item.component_id for item in projections] == ["switch_1", "switch_2"]
    assert [item.control_key for item in projections] == ["1-p", "2-sp"]
    assert [item.is_on for item in projections] == [True, False]


def test_unknown_readable_property_projects_marked_fallback_sensor_when_hiding_disabled() -> None:
    """隐藏关闭时，未知可读属性应生成明确标记 unknown 的 fallback sensor。"""
    device = projection_payload(
        device_id="unknown-visible-1",
        category="other",
        component_id="vendor_private_meter",
        state={"vendor_private": 7},
        params={"vendor_private": 7},
        component_category="vendor private meter",
    )
    device["hide_unknown_entities"] = False

    projections = project_sensors(device, domain=DOMAIN)

    assert len(projections) == 1
    assert projections[0].component_id == "unknown_vendor_private"
    assert projections[0].unique_id == f"{DOMAIN}_unknown-visible-1_unknown_vendor_private"
    assert projections[0].native_value == 7
    assert projections[0].device_class is None
    assert projections[0].native_unit_of_measurement is None
    assert projections[0].icon == "mdi:help-circle-outline"


def test_unknown_bool_value_does_not_project_generic_writable_or_binary_entity() -> None:
    """未知 bool 不能照搬 Xiaomi 通用规则生成 switch 或 binary_sensor。"""
    device = projection_payload(
        device_id="unknown-bool-1",
        category="other",
        component_id="vendor_private_flag",
        state={"vendor_flag": True},
        params={"vendor_flag": True},
        component_category="vendor private flag",
    )
    device["hide_unknown_entities"] = False

    assert project_switches(device, domain=DOMAIN) == []
    assert project_binary_sensors(device, domain=DOMAIN) == []
    assert project_sensors(device, domain=DOMAIN) == []
    assert collect_active_entity_keys(
        LifecycleCoordinator(data={"unknown": device}, hide_unknown_entities=False)
    ) == set()


def test_unknown_list_or_mapping_value_does_not_project_select_or_sensor() -> None:
    """未知枚举/结构值不能在没有写入合同前生成 select 或普通 sensor。"""
    for device_id, value in (
        ("unknown-list-1", ["auto", "manual"]),
        ("unknown-map-1", {"code": "auto"}),
    ):
        device = projection_payload(
            device_id=device_id,
            category="other",
            component_id="vendor_private_mode",
            state={"vendor_mode": value},
            params={"vendor_mode": value},
            component_category="vendor private mode",
        )
        device["hide_unknown_entities"] = False

        assert project_sensors(device, domain=DOMAIN) == []


def test_event_input_unknown_scalar_does_not_project_fallback_sensor() -> None:
    """事件输入设备不应因为未知标量 fallback 泄漏到 sensor 平台。"""
    device = projection_payload(
        device_id="scene-panel-unknown-scalar-1",
        category="scene_panel",
        component_id="scene_panel",
        state={"vendor_private": 7},
        params={"vendor_private": 7},
        component_category="scene_panel",
    )
    device["hide_unknown_entities"] = False

    assert project_sensors(device, domain=DOMAIN) == []
    assert collect_active_entity_keys(
        LifecycleCoordinator(data={"panel": device}, hide_unknown_entities=False)
    ) == set()


def test_low_frequency_component_unknown_scalar_does_not_project_fallback_sensor() -> None:
    """audio/screen 等低频组件无样本前不能因隐藏关闭生成泛化 sensor。"""
    for device_id, component_id, component_category in (
        ("audio-lowfreq-1", "audio_control", "audio control"),
        ("screen-lowfreq-1", "wifi_screen", "wifi screen"),
    ):
        device = projection_payload(
            device_id=device_id,
            category="other",
            component_id=component_id,
            state={"vendor_private": 7},
            params={"vendor_private": 7},
            component_category=component_category,
        )
        device["hide_unknown_entities"] = False

        assert project_sensors(device, domain=DOMAIN) == []
        assert collect_active_entity_keys(
            LifecycleCoordinator(data={device_id: device}, hide_unknown_entities=False)
        ) == set()


def test_bridge_protocol_metadata_does_not_enable_unknown_fallback_sensor() -> None:
    """Matter/Thread/DALI 桥接元数据不能单独放宽未知属性投影。"""
    device = projection_payload(
        device_id="bridge-metadata-1",
        category="other",
        component_id="vendor_meter",
        state={"vendor_private": 7},
        params={"vendor_private": 7},
        component_category="vendor meter",
    )
    device["type"] = "sensor"
    device["hide_unknown_entities"] = False
    device["ha_product_model"]["product"]["bridge"] = {
        "protocols": ["Matter", "Thread", "DALI"],
    }

    assert project_sensors(device, domain=DOMAIN) == []
    assert collect_active_entity_keys(
        LifecycleCoordinator(data={"bridge": device}, hide_unknown_entities=False)
    ) == set()


def test_ha_entity_platforms_are_not_yeelight_iot_device_categories() -> None:
    """scene/button/select/number/vacuum/text 是 HA 表达或实验能力，不是后台 IoT 品类。"""
    for platform in HA_ENTITY_PLATFORMS_NOT_IOT_CATEGORIES:
        assert not is_iot_category(platform)
        assert platform_for_category(platform) is None

    assert "vacuum" in EXPERIMENTAL_PLATFORMS


def test_vacuum_projection_is_experimental_and_requires_explicit_vacuum_payload() -> None:
    """vacuum 保留为实验平台，只有明确 vacuum payload 才投影。"""
    light = projection_payload(
        device_id="light-robot-name",
        category="light",
        component_id="light",
        state={"p": True},
    )
    vacuum = projection_payload(
        device_id="vacuum-1",
        category="other",
        component_id="vacuum",
        state={"status": "cleaning", "bl": 88},
        component_category="vacuum",
    )
    vacuum["type"] = "vacuum"

    assert project_vacuum(light, domain=DOMAIN) is None
    projection = project_vacuum(vacuum, domain=DOMAIN)
    assert projection is not None
    assert projection.status == "cleaning"
    assert projection.battery_level == 88
    assert len(CORE_IOT_DEVICE_CATEGORIES) == 10
    assert "vacuum" not in CORE_IOT_DEVICE_CATEGORIES
