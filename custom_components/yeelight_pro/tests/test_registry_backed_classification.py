"""Registry-backed runtime classification tests."""

from __future__ import annotations

import pytest

from custom_components.yeelight_pro.core.device_runtime_capabilities import (
    category_from_property_keys,
)
from custom_components.yeelight_pro.core.device_classification import (
    infer_iot_category,
)
from custom_components.yeelight_pro.core.device_registry_classification import (
    categories_for_property,
)


@pytest.mark.parametrize(
    ("category", "props", "expected"),
    [
        ("light", {"dc", "alm"}, "contact_sensor"),
        ("light", {"mv", "luminance", "sens_range", "delay_time"}, "light_sensor"),
        ("light", {"cp", "tp", "rd"}, "curtain"),
        ("light", {"vmcp", "vmcf"}, "temp_control"),
        ("light", {"p", "l", "ct"}, "light"),
        ("relay_switch", {"p"}, "relay_switch"),
        ("light", {"t", "h", "bl"}, "other"),
    ],
)
def test_category_uses_documented_property_capabilities_before_broad_category(
    category: str,
    props: set[str],
    expected: str,
) -> None:
    """粗 category 与属性能力冲突时，以易来 CSV 组件属性事实为准."""
    assert category_from_property_keys(props, current_category=category) == expected


def test_property_category_index_comes_from_iot_component_membership() -> None:
    """属性到品类的证据应来自 docs/iot 组件与属性关系."""
    assert categories_for_property("dc") == frozenset({"contact_sensor"})
    assert categories_for_property("tp") == frozenset({"curtain"})
    assert categories_for_property("vmcp") == frozenset({"temp_control"})
    assert "light_sensor" in categories_for_property("luminance")
    assert "human_sensor" in categories_for_property("mv")


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (
            {"category": "light", "name": "厨房烟雾传感器", "params": {"dc": False}},
            "contact_sensor",
        ),
        (
            {
                "category": "light",
                "name": "厨房烟雾传感器",
                "params": {"mv": True, "luminance": 188, "sens_range": 3},
            },
            "light_sensor",
        ),
        (
            {"category": "light", "name": "厨房烟雾传感器", "params": {"p": True}},
            "light",
        ),
    ],
)
def test_user_name_never_overrides_documented_runtime_capabilities(
    payload: dict[str, object],
    expected: str,
) -> None:
    """设备名只作显示，分类必须由 category、组件和属性能力决定."""
    assert infer_iot_category(payload) == expected


def test_user_name_alone_does_not_create_documented_capability() -> None:
    """只有用户名称时，不能伪造 docs/iot 未声明的设备能力."""
    payload = {"category": "light", "name": "厨房烟雾传感器", "params": {}}

    assert infer_iot_category(payload) == "light"
