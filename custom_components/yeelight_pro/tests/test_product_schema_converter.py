"""Product schema converter regression tests."""
from __future__ import annotations

from custom_components.yeelight_pro.converter.product import (
    YeelightProductSchemaConverter,
)


def test_product_schema_converter_builds_canonical_components() -> None:
    """Yeelight product schema must become a canonical product model."""
    schema = {
        "pid": 1001,
        "name": "Demo light",
        "desc": "Commercial lighting schema",
        "category": "light",
        "supportedBridge": True,
        "supportedBridgeType": [{"desc": "Matter"}, {"desc": "Mesh"}],
        "components": [
            {
                "cid": 4,
                "name": "color temperature light",
                "type": 0,
                "category": "light",
                "index": 1,
                "properties": [
                    {
                        "propId": "p",
                        "desc": "Power",
                        "format": "bool",
                        "operators": ["set", "toggle"],
                    },
                    {
                        "propId": "ct",
                        "desc": "Color temperature",
                        "format": "uint16",
                        "unit": "k",
                        "operators": ["set"],
                        "valueRange": {"min": 2700, "max": 6500, "step": 1},
                    },
                    {
                        "propId": "name",
                        "desc": "Name",
                    },
                ],
                "events": [{"eventId": 1, "name": "click", "desc": "Click"}],
                "supportActions": [
                    {"actionName": "toggle", "params": [{"propId": "p"}]}
                ],
            }
        ],
        "supportActions": [{"actionName": "identify"}],
    }

    product = YeelightProductSchemaConverter().convert(schema)

    assert product.product.model_id == "YL-1001"
    assert product.product.bridge is not None
    assert product.product.bridge.protocols == ["matter", "mesh"]
    assert product.product.categories == ["light"]
    assert len(product.components) == 1
    component = product.components[0]
    assert component.component_id == "light"
    assert component.component_type == "custom"
    assert component.capabilities == ["light", "light.p", "light.ct", "toggle"]
    assert [prop.prop_id for prop in component.properties] == ["p", "ct", "name"]
    assert component.properties[1].value_range is not None
    assert component.properties[1].value_range.min == 2700
    assert component.events[0].event_id == 1
    assert product.device_actions[0].targets == ["light"]


def test_product_schema_converter_applies_spec_corrections() -> None:
    """产品 schema 转换应先应用保守 correction 规则."""
    product = YeelightProductSchemaConverter().convert(
        {
            "pid": 1006,
            "name": "Correction lamp",
            "category": "light",
            "components": [
                {
                    "cid": 4,
                    "name": "brightness light",
                    "type": 0,
                    "category": "light",
                    "properties": [
                        {"propId": "p", "format": "bool", "operators": ["toggle"]},
                        {
                            "propId": "l",
                            "format": "uint16",
                            "valueRange": {"min": 1, "max": 100},
                            "operators": ["adjust"],
                        },
                        {"propId": "luminance", "format": "uint32", "access": 4},
                    ],
                }
            ],
        }
    )

    props = {prop.prop_id: prop for prop in product.components[0].properties}
    assert props["p"].format == "boolean"
    assert props["p"].access == "read_write"
    assert props["l"].access == "read_write"
    assert props["l"].value_range is not None
    assert props["l"].value_range.step is None
    assert props["luminance"].kind == "state"
    assert props["luminance"].access == "read_only"


def test_product_schema_converter_deduplicates_component_sources() -> None:
    """components/customComponents duplicates should produce stable unique component ids."""
    product = YeelightProductSchemaConverter().convert(
        {
            "pid": 1005,
            "name": "Merged relay",
            "category": "relay_switch",
            "components": [
                {
                    "cid": 20,
                    "name": "switch control",
                    "type": 0,
                    "category": "relay_switch",
                    "index": 1,
                    "properties": [{"propId": "p", "operators": ["set"]}],
                },
                {
                    "cid": 20,
                    "name": "switch control",
                    "type": 0,
                    "category": "relay_switch",
                    "index": 2,
                    "properties": [{"propId": "p", "operators": ["set"]}],
                },
            ],
            "customComponents": [
                {
                    "cid": 20,
                    "name": "switch control",
                    "type": 0,
                    "category": "relay_switch",
                    "index": 1,
                    "properties": [{"propId": "p", "operators": ["set"]}],
                },
            ],
            "supportActions": [{"actionName": "identify"}],
        }
    )

    assert [component.component_id for component in product.components] == [
        "relay_switch_1",
        "relay_switch_2",
    ]
    assert product.device_actions[0].targets == [
        "relay_switch_1",
        "relay_switch_2",
    ]
