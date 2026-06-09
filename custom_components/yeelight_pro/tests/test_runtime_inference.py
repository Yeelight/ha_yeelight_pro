"""Runtime product model inference regression tests."""
from __future__ import annotations

from custom_components.yeelight_pro.converter.product import (
    RuntimeInferredProductModelBuilder,
)


def test_runtime_inferred_product_model_handles_indexed_switches() -> None:
    """Runtime inference must split indexed switch params into components."""
    payload = {
        "model_id": "runtime-switch",
        "type": "switch",
        "category": "relay_switch",
        "params": {
            "1-p": True,
            "2-sp": False,
            "l": 80,
        },
    }

    product = RuntimeInferredProductModelBuilder().build(payload)

    assert product is not None
    assert product.schema_version == "runtime-v1"
    assert [component.component_id for component in product.components] == [
        "switch_1",
        "switch_2",
    ]
    assert product.components[0].properties[0].prop_id == "p"
    assert product.components[1].properties[0].prop_id == "sp"


def test_runtime_inferred_light_template_ranges_are_stable() -> None:
    """Runtime light fallback must keep Yeelight brightness and CT ranges stable."""
    payload = {
        "model_id": "runtime-light",
        "type": "light",
        "category": "light",
        "params": {
            "p": True,
            "l": 75,
            "ct": 4000,
        },
    }

    product = RuntimeInferredProductModelBuilder().build(payload)

    assert product is not None
    props = {prop.prop_id: prop for prop in product.components[0].properties}
    assert props["l"].value_range is not None
    assert props["l"].value_range.min == 1
    assert props["l"].value_range.max == 100
    assert props["l"].value_range.step == 1
    assert props["ct"].value_range is not None
    assert props["ct"].value_range.min == 2700
    assert props["ct"].value_range.max == 6500
    assert props["ct"].value_range.step is None
