"""Device channel label semantics tests."""
from __future__ import annotations

from custom_components.yeelight_pro.device_display import (
    channel_name_label,
    switch_channel_count_hint,
)


def test_wireless_switch_component_without_product_evidence_keeps_output_label() -> None:
    """无线开关通道是输入通道，即使父级是 relay_switch 也显示按键语义."""
    assert channel_name_label(
        index=1,
        component={
            "component_id": "wireless_switch_channel_1",
            "name": "wireless switch channel",
            "category": "relay_switch",
        },
        device_payload={"category": "relay_switch"},
    ) == "按键 1"
    assert channel_name_label(
        index=4,
        component={
            "component_id": "wireless_switch_channel_4",
            "name": "无线开关通道",
            "category": "relay_switch",
        },
        device_payload={"category": "relay_switch"},
    ) == "按键 4"


def test_product_catalog_wireless_switch_uses_key_labels_without_component() -> None:
    """只有 PID 和 relay_switch 大类时，官方无线开关通道仍应显示按键语义."""
    payload = {
        "pid": 854041,
        "name": "四键",
        "category": "relay_switch",
    }

    assert switch_channel_count_hint(payload) == 4
    assert channel_name_label(index=1, device_payload=payload) == "按键 1"
    assert channel_name_label(index=4, device_payload=payload) == "按键 4"


def test_product_catalog_mixed_scene_switch_uses_key_labels_without_component() -> None:
    """情景按键+无线开关通道产品不能被父级 relay_switch 压成回路."""
    payload = {
        "pid": 1509378,
        "name": "四键",
        "category": "relay_switch",
    }

    assert switch_channel_count_hint(payload) == 4
    assert channel_name_label(index=1, device_payload=payload) == "按键 1"
    assert channel_name_label(index=4, device_payload=payload) == "按键 4"


def test_product_catalog_output_switch_still_uses_loop_labels() -> None:
    """官方开关输出组件仍应显示位置语义，避免误认为四键输入按键."""
    payload = {
        "pid": 17000007,
        "name": "屏幕开关",
        "category": "relay_switch",
    }

    assert switch_channel_count_hint(payload) == 2
    assert channel_name_label(index=1, device_payload=payload) == "左键"
    assert channel_name_label(index=2, device_payload=payload) == "右键"
