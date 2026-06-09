"""Adapters that normalize Yeelight product schemas into source contracts."""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from ..capabilities.spec_correction import (
    correct_property_schema,
    derive_component_capabilities,
    normalize_component_type,
    normalize_property_format,
    normalize_property_operators,
    normalize_source_property_type,
)
from .models import (
    SourceActionInput,
    SourceActionParamInput,
    SourceBridgeInput,
    SourceComponentInput,
    SourceEventInput,
    SourceProductSchemaInput,
    SourcePropertyInput,
)
from .product_helpers import (
    adapt_value_list,
    adapt_value_range,
    build_component_key,
    build_model_id,
    collect_categories,
    component_base_name,
    merge_components,
    normalize_protocol,
    normalized_scale,
    normalized_unit,
    normalized_zoom,
    string,
)


class YeelightProductSchemaAdapter:
    """将 ProductSchemaDtoV2 类载荷标准化为适配器层源侧契约。"""

    def __init__(self, manufacturer: str = "Yeelight") -> None:
        self._manufacturer = manufacturer

    def adapt(self, schema: Mapping[str, Any]) -> SourceProductSchemaInput:
        """适配 ProductSchemaDtoV2 类映射至源侧产品模型输入。"""
        components = self._adapt_components(
            schema.get("components"),
            schema.get("customComponents"),
        )
        return SourceProductSchemaInput(
            source="yeelight",
            product_key=str(schema.get("pid")) if schema.get("pid") is not None else "",
            model_id=build_model_id(schema.get("pid")),
            manufacturer=self._manufacturer,
            name=string(schema.get("name")),
            description=string(schema.get("desc")),
            category=string(schema.get("category")),
            categories=collect_categories(components),
            bridge=self._adapt_bridge(schema),
            components=components,
            device_actions=self._adapt_device_actions(
                schema.get("supportActions"), components
            ),
            metadata={
                "pid": schema.get("pid"),
                "pcId": schema.get("pcId"),
                "connectType": schema.get("connectType"),
                "supportedBridge": schema.get("supportedBridge"),
            },
        )

    def _adapt_bridge(self, schema: Mapping[str, Any]) -> SourceBridgeInput | None:
        """适配桥接协议元数据。"""
        supported_types = schema.get("supportedBridgeType")
        if not schema.get("supportedBridge") and not supported_types:
            return None

        protocols: list[str] = []
        for item in supported_types or []:
            if not isinstance(item, Mapping):
                continue
            protocol = normalize_protocol(item.get("desc"))
            if protocol and protocol not in protocols:
                protocols.append(protocol)

        return SourceBridgeInput(protocols=protocols)

    def _adapt_components(
        self,
        raw_components: Any,
        raw_custom_components: Any = None,
    ) -> list[SourceComponentInput]:
        """适配组件列表，合并标准组件与自定义组件。"""
        components = merge_components(raw_components, raw_custom_components)
        base_counts = Counter(component_base_name(component) for component in components)
        seen_counts: Counter[str] = Counter()

        normalized_components: list[SourceComponentInput] = []
        for component in components:
            base_name = component_base_name(component)
            seen_counts[base_name] += 1
            component_key = build_component_key(
                component,
                base_name=base_name,
                duplicate_count=base_counts[base_name],
                occurrence=seen_counts[base_name],
            )
            normalized_components.append(
                SourceComponentInput(
                    component_key=component_key,
                    name=string(component.get("name")),
                    desc=string(component.get("desc")),
                    component_type=normalize_component_type(component.get("type")),
                    category=string(component.get("category")),
                    capabilities=derive_component_capabilities(component),
                    properties=self._adapt_properties(
                        component.get("properties"),
                        component=component,
                    ),
                    events=self._adapt_events(component.get("events")),
                    actions=self._adapt_actions(
                        component.get("supportActions"),
                        scope="component",
                        targets=[component_key],
                    ),
                    cid=component.get("cid"),
                    index=component.get("index"),
                    metadata={
                        "originCid": component.get("originCid"),
                        "mockAbilities": component.get("mockAbilities") or [],
                    },
                )
            )

        return normalized_components

    def _adapt_properties(
        self,
        raw_properties: Any,
        *,
        component: Mapping[str, Any] | None = None,
    ) -> list[SourcePropertyInput]:
        """适配属性定义列表。"""
        properties: list[SourcePropertyInput] = []
        for payload in raw_properties or []:
            if not isinstance(payload, Mapping):
                continue
            prop_key = string(payload.get("propId"))
            if prop_key is None:
                continue
            correction = correct_property_schema(
                component,
                payload,
                property_type=normalize_source_property_type(payload.get("type")),
            )
            properties.append(
                SourcePropertyInput(
                    property_key=prop_key,
                    name=string(payload.get("desc")) or prop_key,
                    desc=string(payload.get("desc")),
                    kind=correction.kind,
                    property_type=correction.property_type,
                    format=correction.format,
                    unit=normalized_unit(payload.get("unit")),
                    access=correction.access,
                    default=payload.get("value"),
                    value_range=adapt_value_range(payload.get("valueRange")),
                    value_list=adapt_value_list(payload.get("valueList")),
                    metadata={
                        "id": payload.get("id"),
                        "zoom": normalized_zoom(payload.get("zoom")),
                        "scale": normalized_scale(payload.get("scale")),
                        "operators": normalize_property_operators(
                            payload.get("operators")
                        ),
                        "supportedConnectType": payload.get("supportedConnectType"),
                        "runtime_filtered": correction.runtime_filtered,
                    },
                )
            )
        return properties

    def _adapt_events(self, raw_events: Any) -> list[SourceEventInput]:
        """适配事件定义列表。"""
        events: list[SourceEventInput] = []
        for payload in raw_events or []:
            if not isinstance(payload, Mapping):
                continue
            event_key = (
                str(payload.get("eventId"))
                if payload.get("eventId") is not None
                else string(payload.get("name")) or "event"
            )
            events.append(
                SourceEventInput(
                    event_key=event_key,
                    name=string(payload.get("name")),
                    desc=string(payload.get("desc")),
                    params=self._adapt_properties(payload.get("params")),
                    metadata={"eventTypeId": payload.get("eventTypeId")},
                )
            )
        return events

    def _adapt_actions(
        self, raw_actions: Any, scope: str, targets: list[str]
    ) -> list[SourceActionInput]:
        """适配动作定义列表。"""
        actions: list[SourceActionInput] = []
        for payload in raw_actions or []:
            if not isinstance(payload, Mapping):
                continue
            action_key = string(payload.get("actionName"))
            if action_key is None:
                continue
            actions.append(
                SourceActionInput(
                    action_key=action_key,
                    name=action_key,
                    desc=action_key,
                    scope=scope,
                    targets=list(targets),
                    params=self._adapt_action_params(payload.get("params")),
                )
            )
        return actions

    def _adapt_action_params(self, raw_params: Any) -> list[SourceActionParamInput]:
        """适配动作参数定义列表。"""
        params: list[SourceActionParamInput] = []
        for payload in raw_params or []:
            if not isinstance(payload, Mapping):
                continue
            param_key = string(payload.get("propId"))
            if param_key is None:
                continue
            params.append(
                SourceActionParamInput(
                    param_key=param_key,
                    name=string(payload.get("desc")) or param_key,
                    desc=string(payload.get("desc")),
                    format=normalize_property_format(payload.get("format")),
                    unit=normalized_unit(payload.get("unit")),
                    default=payload.get("value"),
                    value_range=adapt_value_range(payload.get("valueRange")),
                    value_list=adapt_value_list(payload.get("valueList")),
                    metadata={
                        "id": payload.get("id"),
                        "zoom": normalized_zoom(payload.get("zoom")),
                        "scale": normalized_scale(payload.get("scale")),
                        "operators": normalize_property_operators(
                            payload.get("operators")
                        ),
                    },
                )
            )
        return params

    def _adapt_device_actions(
        self, raw_actions: Any, components: list[SourceComponentInput]
    ) -> list[SourceActionInput]:
        """适配设备级动作，目标为所有非全局组件。"""
        targets = [
            component.component_key
            for component in components
            if component.component_type != "global"
        ]
        return self._adapt_actions(raw_actions, scope="device", targets=targets)
