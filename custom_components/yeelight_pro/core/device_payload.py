"""Normalize Yeelight Pro device payloads for Home Assistant projectors."""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from typing import Any

from ..capabilities.mapping import platform_for_category
from ..converter.device import YeelightLanDeviceInstanceConverter
from ..converter.product import YeelightProductSchemaConverter
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
    ) -> None:
        self._product_schema_converter = (
            product_schema_converter or YeelightProductSchemaConverter()
        )
        self._device_instance_converter = (
            device_instance_converter or YeelightLanDeviceInstanceConverter()
        )

    def normalize(
        self,
        device: Mapping[str, Any],
        product_schemas: Mapping[int, Mapping[str, Any]],
    ) -> dict[str, Any]:
        """将 open API 格式转换为 projector 期望的格式."""
        normalized = dict(device)

        if "category" in normalized and "type" not in normalized:
            category = normalized["category"]
            normalized["type"] = platform_for_category(category, default=category)

        if "id" in normalized and "device_id" not in normalized:
            normalized["device_id"] = normalized["id"]

        online = to_bool(normalized.get("online"), default=True)

        if "properties" in normalized:
            params: dict[str, Any] | None = (
                {} if "params" not in normalized else None
            )
            for prop in normalized.get("properties", []):
                if not isinstance(prop, Mapping):
                    continue
                prop_id = prop.get("propId")
                value = prop.get("value")
                if prop_id == "o":
                    online = to_bool(value, default=online)
                elif params is not None and prop_id and value is not None:
                    params[str(prop_id)] = value
            if params is not None:
                normalized["params"] = params
        normalized["online"] = online

        pid = to_int(normalized.get("pid"))
        if pid is not None:
            normalized["pid"] = pid
            product_schema = product_schemas.get(pid)
            if product_schema is not None:
                normalized["product_schema"] = dict(product_schema)

        return normalized

    def build_runtime_payloads(
        self,
        *,
        devices: list[dict[str, Any]],
        gateways: list[dict[str, Any]],
        product_schemas: Mapping[int, Mapping[str, Any]],
        apply_runtime_overrides: RuntimeOverrideApplier,
    ) -> tuple[dict[int, dict[str, Any]], dict[int, dict[str, Any]]]:
        """Build coordinator device and gateway maps from Open API rows."""
        data: dict[int, dict[str, Any]] = {}
        for device in devices:
            device_id = device.get("id")
            if device_id:
                normalized = self.normalize(device, product_schemas)
                normalized = apply_runtime_overrides(normalized)
                self.attach_canonical_models_if_available(normalized)
                data[device_id] = normalized

        gateway_data: dict[int, dict[str, Any]] = {}
        for gateway in gateways:
            gateway_id = gateway.get("id")
            if gateway_id:
                normalized = self.normalize(gateway, product_schemas)
                self.attach_canonical_models_if_available(normalized)
                gateway_data[gateway_id] = normalized
                data[gateway_id] = normalized

        return data, gateway_data

    def attach_canonical_models_if_available(self, payload: dict[str, Any]) -> None:
        """在载荷包含产品 schema 时生成规范产品与运行时实例."""
        product_schema = payload.get("product_schema")
        if isinstance(product_schema, Mapping):
            self.attach_canonical_models(payload, product_schema)

    def attach_canonical_models(
        self,
        payload: dict[str, Any],
        product_schema: Mapping[str, Any],
    ) -> None:
        """把官方产品 schema 转换成 projector 可消费的规范模型."""
        try:
            product_model = self._product_schema_converter.convert(product_schema)
            payload["ha_product_model"] = product_model.to_dict()
            payload["model_id"] = product_model.product.model_id
            payload["ha_device_instance"] = self._device_instance_converter.convert(
                payload,
                product_model=product_model,
                model_id=product_model.product.model_id,
            ).to_dict()
        except Exception as err:
            _LOGGER.warning(
                "Failed to build Yeelight Pro canonical model: %s",
                safe_error_summary(err),
            )
