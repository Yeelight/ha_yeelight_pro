"""Yeelight IoT registry integrity validation tests."""

from __future__ import annotations

import pytest

from custom_components.yeelight_pro.capabilities.data import (
    IOT_CATEGORY_SPECS,
    IOT_COMPONENT_SPECS,
    IOT_EVENT_SPECS,
    IOT_PROPERTY_SPECS,
    IOT_PROTOCOL_SPECS,
)
from custom_components.yeelight_pro.capabilities.models import (
    IoTCategorySpec,
    IoTComponentSpec,
    IoTEventSpec,
    IoTPropertySpec,
    PropertyCapability,
)
from custom_components.yeelight_pro.capabilities.registry import (
    YeelightIoTRegistry,
    iot_registry,
)
from custom_components.yeelight_pro.capabilities.validation import (
    validate_iot_registry,
)


def test_current_iot_registry_is_structurally_valid() -> None:
    """当前内置物模型必须满足发布前结构不变量."""
    assert validate_iot_registry(iot_registry()) == []


def test_registry_validation_detects_duplicate_and_unknown_references() -> None:
    """校验器应能发现重复键和跨表引用错误."""
    registry = YeelightIoTRegistry(
        categories=(
            *IOT_CATEGORY_SPECS,
            IoTCategorySpec("light", 999, "重复灯类", "light", "duplicate"),
            IoTCategorySpec("scene", 998, "错误平台", "scene", "bad category"),
        ),
        components=(
            *IOT_COMPONENT_SPECS,
            IoTComponentSpec(
                2,
                "broken component",
                "坏组件",
                "ghost_category",
                "normal",
                "ghost_platform",
                ("ghost_prop",),
                ("ghost_event",),
            ),
        ),
        properties=(
            *IOT_PROPERTY_SPECS,
            IoTPropertySpec(
                "broken_prop",
                "broken",
                "int",
                "read",
                "application",
                "device",
                PropertyCapability("other_prop"),
                ("ghost_component",),
            ),
        ),
        events=(
            *IOT_EVENT_SPECS,
            IoTEventSpec(
                "broken event",
                "broken_event",
                description="bad",
                components=("ghost_component",),
            ),
        ),
        protocols=IOT_PROTOCOL_SPECS,
    )

    errors = validate_iot_registry(registry)

    assert "duplicate category: light" in errors
    assert "duplicate component_id: 2" in errors
    assert "HA platform must not be an IoT category: scene" in errors
    assert (
        "component broken component references unknown category ghost_category"
        in errors
    )
    assert (
        "component broken component has unknown platform hint ghost_platform"
        in errors
    )
    assert (
        "component broken component references unknown property ghost_prop"
        in errors
    )
    assert "component broken component references unknown event ghost_event" in errors
    assert "property broken_prop capability prop mismatch: other_prop" in errors
    assert (
        "property broken_prop references unknown component ghost_component"
        in errors
    )
    assert (
        "event broken_event references unknown component ghost_component"
        in errors
    )


@pytest.mark.parametrize(
    "platform",
    ["event", "scene", "button", "select", "number", "text"],
)
def test_registry_validation_guards_ha_platform_categories(platform: str) -> None:
    """HA 实体平台不能被误登记为 Yeelight IoT 品类."""
    registry = YeelightIoTRegistry(
        categories=(
            *IOT_CATEGORY_SPECS,
            IoTCategorySpec(platform, 900, platform, platform, "bad platform"),
        ),
        components=IOT_COMPONENT_SPECS,
        properties=IOT_PROPERTY_SPECS,
        events=IOT_EVENT_SPECS,
        protocols=IOT_PROTOCOL_SPECS,
    )

    assert (
        f"HA platform must not be an IoT category: {platform}"
        in validate_iot_registry(registry)
    )


def test_registry_validation_detects_normalized_event_alias_collisions() -> None:
    """事件别名冲突应按运行时归一化 key 校验."""
    registry = YeelightIoTRegistry(
        categories=IOT_CATEGORY_SPECS,
        components=IOT_COMPONENT_SPECS,
        properties=IOT_PROPERTY_SPECS,
        events=(
            IoTEventSpec("foo.bar", "first_event", aliases=("first event",)),
            IoTEventSpec("foo_bar", "second_event", aliases=("second event",)),
        ),
        protocols=IOT_PROTOCOL_SPECS,
    )

    errors = validate_iot_registry(registry)

    assert any(
        "maps to both first_event and second_event" in error for error in errors
    )
