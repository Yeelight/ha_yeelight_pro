"""Normalize Yeelight Pro device payloads for Home Assistant projectors."""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from typing import Any

from ..converter.device import YeelightLanDeviceInstanceConverter
from ..converter.product import (
    RuntimeInferredProductModelBuilder,
    YeelightProductSchemaConverter,
)
from ..capabilities.platform_contract import (
    platform_candidates_for_payload,
    primary_platform_for_payload,
)
from ..capabilities.registry import format_component_property_key
from .device_classification import infer_iot_category
from .device_runtime_capabilities import schema_conflicts_with_runtime_category
from .device_metadata import attach_fallback_payload_metadata, enrich_payload_metadata
from .exceptions import safe_error_summary
from ..utils import to_bool, to_int

_LOGGER = logging.getLogger(__name__)
RuntimeOverrideApplier = Callable[[dict[str, Any]], dict[str, Any]]


class DevicePayloadBuilder:
    """Build projector-ready device payloads from Open API rows."""

    def __init__(
        self,
        *,
        product_schema_converter: YeelightProductSchemaConverter | None = None,
        device_instance_converter: YeelightLanDeviceInstanceConverter | None = None,
        runtime_product_builder: RuntimeInferredProductModelBuilder | None = None,
    ) -> None:
        self._product_schema_converter = (
            product_schema_converter or YeelightProductSchemaConverter()
        )
        self._device_instance_converter = (
            device_instance_converter or YeelightLanDeviceInstanceConverter()
        )
        self._runtime_product_builder = (
            runtime_product_builder or RuntimeInferredProductModelBuilder()
        )

    def normalize(
        self,
        device: Mapping[str, Any],
        product_schemas: Mapping[int, Mapping[str, Any]],
    ) -> dict[str, Any]:
        """将 open API 格式转换为 projector 期望的格式."""
        normalized = dict(device)

        if "id" in normalized and "device_id" not in normalized:
            normalized["device_id"] = normalized["id"]

        online = to_bool(normalized.get("online"), default=True)

        params = _params(normalized)
        has_property_source = "properties" in normalized or bool(
            _subdevices(normalized.get("subDeviceList"))
        )

        for prop in _properties(normalized.get("properties")):
            prop_id = _property_id(prop)
            value = _property_value(prop)
            if prop_id == "o":
                online = to_bool(value, default=online)
            elif prop_id and value is not None:
                params[str(prop_id)] = value

        for subdevice in _subdevices(normalized.get("subDeviceList")):
            index = to_int(subdevice.get("index"))
            for prop in _properties(subdevice.get("properties")):
                prop_id = _property_id(prop)
                value = _property_value(prop)
                if prop_id and value is not None:
                    params[format_component_property_key(index, prop_id)] = value

        if params or has_property_source:
            normalized["params"] = params
        normalized["online"] = online

        pid = to_int(normalized.get("pid"))
        if pid is not None:
            normalized["pid"] = pid
            product_schema = product_schemas.get(pid)
            if product_schema is not None:
                normalized["product_schema"] = dict(product_schema)

        iot_category = infer_iot_category(normalized)
        if iot_category is not None:
            normalized["iot_category"] = iot_category
            normalized["category"] = iot_category

        candidates = platform_candidates_for_payload(normalized)
        if candidates:
            normalized["ha_platform_candidates"] = list(candidates)
        platform = primary_platform_for_payload(normalized)
        if platform is not None:
            normalized["ha_platform"] = platform

        return normalized

    def build_runtime_payloads(
        self,
        *,
        devices: list[dict[str, Any]],
        gateways: list[dict[str, Any]],
        product_schemas: Mapping[int, Mapping[str, Any]],
        apply_runtime_overrides: RuntimeOverrideApplier,
        rooms: list[dict[str, Any]] | None = None,
        areas: list[dict[str, Any]] | None = None,
    ) -> tuple[dict[int, dict[str, Any]], dict[int, dict[str, Any]]]:
        """Build coordinator device and gateway maps from Open API rows."""
        data: dict[int, dict[str, Any]] = {}
        for device in devices:
            device_id = to_int(device.get("id"))
            if device_id:
                normalized = self.normalize(device, product_schemas)
                normalized["id"] = device_id
                normalized["device_id"] = device_id
                normalized = apply_runtime_overrides(normalized)
                self.attach_canonical_models_if_available(
                    normalized,
                    rooms=rooms,
                    areas=areas,
                )
                _attach_platform_metadata(normalized)
                data[device_id] = normalized

        gateway_data: dict[int, dict[str, Any]] = {}
        for gateway in gateways:
            gateway_id = to_int(gateway.get("id"))
            if gateway_id:
                normalized = self.normalize(gateway, product_schemas)
                normalized["id"] = gateway_id
                normalized["device_id"] = gateway_id
                normalized["is_gateway"] = True
                self.attach_canonical_models_if_available(
                    normalized,
                    rooms=rooms,
                    areas=areas,
                )
                _attach_platform_metadata(normalized)
                gateway_data[gateway_id] = normalized
                data[gateway_id] = normalized

        return data, gateway_data

    def attach_canonical_models_if_available(
        self,
        payload: dict[str, Any],
        *,
        rooms: list[dict[str, Any]] | None = None,
        areas: list[dict[str, Any]] | None = None,
    ) -> None:
        """在载荷包含产品 schema 时生成规范产品与运行时实例."""
        product_schema = payload.get("product_schema")
        if isinstance(product_schema, Mapping):
            if self._schema_conflicts_with_runtime_category(payload, product_schema):
                self.attach_inferred_canonical_models(payload, rooms=rooms, areas=areas)
                return
            self.attach_canonical_models(
                payload,
                product_schema,
                rooms=rooms,
                areas=areas,
            )
            return
        self.attach_inferred_canonical_models(payload, rooms=rooms, areas=areas)
        if "device_info" not in payload:
            attach_fallback_payload_metadata(payload, rooms=rooms, areas=areas)

    def attach_canonical_models(
        self,
        payload: dict[str, Any],
        product_schema: Mapping[str, Any],
        *,
        rooms: list[dict[str, Any]] | None = None,
        areas: list[dict[str, Any]] | None = None,
    ) -> None:
        """把官方产品 schema 转换成 projector 可消费的规范模型."""
        try:
            product_model = self._product_schema_converter.convert(product_schema)
            device_info = enrich_payload_metadata(
                payload,
                product_model=product_model,
                rooms=rooms,
                areas=areas,
            )
            payload["ha_product_model"] = product_model.to_dict()
            payload["model_id"] = product_model.product.model_id
            payload["ha_device_instance"] = self._device_instance_converter.convert(
                payload,
                product_model=product_model,
                model_id=product_model.product.model_id,
                device_info=device_info,
            ).to_dict()
        except Exception as err:
            _LOGGER.warning(
                "Failed to build Yeelight Pro canonical model: %s",
                safe_error_summary(err),
            )

    def attach_inferred_canonical_models(
        self,
        payload: dict[str, Any],
        *,
        rooms: list[dict[str, Any]] | None = None,
        areas: list[dict[str, Any]] | None = None,
    ) -> None:
        """缺少官方 schema 时用保守运行时模型补齐 HA 设备实例."""
        try:
            product_model = self._runtime_product_builder.build(payload)
            if product_model is None:
                attach_fallback_payload_metadata(payload, rooms=rooms, areas=areas)
                return
            device_info = enrich_payload_metadata(
                payload,
                product_model=product_model,
                rooms=rooms,
                areas=areas,
            )
            payload["ha_product_model"] = product_model.to_dict()
            payload["model_id"] = product_model.product.model_id
            payload["ha_device_instance"] = self._device_instance_converter.convert(
                payload,
                product_model=product_model,
                model_id=product_model.product.model_id,
                device_info=device_info,
            ).to_dict()
        except Exception as err:
            _LOGGER.warning(
                "Failed to build Yeelight Pro inferred runtime model: %s",
                safe_error_summary(err),
            )

    def _schema_conflicts_with_runtime_category(
        self,
        payload: Mapping[str, Any],
        product_schema: Mapping[str, Any],
    ) -> bool:
        """Return true when broad schema would hide a stricter runtime category."""
        category = str(
            payload.get("iot_specific_category")
            or payload.get("iot_category")
            or payload.get("category")
            or ""
        )
        return schema_conflicts_with_runtime_category(
            payload,
            product_schema,
            runtime_category=category or None,
        )


