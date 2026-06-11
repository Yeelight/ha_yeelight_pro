"""OpenAPI broad category projection regressions."""

from __future__ import annotations

from custom_components.yeelight_pro.const import DOMAIN
from custom_components.yeelight_pro.projector.light import project_lights

from .openapi_subdevice_helpers import build_openapi_device as _build_device
from .openapi_subdevice_helpers import candidate_platform_components as _candidate_platform_components
from .openapi_subdevice_helpers import openapi_prop as _prop


def test_openapi_broad_light_contact_sensor_does_not_project_light() -> None:
    """OpenAPI 粗 category=light 的门磁只能生成门磁/电量候选。"""
    device = _build_device(
        {
            "id": 9010,
            "name": "玄关门磁传感器",
            "category": "light",
            "properties": [
                _prop("dc", False, "是否接触", "boolean"),
                _prop("alm", True, "防拆", "boolean"),
                _prop("bl", 73, "电量", "uint8", unit="%"),
            ],
        }
    )

    candidates = _candidate_platform_components(device)

    assert device["iot_category"] == "contact_sensor"
    assert device["ha_platform_candidates"] == ["binary_sensor", "sensor"]
    assert ("light", "contact_sensor") not in candidates
    assert candidates == {
        ("binary_sensor", "door"),
        ("binary_sensor", "tamper"),
        ("sensor", "battery"),
    }


def test_openapi_broad_light_human_sensor_does_not_project_light() -> None:
    """OpenAPI 粗 category=light 的人体设备只能生成 motion/照度/电量候选。"""
    device = _build_device(
        {
            "id": 9011,
            "name": "走廊人体传感器",
            "category": "light",
            "properties": [
                _prop("mv", True, "人体移动", "boolean"),
                _prop("luminance", 188, "照度", "uint16", unit="lx"),
                _prop("bl", 91, "电量", "uint8", unit="%"),
            ],
            "events": [{"id": 8, "name": "motion.true"}],
        }
    )

    candidates = _candidate_platform_components(device)

    assert device["iot_category"] == "human_sensor"
    assert device["ha_platform_candidates"] == [
        "binary_sensor",
        "sensor",
        "event",
    ]
    assert not any(platform == "light" for platform, _component in candidates)
    assert {
        ("binary_sensor", "motion"),
        ("sensor", "illuminance"),
        ("sensor", "battery"),
    } <= candidates


def test_openapi_broad_light_temperature_humidity_does_not_project_light() -> None:
    """OpenAPI 粗 category=light 的温湿度设备只能生成 sensor 候选。"""
    device = _build_device(
        {
            "id": 9012,
            "name": "客厅温湿度传感器",
            "category": "light",
            "properties": [
                _prop("t", 24.5, "温度", "float", unit="°C"),
                _prop("h", 58, "湿度", "uint8", unit="%"),
                _prop("bl", 80, "电量", "uint8", unit="%"),
            ],
        }
    )

    candidates = _candidate_platform_components(device)

    assert device["iot_category"] == "other"
    assert device["ha_platform_candidates"] == ["sensor"]
    assert candidates == {
        ("sensor", "temperature"),
        ("sensor", "humidity"),
        ("sensor", "battery"),
    }


def test_openapi_broad_light_illuminance_sensor_does_not_project_light() -> None:
    """OpenAPI 粗 category=light 的照度设备只能生成 sensor 候选。"""
    device = _build_device(
        {
            "id": 9013,
            "name": "门厅照度传感器",
            "category": "light",
            "properties": [
                _prop("luminance", 322, "照度", "uint16", unit="lx"),
                _prop("bl", 88, "电量", "uint8", unit="%"),
            ],
        }
    )

    candidates = _candidate_platform_components(device)

    assert device["iot_category"] == "light_sensor"
    assert device["ha_platform_candidates"] == ["sensor"]
    assert candidates == {
        ("sensor", "illuminance"),
        ("sensor", "battery"),
    }


def test_openapi_light_payload_still_projects_light() -> None:
    """真实灯具属性仍应生成 light 候选。"""
    device = _build_device(
        {
            "id": 9014,
            "name": "客厅筒灯",
            "category": "light",
            "properties": [
                _prop("p", True, "开关", "boolean", operators=["set", "toggle"]),
                _prop("l", 80, "亮度", "uint8", unit="%", operators=["set", "adjust"]),
                _prop("ct", 4000, "色温", "uint16", operators=["set", "adjust"]),
            ],
        }
    )

    candidates = _candidate_platform_components(device)

    assert device["iot_category"] == "light"
    assert device["ha_platform_candidates"] == ["light"]
    assert candidates == {("light", "light")}


def test_single_openapi_light_uses_device_name_as_primary_entity() -> None:
    """单个主灯实体名称应交给 HA 使用设备名，避免所有灯都叫照明."""
    device = _build_device(
        {
            "id": 9015,
            "name": "餐厅吊灯",
            "category": "light",
            "properties": [
                _prop("p", True, "开关", "boolean", operators=["set", "toggle"]),
                _prop("l", 80, "亮度", "uint8", unit="%", operators=["set", "adjust"]),
            ],
        }
    )

    [light] = project_lights(device, domain=DOMAIN)

    assert light.component_id == "light"
    assert light.name is None


def test_openapi_double_switch_ignores_extra_third_subdevice() -> None:
    """双键开关的 subDeviceList 如果带第三路残留，也只生成两路实体."""
    device = _build_device(
        {
            "id": 9016,
            "name": "厨房双键开关",
            "category": "relay_switch",
            "subDeviceList": [
                {
                    "index": 1,
                    "category": "relay_switch",
                    "properties": [_prop("p", True, "开关", "boolean", operators=["set"])],
                },
                {
                    "index": 2,
                    "category": "relay_switch",
                    "properties": [_prop("p", False, "开关", "boolean", operators=["set"])],
                },
                {
                    "index": 3,
                    "category": "relay_switch",
                    "properties": [_prop("p", True, "开关", "boolean", operators=["set"])],
                },
            ],
        }
    )

    candidates = _candidate_platform_components(device)

    assert candidates == {("switch", "switch_1"), ("switch", "switch_2")}
