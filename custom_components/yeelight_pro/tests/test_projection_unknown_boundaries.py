"""Unknown-capability projection fallback boundary tests."""

from __future__ import annotations

from custom_components.yeelight_pro.entity_lifecycle import collect_active_entity_keys
from custom_components.yeelight_pro.projector.binary_sensor import project_binary_sensors
from custom_components.yeelight_pro.projector.sensor import project_sensors
from custom_components.yeelight_pro.projector.switch import project_switches

from .projection_helpers import DOMAIN, LifecycleCoordinator, projection_payload


def test_unknown_readable_property_does_not_project_when_hiding_disabled() -> None:
    """隐藏关闭时，未知可读属性也不能泛化生成 sensor。"""
    device = projection_payload(
        device_id="unknown-visible-1",
        category="light_sensor",
        component_id="vendor_private_meter",
        state={"vendor_private": 7},
        params={"vendor_private": 7},
        component_category="vendor private meter",
    )
    device["hide_unknown_entities"] = False

    assert project_sensors(device, domain=DOMAIN) == []
    assert collect_active_entity_keys(
        LifecycleCoordinator(data={"unknown": device}, hide_unknown_entities=False)
    ) == set()


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
    ) == {
        ("event", "yeelight_pro_scene-panel-unknown-scalar-1_scene_panel_event")
    }


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
