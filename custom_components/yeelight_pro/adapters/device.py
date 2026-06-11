"""Adapters that normalize Yeelight Pro LAN runtime payloads into source contracts."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping

from ..canonical.models import HAProductModel
from .models import (
    SourceDeviceComponentInput,
    SourceDeviceInfoInput,
    SourceDeviceInstanceInput,
)
from ..utils import apply_property_scale, to_bool, to_str
from .device_helpers import (
    fallback_component_key,
    fallback_runtime_state,
    normalize_pair,
    normalize_pair_list,
    prefer_plain_match,
    should_expose_component_state,
    should_expose_runtime_property,
    should_include_runtime_component,
)


class YeelightLanDeviceAdapter:
    """Normalize Yeelight LAN topology and device snapshots into source contracts."""

    def adapt(
        self,
        payload: Mapping[str, Any],
        *,
        product_model: HAProductModel | None = None,
        model_id: str | None = None,
        device_info: Mapping[str, Any] | None = None,
    ) -> SourceDeviceInstanceInput:
        """Adapt a runtime payload into a normalized device-instance contract."""
        device_id = to_str(
            payload.get("device_id", payload.get("deviceId", payload.get("id")))
        )
        if device_id is None:
            device_id = "unknown"
        name = to_str(payload.get("name", payload.get("n")))
        online = to_bool(payload.get("online", payload.get("o")), default=True)
        raw_params = payload.get("params")
        params: Mapping[str, Any] = raw_params if isinstance(raw_params, Mapping) else {}

        resolved_model_id = model_id
        if not resolved_model_id and product_model is not None:
            resolved_model_id = product_model.product.model_id
        if not resolved_model_id and payload.get("model_id") is not None:
            resolved_model_id = to_str(payload.get("model_id"))

        product_key = to_str(
            payload.get("product_key", payload.get("pid", payload.get("product_type")))
        )

        return SourceDeviceInstanceInput(
            source="yeelight",
            device_id=device_id,
            product_key=product_key,
            model_id=resolved_model_id,
            name=name,
            online=online,
            device_info=self._adapt_device_info(device_info, payload, resolved_model_id, name),
            components=self._adapt_components(
                payload,
                params=params,
                online=online,
                product_model=product_model,
            ),
            extensions=self._build_extensions(payload),
        )

    def _adapt_device_info(
        self,
        device_info: Mapping[str, Any] | None,
        payload: Mapping[str, Any],
        model_id: str | None,
        name: str | None,
    ) -> SourceDeviceInfoInput | None:
        """适配设备信息，优先使用显式 device_info，回退到 payload 推断。"""
        if device_info:
            device_info_model_id = to_str(device_info.get("model_id"))
            return SourceDeviceInfoInput(
                identifiers=normalize_pair_list(device_info.get("identifiers")),
                connections=normalize_pair_list(device_info.get("connections")),
                via_device=normalize_pair(device_info.get("via_device")),
                manufacturer=to_str(device_info.get("manufacturer")),
                model=to_str(device_info.get("model")),
                model_id=_public_model_id(device_info_model_id),
                name=to_str(device_info.get("name")) or name,
                serial_number=to_str(device_info.get("serial_number")),
                sw_version=to_str(device_info.get("sw_version")),
                hw_version=to_str(device_info.get("hw_version")),
                configuration_url=to_str(device_info.get("configuration_url")),
                entry_type=to_str(device_info.get("entry_type")),
                suggested_area=to_str(device_info.get("suggested_area")),
                default_manufacturer=to_str(device_info.get("default_manufacturer")),
                default_model=to_str(device_info.get("default_model")),
                default_name=to_str(device_info.get("default_name")),
                translation_key=to_str(device_info.get("translation_key")),
                translation_placeholders=(
                    dict(translation_placeholders)
                    if isinstance(
                        translation_placeholders := device_info.get(
                            "translation_placeholders"
                        ),
                        Mapping,
                    )
                    else None
                ),
            )

        # 从 payload 推断设备信息
        identifiers = []
        device_id = to_str(payload.get("device_id", payload.get("id")))
        if device_id:
            identifiers.append(["yeelight_pro", f"device:{device_id}"])

        mac = to_str(payload.get("mac"))
        connections = [["mac", mac]] if mac else []

        if not identifiers and not connections and not model_id and not name:
            return None

        return SourceDeviceInfoInput(
            identifiers=identifiers,
            connections=connections,
            manufacturer="Yeelight" if model_id else None,
            model_id=_public_model_id(model_id),
            name=name,
        )

    def _adapt_components(
        self,
        payload: Mapping[str, Any],
        *,
        params: Mapping[str, Any],
        online: bool,
        product_model: HAProductModel | None,
    ) -> list[SourceDeviceComponentInput]:
        """适配设备组件列表，有产品模型时精确映射，否则回退。"""
        if product_model is None:
            return [
                SourceDeviceComponentInput(
                    component_key=fallback_component_key(payload),
                    name=to_str(payload.get("componentName", payload.get("component_name"))),
                    desc=to_str(payload.get("desc")),
                    category=to_str(payload.get("category")),
                    available=online,
                    state=fallback_runtime_state(payload, params),
                )
            ]

        state_map: dict[str, dict[str, Any]] = {
            component.component_id: {} for component in product_model.components
        }
        indexed_lookup: dict[str, tuple[str, str]] = {}
        plain_lookup: dict[str, list[str]] = defaultdict(list)

        component_by_id = {component.component_id: component for component in product_model.components}
        property_by_component: dict[str, dict[str, Any]] = {
            component.component_id: {
                prop.prop_id: prop for prop in component.properties
            }
            for component in product_model.components
        }
        for component in product_model.components:
            if not should_expose_component_state(component):
                continue
            for prop in component.properties:
                if not should_expose_runtime_property(component, prop):
                    continue
                plain_lookup[prop.prop_id].append(component.component_id)
                if component.index is not None:
                    indexed_lookup[f"{component.index}-{prop.prop_id}"] = (
                        component.component_id,
                        prop.prop_id,
                    )

        # 将运行时 params 映射到组件 state
        for raw_key, value in params.items():
            if raw_key in indexed_lookup:
                component_id, prop_id = indexed_lookup[raw_key]
                property_model = property_by_component.get(component_id, {}).get(prop_id)
                state_map[component_id][prop_id] = scaled_runtime_value(
                    value, property_model
                )
                continue

            candidates = plain_lookup.get(raw_key, [])
            if len(candidates) == 1:
                component_id = candidates[0]
                property_model = property_by_component.get(component_id, {}).get(raw_key)
                state_map[component_id][raw_key] = scaled_runtime_value(
                    value, property_model
                )
                continue

            if len(candidates) > 1:
                preferred = prefer_plain_match(candidates, component_by_id, raw_key)
                if preferred:
                    property_model = property_by_component.get(preferred, {}).get(
                        raw_key
                    )
                    state_map[preferred][raw_key] = scaled_runtime_value(
                        value, property_model
                    )

        components: list[SourceDeviceComponentInput] = []
        for component in product_model.components:
            if not should_expose_component_state(component):
                continue
            component_state = state_map.get(component.component_id, {})
            if not should_include_runtime_component(component, component_state):
                continue
            components.append(
                SourceDeviceComponentInput(
                    component_key=component.component_id,
                    name=component.name,
                    desc=component.desc,
                    index=component.index,
                    component_type=component.component_type,
                    category=component.category,
                    available=online,
                    state=component_state,
                )
            )

        return components

    def _build_extensions(
        self,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        """构建设备扩展元数据（当前为空，预留扩展点）。"""
        return {}


def scaled_runtime_value(value: Any, prop: Any | None) -> Any:
    """按产品模型属性缩放规则转换运行时读值。"""
    if prop is None:
        return value
    return apply_property_scale(
        value,
        zoom=getattr(prop, "zoom", 1),
        scale=getattr(prop, "scale", 1),
    )


def _public_model_id(value: str | None) -> str | None:
    """Hide internal runtime-* model ids from HA device registry metadata."""
    if value is None or value.startswith("runtime-"):
        return None
    return value
