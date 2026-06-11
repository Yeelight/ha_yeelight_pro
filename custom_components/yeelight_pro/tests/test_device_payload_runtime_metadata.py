"""Runtime device payload metadata tests."""

from __future__ import annotations

from custom_components.yeelight_pro.core.device_payload import DevicePayloadBuilder
from custom_components.yeelight_pro.entity_candidates import iter_device_entity_candidates
from .device_payload_helpers import (
    _DeviceInstanceConverter,
    _ProductSchemaConverter,
)


def test_build_runtime_payloads_enriches_canonical_device_info_from_rooms() -> None:
    """运行态 payload 应把设备名称、产品型号和房间同步到 HA device_info."""
    device_converter = _DeviceInstanceConverter()
    builder = DevicePayloadBuilder(
        product_schema_converter=_ProductSchemaConverter(),  # type: ignore[arg-type]
        device_instance_converter=device_converter,  # type: ignore[arg-type]
    )

    data, _gateways = builder.build_runtime_payloads(
        devices=[
            {
                "id": 387958,
                "name": "客厅主灯",
                "category": "light",
                "pid": 100,
                "roomId": "397",
            }
        ],
        gateways=[],
        product_schemas={100: {"pid": 100, "name": "智能筒灯"}},
        apply_runtime_overrides=lambda payload: payload,
        rooms=[{"id": "397", "name": "客厅"}],
    )

    device_info = data[387958]["ha_device_instance"]["device_info"]
    assert data[387958]["name"] == "客厅主灯"
    assert data[387958]["room_name"] == "客厅"
    assert device_info["name"] == "客厅主灯"
    assert device_info["model"] == "Fake Product"
    assert device_info["model_id"] == "model-100"
    assert device_info["suggested_area"] == "客厅"
    assert device_info["identifiers"] == [
        ["yeelight_pro", "387958"],
        ["yeelight_pro", "device:387958"],
    ]
    assert device_converter.device_infos == [device_info]


def test_build_runtime_payloads_supports_lan_roomid_and_name_aliases() -> None:
    """本地网关风格 n/roomid 字段也应生成友好的 HA 设备名和区域建议."""
    builder = DevicePayloadBuilder(
        product_schema_converter=_ProductSchemaConverter(),  # type: ignore[arg-type]
        device_instance_converter=_DeviceInstanceConverter(),  # type: ignore[arg-type]
    )

    data, _gateways = builder.build_runtime_payloads(
        devices=[
            {
                "id": 429392,
                "n": "玄关射灯",
                "category": "light",
                "pid": 100,
                "roomid": 12,
            }
        ],
        gateways=[],
        product_schemas={100: {"pid": 100, "name": "智能射灯"}},
        apply_runtime_overrides=lambda payload: payload,
        rooms=[{"id": "12", "name": "入户门"}],
    )

    device_info = data[429392]["ha_device_instance"]["device_info"]
    assert device_info["name"] == "玄关射灯"
    assert device_info["suggested_area"] == "入户门"


def test_build_runtime_payloads_infers_canonical_device_info_without_schema() -> None:
    """缺少官方 schema 时也应生成设备级 registry metadata."""
    builder = DevicePayloadBuilder()

    data, _gateways = builder.build_runtime_payloads(
        devices=[
            {
                "id": 304784333,
                "name": "客厅筒灯 1",
                "category": "light",
                "pid": 200,
                "roomId": 397,
                "properties": [
                    {"propId": "p", "value": True},
                    {"propId": "l", "value": 80},
                ],
            }
        ],
        gateways=[],
        product_schemas={},
        apply_runtime_overrides=lambda payload: payload,
        rooms=[{"id": "397", "name": "客厅"}],
    )

    device = data[304784333]
    device_info = device["ha_device_instance"]["device_info"]
    assert device["ha_product_model"]["schema_version"] == "runtime-v1"
    assert device["model_id"] == "YL-200"
    assert device_info["name"] == "客厅筒灯 1"
    assert device_info["model"] == "筒灯"
    assert device_info["suggested_area"] == "客厅"
    assert device_info["identifiers"] == [
        ["yeelight_pro", "304784333"],
        ["yeelight_pro", "device:304784333"],
    ]
    assert device["ha_device_instance"]["components"][0]["state"] == {
        "p": True,
        "l": 80,
    }