def _property_id(prop: Mapping[str, Any]) -> Any:
    """Return the Yeelight property id from list/read response variants."""
    return prop.get("propId", prop.get("propName"))


def _property_value(prop: Mapping[str, Any]) -> Any:
    """Return the Yeelight property value from list/read response variants."""
    if "value" in prop:
        return prop.get("value")
    return prop.get("data")


def _params(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a mutable runtime params copy."""
    raw_params = payload.get("params")
    return dict(raw_params) if isinstance(raw_params, Mapping) else {}


def _properties(value: Any) -> list[Mapping[str, Any]]:
    """Return property mappings from Open API response variants."""
    return [item for item in value or [] if isinstance(item, Mapping)]


def _subdevices(value: Any) -> list[Mapping[str, Any]]:
    """Return sub-device mappings from Open API device-list rows."""
    return [item for item in value or [] if isinstance(item, Mapping)]


def _attach_platform_metadata(payload: dict[str, Any]) -> None:
    """Refresh HA platform hints after runtime schema inference."""
    candidates = platform_candidates_for_payload(payload)
    if candidates:
        payload["ha_platform_candidates"] = list(candidates)
    else:
        payload.pop("ha_platform_candidates", None)
    platform = primary_platform_for_payload(payload)
    if platform is not None:
        payload["ha_platform"] = platform
    else:
        payload.pop("ha_platform", None)
