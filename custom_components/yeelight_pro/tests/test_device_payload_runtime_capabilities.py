"""Runtime device capability projection tests."""

from __future__ import annotations

from custom_components.yeelight_pro.core.device_payload import DevicePayloadBuilder
from custom_components.yeelight_pro.entity_candidates import iter_device_entity_candidates


def test_build_runtime_payloads_infers_real_category_from_properties() -> None:
    """云端粗品类缺失或错误时，应按属性能力修正设备主平台与型号。"""
    builder = DevicePayloadBuilder()

    data, _gateways = builder.build_runtime_payloads(
        devices=[
            {
                "id": 311930423,
                "name": "玄关门磁传感器",
                "category": "light",
                "pid": 301,
                "roomId": 10,
                "properties": [
                    {"propId": "dc", "value": True},
                    {"propId": "alm", "value": False},
                    {"propId": "bl", "value": 87},
                ],
            },
            {
                "id": 311930425,
                "name": "客厅温湿度传感器",
                "category": "light",
                "pid": 302,
                "roomId": 11,
                "properties": [
                    {"propId": "t", "value": 25},
                    {"propId": "h", "value": 58},
                ],
            },
            {
                "id": 311930424,
                "name": "客厅窗帘电机",
                "category": "relay_switch",
                "pid": 303,
                "roomId": 11,
                "properties": [
                    {"propId": "cp", "value": 20},
                    {"propId": "tp", "value": 80},
                ],
            },
        ],
        gateways=[],
        product_schemas={},
        apply_runtime_overrides=lambda payload: payload,
        rooms=[
            {"id": "10", "name": "玄关"},
            {"id": "11", "name": "客厅"},
        ],
    )

    contact = data[311930423]
    climate_sensor = data[311930425]
    curtain = data[311930424]
    assert contact["iot_category"] == "contact_sensor"
    assert "type" not in contact
    assert contact["ha_platform"] == "binary_sensor"
    assert contact["ha_platform_candidates"] == ["binary_sensor", "sensor", "event"]
    assert contact["device_info"]["model"] == "门磁传感器"
    assert contact["ha_device_instance"]["components"][0]["state"] == {
        "dc": True,
        "alm": False,
        "bl": 87,
    }
    assert climate_sensor["iot_category"] == "other"
    assert "type" not in climate_sensor
    assert climate_sensor["ha_platform"] == "sensor"
    assert climate_sensor["ha_platform_candidates"] == ["sensor"]
    assert climate_sensor["device_info"]["model"] == "温湿度传感器"
    assert curtain["iot_category"] == "curtain"
    assert "type" not in curtain
    assert curtain["ha_platform"] == "cover"
    assert curtain["ha_platform_candidates"] == ["cover"]
    assert curtain["device_info"]["model"] == "窗帘"


def test_runtime_payloads_project_entities_from_each_supported_property() -> None:
    """属性级能力必须进入 HA 实体候选，而不是把所有设备压成一个开关."""
    builder = DevicePayloadBuilder()

    data, _gateways = builder.build_runtime_payloads(
        devices=[
            _device(401, "厨房筒灯", "light", 4010, 1, [
                {"propId": "p", "value": True},
                {"propId": "l", "value": 80},
                {"propId": "ct", "value": 4100},
            ]),
            _device(402, "客厅人体传感器", "light", 4020, 2, [
                {"propId": "mv", "value": True},
                {"propId": "alm", "value": False},
                {"propId": "luminance", "value": 168},
                {"propId": "bl", "value": 96},
            ]),
            _device(403, "阳台窗帘电机", "relay_switch", 4030, 3, [
                {"propId": "cp", "value": 40},
                {"propId": "tp", "value": 90},
            ]),
            _device(404, "主卧温湿度传感器", "light", 4040, 4, [
                {"propId": "t", "value": 24.5},
                {"propId": "h", "value": 57},
                {"propId": "bl", "value": 83},
            ]),
        ],
        gateways=[],
        product_schemas={},
        apply_runtime_overrides=lambda payload: payload,
        rooms=[
            {"id": "1", "name": "厨房"},
            {"id": "2", "name": "客厅"},
            {"id": "3", "name": "阳台"},
            {"id": "4", "name": "主卧"},
        ],
    )

    light_candidates = {item.platform for item in iter_device_entity_candidates(data[401])}
    human_candidates = _candidate_pairs(data[402])
    curtain_candidates = {item.platform for item in iter_device_entity_candidates(data[403])}
    temp_candidates = _candidate_pairs(data[404])

    assert data[402]["iot_category"] == "human_sensor"
    assert "type" not in data[402]
    assert data[402]["ha_platform"] == "binary_sensor"
    assert data[402]["ha_platform_candidates"] == ["binary_sensor", "sensor"]
    assert data[402]["device_info"]["model"] == "人体传感器"
    assert data[402]["device_info"]["suggested_area"] == "客厅"
    assert "light" in light_candidates
    assert "light" not in {item.platform for item in iter_device_entity_candidates(data[402])}
    assert "light" not in {item.platform for item in iter_device_entity_candidates(data[404])}
    assert human_candidates == {
        ("binary_sensor", "motion"),
        ("binary_sensor", "tamper"),
        ("sensor", "illuminance"),
        ("sensor", "battery"),
    }
    assert curtain_candidates == {"cover"}
    assert temp_candidates == {
        ("sensor", "temperature"),
        ("sensor", "humidity"),
        ("sensor", "battery"),
    }


def test_runtime_payloads_do_not_infer_capabilities_from_safety_name() -> None:
    """云端粗 light 且无细分证据时，设备名不能生成任何实体。"""
    builder = DevicePayloadBuilder()

    data, _gateways = builder.build_runtime_payloads(
        devices=[{
            "id": 405,
            "name": "厨房烟雾传感器",
            "category": "light",
            "pid": 4050,
            "roomId": 1,
            "properties": [],
        }],
        gateways=[],
        product_schemas={},
        apply_runtime_overrides=lambda payload: payload,
        rooms=[{"id": "1", "name": "厨房"}],
    )

    device = data[405]

    assert device["iot_category"] == "light"
    assert "ha_platform" not in device
    assert "ha_platform_candidates" not in device
    assert device["device_info"]["model"] == "灯具"
    assert [(item.platform, item.component_id) for item in iter_device_entity_candidates(device)] == []


def _device(
    device_id: int,
    name: str,
    category: str,
    pid: int,
    room_id: int,
    properties: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "id": device_id,
        "name": name,
        "category": category,
        "pid": pid,
        "roomId": room_id,
        "properties": properties,
    }


def _candidate_pairs(device: dict[str, object]) -> set[tuple[str, str]]:
    return {
        (item.platform, str(item.component_id))
        for item in iter_device_entity_candidates(device)
    }