def test_runtime_metadata_replaces_generic_cloud_model_labels() -> None:
    """云端粗 model 不应短路设备名和属性推导出的友好产品型号."""
    builder = DevicePayloadBuilder()

    data, _gateways = builder.build_runtime_payloads(
        devices=[
            {
                "id": 304784337,
                "name": "E20射灯1",
                "category": "light",
                "model": "light",
                "pid": 202,
                "roomId": 397,
                "properties": [
                    {"propId": "p", "value": True},
                    {"propId": "l", "value": 70},
                    {"propId": "ct", "value": 3900},
                ],
            },
            {
                "id": 304784338,
                "name": "墙壁开关1",
                "category": "relay_switch",
                "model": "relay_switch",
                "pid": 203,
                "roomId": 397,
                "properties": [],
            },
        ],
        gateways=[],
        product_schemas={},
        apply_runtime_overrides=lambda payload: payload,
        rooms=[{"id": "397", "name": "客厅"}],
    )

    light_info = data[304784337]["ha_device_instance"]["device_info"]
    switch_info = data[304784338]["device_info"]
    assert light_info["model"] == "E20 射灯"
    assert light_info["model_id"] == "YL-202"
    assert switch_info["model"] == "墙壁开关"
    assert switch_info["model_id"] == "YL-203"


def test_runtime_metadata_does_not_expose_internal_runtime_model_id() -> None:
    """没有真实产品 ID 时，HA device_info 不应显示 runtime-* 内部兜底值."""
    builder = DevicePayloadBuilder()

    data, _gateways = builder.build_runtime_payloads(
        devices=[
            {
                "id": 304784339,
                "name": "未识别灯具",
                "category": "light",
                "properties": [
                    {"propId": "p", "value": True},
                    {"propId": "l", "value": 70},
                ],
            }
        ],
        gateways=[],
        product_schemas={},
        apply_runtime_overrides=lambda payload: payload,
    )

    device_info = data[304784339]["ha_device_instance"]["device_info"]
    assert data[304784339]["ha_product_model"]["product"]["model_id"] == "runtime-light"
    assert device_info["model"] == "易来照明设备"
    assert "model_id" not in device_info


def test_build_runtime_payloads_infers_real_category_from_properties_and_name() -> None:
    """云端粗品类缺失或错误时，应按属性和名称修正设备主平台与型号."""
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
    assert contact["ha_platform_candidates"] == ["binary_sensor", "sensor"]
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
    assert curtain["device_info"]["model"] == "窗帘电机"


def test_runtime_payloads_project_entities_from_each_supported_property() -> None:
    """属性级能力必须进入 HA 实体候选，而不是把所有设备压成一个开关."""
    builder = DevicePayloadBuilder()

    data, _gateways = builder.build_runtime_payloads(
        devices=[
            {
                "id": 401,
                "name": "厨房筒灯",
                "category": "light",
                "pid": 4010,
                "roomId": 1,
                "properties": [
                    {"propId": "p", "value": True},
                    {"propId": "l", "value": 80},
                    {"propId": "ct", "value": 4100},
                ],
            },
            {
                "id": 402,
                "name": "客厅人体传感器",
                "category": "light",
                "pid": 4020,
                "roomId": 2,
                "properties": [
                    {"propId": "mv", "value": True},
                    {"propId": "alm", "value": False},
                    {"propId": "luminance", "value": 168},
                    {"propId": "bl", "value": 96},
                ],
            },
            {
                "id": 403,
                "name": "阳台窗帘电机",
                "category": "relay_switch",
                "pid": 4030,
                "roomId": 3,
                "properties": [
                    {"propId": "cp", "value": 40},
                    {"propId": "tp", "value": 90},
                ],
            },
            {
                "id": 404,
                "name": "主卧温湿度传感器",
                "category": "light",
                "pid": 4040,
                "roomId": 4,
                "properties": [
                    {"propId": "t", "value": 24.5},
                    {"propId": "h", "value": 57},
                    {"propId": "bl", "value": 83},
                ],
            },
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
    human_candidates = {
        (item.platform, item.component_id)
        for item in iter_device_entity_candidates(data[402])
    }
    curtain_candidates = {
        item.platform for item in iter_device_entity_candidates(data[403])
    }
    temp_candidates = {
        (item.platform, item.component_id)
        for item in iter_device_entity_candidates(data[404])
    }

    assert data[402]["iot_category"] == "human_sensor"
    assert "type" not in data[402]
    assert data[402]["ha_platform"] == "binary_sensor"
    assert data[402]["ha_platform_candidates"] == [
        "binary_sensor",
        "sensor",
    ]
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


def test_runtime_payloads_keep_safety_sensor_out_of_light_category() -> None:
    """烟感类设备不能因云端粗 light 品类被当成灯具。"""
    builder = DevicePayloadBuilder()

    data, _gateways = builder.build_runtime_payloads(
        devices=[
            {
                "id": 405,
                "name": "厨房烟雾传感器",
                "category": "light",
                "pid": 4050,
                "roomId": 1,
                "properties": [],
            }
        ],
        gateways=[],
        product_schemas={},
        apply_runtime_overrides=lambda payload: payload,
        rooms=[{"id": "1", "name": "厨房"}],
    )

    device = data[405]

    assert device["iot_category"] == "other"
    assert "ha_platform" not in device
    assert device["device_info"]["model"] == "烟雾传感器"
    assert list(iter_device_entity_candidates(device)) == []
