"""Registry-backed runtime classification tests."""

from __future__ import annotations

import pytest

from custom_components.yeelight_pro.core.device_runtime_capabilities import (
    category_from_property_keys,
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
