"""Yeelight IoT 能力过滤规则测试."""
from __future__ import annotations

from typing import Any, Mapping

from custom_components.yeelight_pro.capabilities.filter import (
    FALLBACK_SENSOR_REASON,
    UNKNOWN_CAPABILITY_REASON,
    UNSUPPORTED_PLATFORM_REASON,
    UNSUPPORTED_VALUE_REASON,
    is_known_property_key,
    is_low_confidence_component_payload,
    should_project_unknown_property,
    summarize_unknown_capabilities,
    unknown_sensor_component_id,
)


def test_known_property_keys_support_component_prefix() -> None:
    """组件前缀属性应按真实 propName 识别。"""
    assert is_known_property_key("p")
    assert is_known_property_key("2-p")
    assert not is_known_property_key("vendor_private")


def test_unknown_property_hidden_by_default() -> None:
    """默认隐藏未知能力，不生成 fallback 实体。"""
    device = {"category": "other", "type": "sensor"}

    decision = should_project_unknown_property(
        "vendor_private",
        7,
        device,
        platform="sensor",
        hide_unknown_entities=True,
    )

    assert decision.allowed is False
    assert decision.reason == UNKNOWN_CAPABILITY_REASON


def test_unknown_property_can_be_marked_fallback_sensor_when_user_allows() -> None:
    """用户关闭隐藏后，只读未知标量可降级为明确 unknown sensor。"""
    device = {"category": "other", "type": "sensor"}

    decision = should_project_unknown_property(
        "vendor private",
        7,
        device,
        platform="sensor",
        hide_unknown_entities=False,
    )

    assert decision.allowed is True
    assert decision.reason == FALLBACK_SENSOR_REASON
    assert unknown_sensor_component_id("vendor private") == "unknown_vendor_private"


def test_unknown_bool_and_structured_values_do_not_become_controls() -> None:
    """未知布尔和结构化值不能按 Xiaomi 通用 transform 泛化成可写实体。"""
    device = {"category": "other", "type": "sensor"}

    for value in (True, {"code": 1}, [1, 2], ("on", "off")):
        decision = should_project_unknown_property(
            "vendor_control",
            value,
            device,
            platform="sensor",
            hide_unknown_entities=False,
        )

        assert decision.allowed is False
        assert decision.reason == UNSUPPORTED_VALUE_REASON


def test_unknown_property_fallback_is_sensor_only() -> None:
    """未知属性 fallback 只允许只读 sensor，不允许 switch/number/select/text。"""
    device = {"category": "other", "type": "sensor"}

    for platform in ("switch", "number", "select", "text", "button"):
        decision = should_project_unknown_property(
            "vendor_control",
            7,
            device,
            platform=platform,
            hide_unknown_entities=False,
        )

        assert decision.allowed is False
        assert decision.reason == UNSUPPORTED_PLATFORM_REASON


def test_event_input_payload_does_not_use_unknown_sensor_fallback() -> None:
    """事件输入设备即使隐藏关闭，也不能用未知标量泄漏到普通 sensor。"""
    device = {"category": "scene_panel", "type": "sensor"}

    decision = should_project_unknown_property(
        "vendor_private",
        7,
        device,
        platform="sensor",
        hide_unknown_entities=False,
    )

    assert decision.allowed is False
    assert decision.reason == UNSUPPORTED_PLATFORM_REASON


def test_low_confidence_components_do_not_use_unknown_sensor_fallback() -> None:
    """低频组件和桥接协议缺少样本时不能暴露未知 fallback sensor。"""
    for device in (
        {"category": "other", "type": "sensor", "component_id": "audio control"},
        {
            "category": "other",
            "type": "sensor",
            "ha_device_instance": {
                "components": [{"component_id": "wifi_screen", "state": {}}],
            },
        },
        {
            "category": "other",
            "type": "sensor",
            "ha_product_model": {
                "product": {"bridge": {"protocols": ["Matter", "Thread"]}},
            },
        },
    ):
        assert is_low_confidence_component_payload(device) is True
        decision = should_project_unknown_property(
            "vendor_private",
            7,
            device,
            platform="sensor",
            hide_unknown_entities=False,
        )
        assert decision.allowed is False
        assert decision.reason == UNSUPPORTED_PLATFORM_REASON


def test_unknown_filter_summary_is_aggregate_only() -> None:
    """诊断摘要只输出计数，不暴露设备或属性明细。"""
    devices: list[Mapping[str, Any]] = [
        {
            "device_id": "secret-device",
            "category": "other",
            "type": "sensor",
            "params": {"vendor_private": 7, "p": True},
        }
    ]

    assert summarize_unknown_capabilities(
        devices,
        hide_unknown_entities=True,
    ) == {
        "hidden_unknown_properties": 1,
        "fallback_sensor_properties": 0,
        "unsupported_unknown_properties": 0,
    }
    assert summarize_unknown_capabilities(
        devices,
        hide_unknown_entities=False,
    ) == {
        "hidden_unknown_properties": 0,
        "fallback_sensor_properties": 1,
        "unsupported_unknown_properties": 0,
    }


def test_low_confidence_summary_counts_unsupported_without_identifiers() -> None:
    """低频组件 diagnostics 只进入 unsupported 聚合，不输出属性或设备明细。"""
    devices: list[Mapping[str, Any]] = [
        {
            "device_id": "screen-secret",
            "category": "other",
            "type": "sensor",
            "ha_device_instance": {
                "components": [
                    {
                        "component_id": "mesh_screen",
                        "state": {"vendor_private": 7},
                    }
                ],
            },
        }
    ]

    summary = summarize_unknown_capabilities(devices, hide_unknown_entities=False)

    assert summary == {
        "hidden_unknown_properties": 0,
        "fallback_sensor_properties": 0,
        "unsupported_unknown_properties": 1,
    }
    assert "screen-secret" not in str(summary)
    assert "vendor_private" not in str(summary)
