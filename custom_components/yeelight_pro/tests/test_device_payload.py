"""Device payload builder tests."""

from __future__ import annotations

import logging
from typing import Any, Mapping, cast

from custom_components.yeelight_pro.core.device_payload import DevicePayloadBuilder
from .device_payload_helpers import (
    _DeviceInstanceConverter,
    _ProductSchemaConverter,
)


def test_normalize_maps_open_api_properties_to_params_and_online() -> None:
    """Open API properties 应转换为 projector 消费的 params/online."""
    builder = DevicePayloadBuilder()

    normalized = builder.normalize(
        {
            "id": 1,
            "category": "light",
            "properties": [
                {"propId": "o", "value": False},
                {"propId": "p", "value": True},
                {"propId": "l", "value": 80},
                {"propId": "ct", "value": None},
                {"propId": "", "value": 1},
                "invalid",
            ],
        },
        {},
    )

    assert normalized["device_id"] == 1
    assert "type" not in normalized
    assert normalized["iot_category"] == "light"
    assert normalized["effective_category"] == "light"
    assert normalized["category"] == "light"
    assert normalized["source_category"] == "light"
    assert normalized["original_category"] == "light"
    assert normalized["ha_platform"] == "light"
    assert normalized["ha_platform_candidates"] == ["light", "sensor"]
    assert normalized["online"] is False
    assert normalized["params"] == {"p": True, "l": 80}


def test_normalize_accepts_read_property_response_shape() -> None:
    """属性读取返回的 propName/data 形态也应进入 projector params."""
    builder = DevicePayloadBuilder()

    normalized = builder.normalize(
        {
            "id": 2,
            "name": "客厅射灯",
            "category": "light",
            "properties": [
                {"propName": "p", "data": True},
                {"propName": "l", "data": 65},
                {"propName": "ct", "data": 4000},
            ],
        },
        {},
    )

    assert normalized["params"] == {"p": True, "l": 65, "ct": 4000}
    assert "type" not in normalized
    assert normalized["iot_category"] == "light"
    assert normalized["ha_platform"] == "light"
    assert normalized["ha_platform_candidates"] == ["light"]


def test_normalize_preserves_openapi_category_when_capabilities_override_it() -> None:
    """OpenAPI 原始 category 是事实源，能力推断写入独立有效品类字段."""
    builder = DevicePayloadBuilder()

    normalized = builder.normalize(
        {
            "id": 3,
            "name": "厨房烟雾传感器",
            "category": "light",
            "properties": [
                {"propId": "dc", "value": False},
                {"propId": "alm", "value": True},
                {"propId": "bl", "value": 91},
            ],
        },
        {},
    )

    assert normalized["category"] == "light"
    assert normalized["source_category"] == "light"
    assert normalized["original_category"] == "light"
    assert normalized["iot_category"] == "contact_sensor"
    assert normalized["effective_category"] == "contact_sensor"
    assert normalized["ha_platform"] == "binary_sensor"
    assert normalized["ha_platform_candidates"] == ["binary_sensor", "sensor"]


def test_normalize_parses_string_online_property_values() -> None:
    """在线属性 o 应按 Yeelight 布尔语义解析字符串值."""
    builder = DevicePayloadBuilder()

    for value in ("false", "0"):
        normalized = builder.normalize(
            {
                "id": value,
                "category": "light",
                "properties": [{"propId": "o", "value": value}],
            },
            {},
        )

        assert normalized["online"] is False


def test_normalize_parses_top_level_string_online_value() -> None:
    """top-level online 应复用 Yeelight 布尔语义."""
    builder = DevicePayloadBuilder()

    normalized = builder.normalize(
        {"id": 1, "category": "light", "online": "false"},
        {},
    )

    assert normalized["online"] is False


def test_normalize_preserves_top_level_offline_without_online_property() -> None:
    """properties 缺少 o 时不应把 top-level offline 覆盖为在线."""
    builder = DevicePayloadBuilder()

    normalized = builder.normalize(
        {
            "id": 1,
            "category": "light",
            "online": False,
            "properties": [{"propId": "p", "value": True}],
        },
        {},
    )

    assert normalized["online"] is False
    assert normalized["params"] == {"p": True}


