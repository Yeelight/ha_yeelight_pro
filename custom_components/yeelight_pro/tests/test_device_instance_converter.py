"""Device instance converter regression tests."""
from __future__ import annotations

from custom_components.yeelight_pro.converter.device import (
    YeelightLanDeviceInstanceConverter,
)
from custom_components.yeelight_pro.converter.product import (
    YeelightProductSchemaConverter,
)


def test_device_converter_fallback_filters_runtime_state() -> None:
    """Fallback conversion must keep only runtime keys relevant to the device type."""
    payload = {
        "id": 123,
        "name": "Fallback Lamp",
        "type": "light",
        "model_id": "runtime-light",
        "online": True,
        "mac": "AA:BB:CC:DD:EE:FF",
        "params": {
            "p": True,
            "l": 75,
            "ct": 4000,
            "ignored": "metadata",
        },
    }

    device = YeelightLanDeviceInstanceConverter().convert(payload)

    assert device.device_id == "123"
    assert device.name == "Fallback Lamp"
    assert device.device_info is not None
    assert device.device_info.identifiers == [["yeelight_pro", "device:123"]]
    assert device.device_info.connections == [["mac", "AA:BB:CC:DD:EE:FF"]]
    assert len(device.components) == 1
    component = device.components[0]
    assert component.component_id == "light"
    assert component.state == {"p": True, "l": 75, "ct": 4000}


def test_device_converter_uses_product_schema_runtime_mapping() -> None:
    """Schema-aware conversion must route params to component state."""
    product = YeelightProductSchemaConverter().convert(
        {
            "pid": 1002,
            "name": "Schema lamp",
            "category": "light",
            "components": [
                {
                    "cid": 1,
                    "name": "basic",
                    "type": 1,
                    "properties": [{"propId": "name"}, {"propId": "o"}],
                },
                {
                    "cid": 4,
                    "name": "color light",
                    "type": 0,
                    "category": "light",
                    "index": 1,
                    "properties": [
                        {"propId": "p", "operators": ["set"]},
                        {"propId": "l", "operators": ["set"]},
                    ],
                },
            ],
        }
    )

    device = YeelightLanDeviceInstanceConverter().convert(
        {
            "id": "schema-lamp-1",
            "name": "Schema Lamp",
            "pid": 1002,
            "online": True,
            "params": {
                "p": True,
                "l": 55,
                "name": "Ignored global name",
            },
        },
        product_model=product,
    )

    assert [component.component_id for component in device.components] == ["light"]
    assert device.components[0].category == "light"
    assert device.components[0].state == {"p": True, "l": 55}


def test_device_converter_applies_schema_zoom_scale_to_runtime_state() -> None:
    """Schema-aware runtime state 应按物模型 zoom/scale 转成实际值."""
    product = YeelightProductSchemaConverter().convert(
        {
            "pid": 1011,
            "name": "Scaled sensor",
            "category": "temp_control",
            "components": [
                {
                    "cid": 63,
                    "name": "temp control",
                    "type": 0,
                    "category": "temp_control",
                    "properties": [
                        {
                            "propId": "t",
                            "format": "int",
                            "access": 5,
                            "zoom": 1,
                            "scale": 10,
                        },
                        {
                            "propId": "curp",
                            "format": "int",
                            "access": 5,
                            "zoom": -1,
                            "scale": 10,
                        },
                        {
                            "propId": "raw",
                            "format": "int",
                            "access": 5,
                            "zoom": 0,
                            "scale": 10,
                        },
                        {"propId": "p", "format": "bool", "operators": ["set"]},
                    ],
                }
            ],
        }
    )

    device = YeelightLanDeviceInstanceConverter().convert(
        {
            "id": "scaled-sensor-1",
            "name": "Scaled Sensor",
            "pid": 1011,
            "online": True,
            "params": {
                "t": 235,
                "curp": "12",
                "raw": 9,
                "p": True,
            },
        },
        product_model=product,
    )

    assert device.components[0].state == {
        "t": 23.5,
        "curp": 120,
        "raw": 9,
        "p": True,
    }


def test_device_converter_routes_indexed_schema_keys_without_cross_talk() -> None:
    """Indexed runtime keys must map to their matching component instances."""
    product = YeelightProductSchemaConverter().convert(
        {
            "pid": 1003,
            "name": "Dual relay",
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
        }
    )

    device = YeelightLanDeviceInstanceConverter().convert(
        {
            "id": "relay-1",
            "name": "Dual Relay",
            "pid": 1003,
            "online": True,
            "params": {"1-p": True, "2-p": False, "p": True},
        },
        product_model=product,
    )

    assert [component.component_id for component in device.components] == [
        "relay_switch_1",
        "relay_switch_2",
    ]
    assert device.components[0].state == {"p": True}
    assert device.components[1].state == {"p": False}


def test_device_converter_excludes_global_config_and_info_state() -> None:
    """Global/config/info schema fields must not become runtime component state."""
    product = YeelightProductSchemaConverter().convert(
        {
            "pid": 1004,
            "name": "Config heavy lamp",
            "category": "light",
            "components": [
                {
                    "cid": 44,
                    "name": "basic",
                    "type": 1,
                    "properties": [
                        {"propId": "name"},
                        {"propId": "o"},
                        {"propId": "fv"},
                        {"propId": "localToken", "operators": ["set"]},
                    ],
                },
                {
                    "cid": 83,
                    "name": "KNX Power config component",
                    "type": 1,
                    "properties": [
                        {"propId": "cfg", "type": 1, "operators": ["set"]},
                    ],
                },
                {
                    "cid": 4,
                    "name": "brightness light",
                    "type": 0,
                    "category": "light",
                    "index": 1,
                    "properties": [
                        {"propId": "p", "operators": ["set"]},
                        {"propId": "l", "operators": ["set"]},
                    ],
                },
            ],
        }
    )

    device = YeelightLanDeviceInstanceConverter().convert(
        {
            "id": "lamp-config",
            "name": "Config Lamp",
            "pid": 1004,
            "online": True,
            "params": {
                "name": "Do not expose",
                "o": True,
                "fv": "1.2.3",
                "localToken": "secret-token",
                "cfg": 1,
                "p": True,
                "l": 70,
            },
        },
        product_model=product,
    )

    assert [component.component_id for component in device.components] == ["light"]
    assert device.components[0].state == {"p": True, "l": 70}
