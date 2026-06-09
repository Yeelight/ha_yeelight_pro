"""Yeelight IoT registry component-property key helper tests."""

from __future__ import annotations

import pytest

from custom_components.yeelight_pro.capabilities import (
    format_component_property_key,
    parse_component_property_key,
)


def test_component_property_key_format_and_parse() -> None:
    """组件属性 key helper 必须支持基础组件和旧式直接属性名."""
    assert format_component_property_key(None, "p") == "p"
    assert format_component_property_key(0, "p") == "0-p"
    assert format_component_property_key(1, "p") == "1-p"

    direct = parse_component_property_key("p")
    assert direct.component_index is None
    assert direct.prop_name == "p"

    indexed = parse_component_property_key("12-ct")
    assert indexed.component_index == 12
    assert indexed.prop_name == "ct"


@pytest.mark.parametrize(
    ("component_index", "prop_name"),
    [(-1, "p"), (1, ""), (1, None)],
)
def test_component_property_key_rejects_invalid_values(
    component_index: int,
    prop_name: str | None,
) -> None:
    """非法组件索引和空属性名应尽早失败."""
    with pytest.raises(ValueError):
        format_component_property_key(component_index, prop_name)
