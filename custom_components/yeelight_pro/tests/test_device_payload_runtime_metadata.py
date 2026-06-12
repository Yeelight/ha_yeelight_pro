"""Runtime device payload metadata tests."""

from __future__ import annotations

from custom_components.yeelight_pro.core.device_payload import DevicePayloadBuilder
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


def test_build_runtime_payloads_uses_model_name_without_raw_id_fallback() -> None:
    """缺少用户设备名时，HA 设备名不应退化成 Yeelight Pro 429392 一类占位名."""
    builder = DevicePayloadBuilder()

    data, _gateways = builder.build_runtime_payloads(
        devices=[
            {
                "id": 429392,
                "category": "light",
                "pid": 100,
                "roomId": 12,
                "properties": [
                    {"propId": "p", "value": True},
                    {"propId": "l", "value": 75},
                    {"propId": "ct", "value": 4000},
                ],
            }
        ],
        gateways=[],
        product_schemas={},
        apply_runtime_overrides=lambda payload: payload,
        rooms=[{"id": "12", "name": "入户门"}],
    )

    device_info = data[429392]["ha_device_instance"]["device_info"]
    assert device_info["name"] == "色温灯"
    assert "429392" not in device_info["name"]
    assert device_info["model"] == "色温灯"
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
    assert device_info["model"] == "亮度灯"
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
    """云端粗 model 不应短路能力证据或安全大类兜底。"""
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
    assert light_info["model"] == "色温灯"
    assert light_info["model_id"] == "YL-202"
    assert switch_info["model"] == "继电器开关"
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
    assert device_info["model"] == "亮度灯"
    assert "model_id" not in device_info

