"""Device payload builder tests."""

from __future__ import annotations

import logging
from typing import Any, Mapping

from custom_components.yeelight_pro.core.device_payload import DevicePayloadBuilder


class _FakeProduct:
    def __init__(self) -> None:
        self.model_id = "model-100"


class _FakeProductModel:
    def __init__(self) -> None:
        self.product = _FakeProduct()

    def to_dict(self) -> dict[str, Any]:
        return {"product": {"model_id": self.product.model_id}}


class _FakeDeviceInstance:
    def to_dict(self) -> dict[str, Any]:
        return {"device_id": 1, "components": []}


class _ProductSchemaConverter:
    def __init__(self, *, raises: bool = False) -> None:
        self.raises = raises
        self.schemas: list[Mapping[str, Any]] = []

    def convert(self, schema: Mapping[str, Any]) -> _FakeProductModel:
        self.schemas.append(schema)
        if self.raises:
            raise ValueError(
                "bad schema token=secret-token "
                "https://api.yeelight.com/apis/iot/house/12345 device_id=67890"
            )
        return _FakeProductModel()


class _DeviceInstanceConverter:
    def __init__(self) -> None:
        self.payloads: list[Mapping[str, Any]] = []
        self.model_ids: list[str | None] = []

    def convert(
        self,
        payload: Mapping[str, Any],
        *,
        product_model: Any | None = None,
        model_id: str | None = None,
    ) -> _FakeDeviceInstance:
        self.payloads.append(payload)
        self.model_ids.append(model_id)
        return _FakeDeviceInstance()


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
    assert normalized["type"] == "light"
    assert normalized["online"] is False
    assert normalized["params"] == {"p": True, "l": 80}


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
    assert payload["ha_device_instance"] == {"device_id": 1, "components": []}
    assert product_converter.schemas == [{"pid": 100}]
    assert device_converter.payloads == [payload]
    assert device_converter.model_ids == ["model-100"]


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