def test_normalize_coerces_pid_and_attaches_product_schema_copy() -> None:
    """pid 应归一为 int，并以副本形式附加产品 schema."""
    schema = {"pid": 100, "name": "Lamp"}
    builder = DevicePayloadBuilder()

    normalized = builder.normalize(
        {"id": 1, "pid": "100", "category": "light"},
        {100: schema},
    )

    assert normalized["pid"] == 100
    assert normalized["product_schema"] == schema
    assert normalized["product_schema"] is not schema
    assert normalized["online"] is True


def test_build_runtime_payloads_applies_overrides_only_to_devices() -> None:
    """运行时覆盖只应用到普通设备，网关按 schema 原样归一化."""
    builder = DevicePayloadBuilder()
    overridden: list[int] = []

    def _apply_runtime_overrides(payload: dict[str, Any]) -> dict[str, Any]:
        overridden.append(payload["id"])
        payload["params"] = {"p": False}
        return payload

    data, gateways = builder.build_runtime_payloads(
        devices=[{"id": 1, "category": "light", "params": {"p": True}}],
        gateways=[{"id": 2, "category": "gateway", "params": {"o": True}}],
        product_schemas={},
        apply_runtime_overrides=_apply_runtime_overrides,
    )

    assert overridden == [1]
    assert data[1]["params"] == {"p": False}
    assert data[2] is gateways[2]
    assert gateways[2]["params"] == {"o": True}


def test_attach_canonical_models_uses_converters() -> None:
    """有产品 schema 时应附加规范产品和运行时实例."""
    product_converter = _ProductSchemaConverter()
    device_converter = _DeviceInstanceConverter()
    builder = DevicePayloadBuilder(
        product_schema_converter=product_converter,  # type: ignore[arg-type]
        device_instance_converter=device_converter,  # type: ignore[arg-type]
    )
    payload = {"id": 1, "device_id": 1, "product_schema": {"pid": 100}}

    builder.attach_canonical_models_if_available(payload)

    assert payload["ha_product_model"] == {"product": {"model_id": "model-100"}}
    assert payload["model_id"] == "model-100"
    assert payload["ha_device_instance"] == {
        "device_id": 1,
        "components": [],
        "device_info": payload["device_info"],
    }
    device_info = cast(Mapping[str, Any], payload["device_info"])
    assert device_info["name"] == "Fake Product 1"
    assert device_info["model"] == "Fake Product"
    assert device_info["model_id"] == "model-100"
    assert device_info["identifiers"] == [
        ["yeelight_pro", "1"],
        ["yeelight_pro", "device:1"],
    ]
    assert product_converter.schemas == [{"pid": 100}]
    assert device_converter.payloads == [payload]
    assert device_converter.model_ids == ["model-100"]
    assert device_converter.device_infos == [device_info]


def test_attach_canonical_models_logs_and_keeps_payload_on_converter_error(
    caplog,
) -> None:
    """schema 转换失败不能阻断 payload 归一化链路."""
    builder = DevicePayloadBuilder(
        product_schema_converter=_ProductSchemaConverter(raises=True),  # type: ignore[arg-type]
        device_instance_converter=_DeviceInstanceConverter(),  # type: ignore[arg-type]
    )
    payload = {"id": 1, "device_id": 1, "product_schema": {"pid": 100}}

    with caplog.at_level(logging.WARNING):
        builder.attach_canonical_models_if_available(payload)

    assert "ha_product_model" not in payload
    assert "ha_device_instance" not in payload
    assert "model_id" not in payload
    assert "Failed to build Yeelight Pro canonical model: ValueError" in caplog.text
    assert "secret-token" not in caplog.text
    assert "api.yeelight.com" not in caplog.text
    assert "12345" not in caplog.text
    assert "67890" not in caplog.text
