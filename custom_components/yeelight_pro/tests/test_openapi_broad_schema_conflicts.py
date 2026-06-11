"""OpenAPI broad schema conflict regressions."""

from __future__ import annotations

from custom_components.yeelight_pro.core.device_payload import DevicePayloadBuilder

from .openapi_subdevice_helpers import candidate_platform_components as _candidate_platform_components
from .openapi_subdevice_helpers import openapi_prop as _prop


def test_conflicting_light_product_schema_does_not_override_sensor_evidence() -> None:
    """运行时属性证明为传感器时，宽泛 light schema 不能重新生成 light。"""
    schema = {
        "pid": 9030,
        "name": "色温灯",
        "category": "light",
        "components": [
            {
                "cid": 4,
                "name": "color temperature light",
                "category": "light",
                "properties": [
                    {"propId": "p", "operators": ["set", "toggle"]},
                    {"propId": "l", "operators": ["set"]},
                    {"propId": "ct", "operators": ["set"]},
                ],
            }
        ],
    }
    builder = DevicePayloadBuilder()
    data, _gateways = builder.build_runtime_payloads(
        devices=[
            {
                "id": 9031,
                "name": "传感设备 A",
                "category": "light",
                "pid": 9030,
                "properties": [
                    _prop("mv", True, "人体移动", "boolean"),
                    _prop("luminance", 188, "照度", "uint16", unit="lx"),
                    _prop("bl", 91, "电量", "uint8", unit="%"),
                ],
            },
            {
                "id": 9032,
                "name": "传感设备 B",
                "category": "light",
                "pid": 9030,
                "properties": [
                    _prop("t", 24.5, "温度", "float", unit="°C"),
                    _prop("h", 58, "湿度", "uint8", unit="%"),
                    _prop("bl", 80, "电量", "uint8", unit="%"),
                ],
            },
            {
                "id": 9033,
                "name": "传感设备 C",
                "category": "light",
                "pid": 9030,
                "properties": [
                    _prop("dc", False, "是否接触", "boolean"),
                    _prop("alm", True, "防拆", "boolean"),
                    _prop("bl", 73, "电量", "uint8", unit="%"),
                ],
            },
        ],
        gateways=[],
        product_schemas={9030: schema},
        apply_runtime_overrides=lambda payload: payload,
    )

    assert data[9031]["iot_category"] == "human_sensor"
    assert data[9031]["ha_product_model"]["schema_version"] == "runtime-v1"
    assert data[9031]["device_info"]["model"] == "人体传感器"
    assert not any(
        platform == "light"
        for platform, _component in _candidate_platform_components(data[9031])
    )

    assert data[9032]["iot_category"] == "other"
    assert data[9032]["ha_product_model"]["schema_version"] == "runtime-v1"
    assert data[9032]["device_info"]["model"] == "温湿度传感器"
    assert _candidate_platform_components(data[9032]) == {
        ("sensor", "temperature"),
        ("sensor", "humidity"),
        ("sensor", "battery"),
    }

    assert data[9033]["iot_category"] == "contact_sensor"
    assert data[9033]["ha_product_model"]["schema_version"] == "runtime-v1"
    assert data[9033]["device_info"]["model"] == "门磁传感器"
    assert not any(
        platform == "light"
        for platform, _component in _candidate_platform_components(data[9033])
    )


def test_conflicting_light_schema_respects_runtime_temp_control_category() -> None:
    """运行时 category 明确为 temp_control 时，错误 light schema 不能抢主平台。"""
    builder = DevicePayloadBuilder()
    data, _gateways = builder.build_runtime_payloads(
        devices=[
            {
                "id": 9034,
                "name": "浴室温控器",
                "category": "light",
                "pid": 9034,
                "subDeviceList": [
                    {
                        "index": 1,
                        "category": "temp_control",
                        "name": "temp control",
                        "properties": [
                            _prop("p", True, "开关", "boolean", operators=["set"]),
                            _prop("t", 24.5, "温度", "float", unit="°C"),
                            _prop("h", 58, "湿度", "uint8", unit="%"),
                            _prop("tgt", 28, "目标温度", "float", unit="°C"),
                        ],
                    }
                ],
            }
        ],
        gateways=[],
        product_schemas={
            9034: {
                "pid": 9034,
                "name": "色温灯",
                "category": "light",
                "components": [
                    {
                        "cid": 4,
                        "name": "color temperature light",
                        "category": "light",
                        "properties": [
                            {"propId": "p", "operators": ["set", "toggle"]},
                            {"propId": "l", "operators": ["set"]},
                            {"propId": "ct", "operators": ["set"]},
                        ],
                    }
                ],
            }
        },
        apply_runtime_overrides=lambda payload: payload,
    )
    device = data[9034]

    assert device["iot_category"] == "temp_control"
    assert device["ha_platform"] == "climate"
    assert device["ha_platform_candidates"][0] == "climate"
    assert not any(
        platform == "light"
        for platform, _component in _candidate_platform_components(device)
    )
