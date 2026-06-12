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

    assert device["category"] == "light"
    assert device["source_category"] == "light"
    assert device["effective_category"] == "contact_sensor"
    assert device["iot_category"] == "contact_sensor"
    assert device["ha_platform_candidates"] == ["binary_sensor", "sensor", "event"]
    assert ("light", "contact_sensor") not in candidates
    assert candidates == {
        ("binary_sensor", "door"),
        ("binary_sensor", "tamper"),
        ("event", "contact_sensor"),
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


def test_documented_light_sensor_component_with_motion_stays_light_sensor() -> None:
    """CSV 中光照/雷达光感组件可含 mv，组件 category 是结构化能力证据."""
    device = _build_device(
        {
            "id": 9017,
            "name": "走廊光感雷达",
            "category": "light",
            "subDeviceList": [
                {
                    "index": 1,
                    "category": "light_sensor",
                    "name": "zonalShieldIlluminanceRadarSensor",
                    "properties": [
                        _prop("mv", True, "人体移动", "boolean"),
                        _prop("luminance", 188, "照度", "uint16", unit="lx"),
                        _prop("bl", 91, "电量", "uint8", unit="%"),
                    ],
                }
            ],
        }
    )

    candidates = _candidate_platform_components(device)

    assert device["iot_category"] == "light_sensor"
    assert device["ha_platform"] == "sensor"
    assert device["ha_platform_candidates"] == ["sensor", "binary_sensor"]
    assert not any(platform == "light" for platform, _component in candidates)
    assert {
        ("binary_sensor", "motion"),
        ("sensor", "illuminance"),
        ("sensor", "battery"),
    } <= candidates


def test_documented_light_sensor_property_bundle_overrides_broad_light() -> None:
    """光照传感器2的配置属性组合保留 light_sensor 大类和 sensor 主平台."""
    device = _build_device(
        {
            "id": 9018,
            "name": "厨房烟雾传感器",
            "category": "light",
            "properties": [
                _prop("mv", True, "人体移动", "boolean"),
                _prop("luminance", 188, "照度", "uint16", unit="lx"),
                _prop("sens_range", 3, "感应范围", "uint8", operators=["set"]),
                _prop("lumi_setting", 120, "照度设置", "uint16", operators=["set"]),
                _prop("delay_time", 30, "延时时间", "uint16", operators=["set"]),
            ],
        }
    )

    candidates = _candidate_platform_components(device)

    assert device["iot_category"] == "light_sensor"
    assert device["ha_platform"] == "sensor"
    assert device["ha_platform_candidates"] == ["sensor", "binary_sensor"]
    assert not any(platform == "light" for platform, _component in candidates)
    assert {
        ("binary_sensor", "motion"),
        ("sensor", "illuminance"),
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


def test_openapi_broad_light_fresh_air_projects_fan_from_documented_props() -> None:
    """粗 light 遇到 CSV 新风属性时，按 temp_control/fan 能力覆盖品类。"""
    device = _build_device(
        {
            "id": 9030,
            "name": "新风",
            "category": "light",
            "properties": [
                _prop("vmcp", True, "新风开关", "boolean", operators=["set"]),
                _prop(
                    "vmcf",
                    30,
                    "新风风速",
                    "uint8",
                    range_={"min": 1, "max": 100, "step": 1},
                    operators=["set"],
                ),
            ],
        }
    )

    candidates = _candidate_platform_components(device)

    assert device["iot_category"] == "temp_control"
    assert device["ha_platform"] == "fan"
    assert device["ha_platform_candidates"] == ["fan"]
    assert candidates == {("fan", "fresh_air")}


def test_openapi_light_named_smoke_without_capabilities_is_device_only() -> None:
    """名称不能生成安全能力；无能力证据时不能按粗 light 生成假实体。"""
    device = _build_device(
        {
            "id": 9020,
            "name": "厨房烟雾传感器",
            "category": "light",
            "properties": [],
        }
    )

    candidates = _candidate_platform_components(device)

    assert device["iot_category"] == "light"
    assert "ha_platform" not in device
    assert "ha_platform_candidates" not in device
    assert candidates == set()


def test_openapi_light_named_smoke_with_events_projects_event_only() -> None:
    """显式 OpenAPI events 只生成 event 候选，并按能力覆盖粗 light。"""
    device = _build_device(
        {
            "id": 9021,
            "name": "厨房烟雾传感器",
            "category": "light",
            "properties": [],
            "events": [
                {"id": 14, "name": "power.alarm"},
                {"id": 15, "name": "power.normal"},
            ],
        }
    )

    candidates = _candidate_platform_components(device)

    assert device["iot_category"] == "other"
    assert device["ha_platform"] == "event"
    assert device["ha_platform_candidates"] == ["event"]
    assert candidates == {("event", "safety_alarm")}


def test_openapi_light_named_smoke_with_product_schema_events_projects_event() -> None:
    """产品 schema 明确声明 events 时生成 event 候选并覆盖粗 light。"""
    from custom_components.yeelight_pro.core.device_payload import DevicePayloadBuilder

    builder = DevicePayloadBuilder()
    data, _gateways = builder.build_runtime_payloads(
        devices=[
            {
                "id": 9022,
                "name": "厨房烟雾传感器",
                "category": "light",
                "pid": 90220,
                "properties": [],
            }
        ],
        gateways=[],
        product_schemas={
            90220: {
                "pid": 90220,
                "name": "Vendor alarm schema",
                "category": "light",
                "components": [
                    {
                        "cid": 900,
                        "name": "vendor power alarm",
                        "category": "vendor power alarm",
                        "events": [
                            {"eventId": 14, "name": "power.alarm"},
                            {"eventId": 15, "name": "power.normal"},
                        ],
                    }
                ],
            }
        },
        apply_runtime_overrides=lambda payload: payload,
    )
    device = data[9022]

    assert device["iot_category"] == "other"
    assert device["ha_platform_candidates"] == ["event"]
    assert _candidate_platform_components(device) == {("event", "vendor_power_alarm")}


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


def test_openapi_light_power_only_does_not_project_light() -> None:
    """category=light+p 证据不足，不能生造只有开关的灯实体."""
    device = _build_device(
        {
            "id": 9019,
            "name": "卧室灯带",
            "category": "light",
            "properties": [
                _prop("p", True, "开关", "boolean", operators=["set", "toggle"]),
            ],
        }
    )

    assert project_lights(device, domain=DOMAIN) == []


def test_openapi_user_named_double_switch_keeps_structured_third_subdevice() -> None:
    """用户设备名写双键时，subDeviceList 里的真实第三路仍必须生成实体."""
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

    assert candidates == {
        ("switch", "switch_1"),
        ("switch", "switch_2"),
        ("switch", "switch_3"),
    }
