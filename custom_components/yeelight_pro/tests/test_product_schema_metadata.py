"""Product schema metadata normalization regression tests."""
from __future__ import annotations

from custom_components.yeelight_pro.adapters.product import YeelightProductSchemaAdapter
from custom_components.yeelight_pro.converter.product import (
    YeelightProductSchemaConverter,
)


def test_product_schema_converter_normalizes_value_range_numbers() -> None:
    """valueRange 数值应在 adapter 边界收敛为 int 或 None."""
    product = YeelightProductSchemaConverter().convert(
        {
            "pid": 1008,
            "name": "Range metadata",
            "category": "light",
            "components": [
                {
                    "cid": 4,
                    "name": "color temperature light",
                    "type": 0,
                    "category": "light",
                    "properties": [
                        {
                            "propId": "ct",
                            "format": "uint16",
                            "unit": "k",
                            "zoom": "-1",
                            "scale": "10",
                            "access": 7,
                            "valueRange": {
                                "min": "2700",
                                "max": 6500.9,
                                "step": "",
                            },
                        },
                        {
                            "propId": "bad_range",
                            "format": "uint16",
                            "access": 5,
                            "valueRange": {
                                "min": "invalid",
                                "max": None,
                                "step": "",
                            },
                        },
                    ],
                }
            ],
        }
    )

    props = {prop.prop_id: prop for prop in product.components[0].properties}
    assert props["ct"].value_range is not None
    assert props["ct"].value_range.min == 2700
    assert props["ct"].value_range.max == 6500
    assert props["ct"].value_range.step is None
    assert props["ct"].unit == "K"
    assert props["ct"].zoom == -1
    assert props["ct"].scale == 10
    assert props["bad_range"].value_range is None


def test_product_schema_converter_preserves_action_param_zoom_scale() -> None:
    """action param 的 zoom/scale 元数据应进入 canonical 模型."""
    product = YeelightProductSchemaConverter().convert(
        {
            "pid": 1010,
            "name": "Action metadata",
            "category": "light",
            "components": [
                {
                    "cid": 4,
                    "name": "color temperature light",
                    "type": 0,
                    "category": "light",
                    "supportActions": [
                        {
                            "actionName": "fade",
                            "params": [
                                {
                                    "propId": "ct",
                                    "format": "uint16",
                                    "unit": "kelvin",
                                    "zoom": "-1",
                                    "scale": "10",
                                }
                            ],
                        }
                    ],
                }
            ],
        }
    )

    [action] = product.components[0].actions
    [param] = action.params
    assert param.prop_id == "ct"
    assert param.unit == "K"
    assert param.zoom == -1
    assert param.scale == 10


def test_product_schema_converter_normalizes_value_list_items() -> None:
    """valueList 应过滤空 code 并按 code 去重."""
    product = YeelightProductSchemaConverter().convert(
        {
            "pid": 1009,
            "name": "Enum metadata",
            "category": "temp_control",
            "components": [
                {
                    "cid": 19,
                    "name": "air conditioner",
                    "type": 0,
                    "category": "temp_control",
                    "properties": [
                        {
                            "propId": "acm",
                            "format": "uint8",
                            "access": 7,
                            "valueList": [
                                {"code": " 0 ", "desc": "Auto"},
                                {"code": "", "desc": "Empty"},
                                {"desc": "Missing"},
                                {"code": 1, "desc": "Cool"},
                                {"code": "1", "desc": "Duplicate cool"},
                            ],
                        }
                    ],
                }
            ],
        }
    )

    [prop] = product.components[0].properties
    assert [(item.code, item.desc) for item in prop.value_list] == [
        ("0", "Auto"),
        ("1", "Cool"),
    ]


def test_product_schema_adapter_normalizes_metadata() -> None:
    """schema adapter normalized metadata 应与物模型边界规则保持一致."""
    source = YeelightProductSchemaAdapter().adapt(
        {
            "pid": 1007,
            "name": "Operator metadata",
            "components": [
                {
                    "cid": 4,
                    "name": "brightness light",
                    "type": "0",
                    "category": "light",
                    "properties": [
                        {
                            "propId": "p",
                            "unit": "none",
                            "zoom": "bad",
                            "scale": 0,
                            "operators": " set, toggle / adjust ",
                        }
                    ],
                    "supportActions": [
                        {
                            "actionName": "fade",
                            "params": [
                                {
                                    "propId": "l",
                                    "unit": "k",
                                    "zoom": "-1",
                                    "scale": "10",
                                    "operators": [{"operator": "SET"}],
                                }
                            ],
                        }
                    ],
                }
            ],
        }
    )

    prop = source.components[0].properties[0]
    action_param = source.components[0].actions[0].params[0]
    assert prop.metadata["operators"] == ["set", "toggle", "adjust"]
    assert prop.unit is None
    assert prop.metadata["zoom"] == 1
    assert prop.metadata["scale"] == 1
    assert prop.kind == "control"
    assert action_param.unit == "K"
    assert action_param.metadata["zoom"] == -1
    assert action_param.metadata["scale"] == 10
    assert action_param.metadata["operators"] == ["set"]
