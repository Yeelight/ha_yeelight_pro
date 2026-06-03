"""Adapters that normalize Yeelight product schemas into source contracts."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Mapping

from .models import (
    SourceActionInput,
    SourceActionParamInput,
    SourceBridgeInput,
    SourceComponentInput,
    SourceEventInput,
    SourceProductSchemaInput,
    SourcePropertyInput,
    SourceValueItemInput,
    SourceValueRangeInput,
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
            model_id=self._build_model_id(schema.get("pid")),
            manufacturer=self._manufacturer,
            name=self._string(schema.get("name")),
            description=self._string(schema.get("desc")),
            category=self._string(schema.get("category")),
            categories=self._collect_categories(components),
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
            protocol = self._normalize_protocol(item.get("desc"))
            if protocol and protocol not in protocols:
                protocols.append(protocol)

        return SourceBridgeInput(protocols=protocols)

    def _adapt_components(
        self,
        raw_components: Any,
        raw_custom_components: Any = None,
    ) -> list[SourceComponentInput]:
        """适配组件列表，合并标准组件与自定义组件。"""
        components = self._merge_components(raw_components, raw_custom_components)
        base_counts = Counter(self._component_base_name(component) for component in components)
        seen_counts: Counter[str] = Counter()

        normalized_components: list[SourceComponentInput] = []
        for component in components:
            base_name = self._component_base_name(component)
            seen_counts[base_name] += 1
            component_key = self._build_component_key(
                component,
                base_name=base_name,
                duplicate_count=base_counts[base_name],
                occurrence=seen_counts[base_name],
            )
            normalized_components.append(
                SourceComponentInput(
                    component_key=component_key,
                    name=self._string(component.get("name")),
                    desc=self._string(component.get("desc")),
                    component_type=self._component_type(component.get("type")),
                    category=self._string(component.get("category")),
                    capabilities=self._derive_component_capabilities(component),
                    properties=self._adapt_properties(component.get("properties")),
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

    def _merge_components(self, *sources: Any) -> list[Mapping[str, Any]]:
        """合并多个组件来源并按身份去重。"""
        merged: list[Mapping[str, Any]] = []
        seen: set[tuple[Any, ...]] = set()

        for source in sources:
            for item in source or []:
                if not isinstance(item, Mapping):
                    continue
                identity = (
                    item.get("cid"),
                    item.get("index"),
                    item.get("type"),
                    self._string(item.get("category")),
                    self._string(item.get("name")),
                )
                if identity in seen:
                    continue
                seen.add(identity)
                merged.append(item)

        return merged

    def _adapt_properties(self, raw_properties: Any) -> list[SourcePropertyInput]:
        """适配属性定义列表。"""
        properties: list[SourcePropertyInput] = []
        for payload in raw_properties or []:
            if not isinstance(payload, Mapping):
                continue
            prop_key = self._string(payload.get("propId"))
            properties.append(
                SourcePropertyInput(
                    property_key=prop_key,
                    name=self._string(payload.get("desc")) or prop_key,
                    desc=self._string(payload.get("desc")),
                    kind=self._property_kind(payload),
                    property_type=self._property_type(payload.get("type")),
                    format=self._string(payload.get("format")),
                    unit=self._normalized_unit(payload.get("unit")),
                    access=self._property_access(payload),
                    default=payload.get("value"),
                    value_range=self._adapt_value_range(payload.get("valueRange")),
                    value_list=self._adapt_value_list(payload.get("valueList")),
                    metadata={
                        "id": payload.get("id"),
                        "zoom": payload.get("zoom"),
                        "scale": payload.get("scale"),
                        "operators": list(payload.get("operators") or []),
                        "supportedConnectType": payload.get("supportedConnectType"),
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
            event_key = str(payload.get("eventId")) if payload.get("eventId") is not None else self._string(payload.get("name")) or "event"
            events.append(
                SourceEventInput(
                    event_key=event_key,
                    name=self._string(payload.get("name")),
                    desc=self._string(payload.get("desc")),
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
            action_key = self._string(payload.get("actionName"))
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
            param_key = self._string(payload.get("propId"))
            params.append(
                SourceActionParamInput(
                    param_key=param_key,
                    name=self._string(payload.get("desc")) or param_key,
                    desc=self._string(payload.get("desc")),
                    format=self._string(payload.get("format")),
                    unit=self._normalized_unit(payload.get("unit")),
                    default=payload.get("value"),
                    value_range=self._adapt_value_range(payload.get("valueRange")),
                    value_list=self._adapt_value_list(payload.get("valueList")),
                    metadata={
                        "id": payload.get("id"),
                        "operators": list(payload.get("operators") or []),
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

    def _adapt_value_range(
        self, payload: Mapping[str, Any] | None
    ) -> SourceValueRangeInput | None:
        """适配数值范围元数据。"""
        if not payload:
            return None
        return SourceValueRangeInput(
            min=payload.get("min"),
            max=payload.get("max"),
            step=payload.get("step"),
        )

    def _adapt_value_list(self, payload: Any) -> list[SourceValueItemInput]:
        """适配枚举值列表。"""
        items: list[SourceValueItemInput] = []
        for item in payload or []:
            if not isinstance(item, Mapping):
                continue
            items.append(
                SourceValueItemInput(
                    code=str(item.get("code", "")),
                    desc=self._string(item.get("desc")),
                )
            )
        return items

    def _collect_categories(self, components: list[SourceComponentInput]) -> list[str]:
        """收集组件中不重复的类别列表。"""
        categories: list[str] = []
        for component in components:
            if component.category and component.category not in categories:
                categories.append(component.category)
        return categories

    def _build_model_id(self, pid: Any) -> str | None:
        """根据产品 ID 构建模型标识。"""
        return f"YL-{pid}" if pid is not None else None

    def _build_component_key(
        self,
        component: Mapping[str, Any],
        *,
        base_name: str,
        duplicate_count: int,
        occurrence: int,
    ) -> str:
        """构建组件唯一键，处理同名组件的歧义。"""
        index = component.get("index")
        if duplicate_count <= 1:
            return base_name
        if index is not None:
            return f"{base_name}_{index}"
        return f"{base_name}_{occurrence}"

    def _component_base_name(self, component: Mapping[str, Any]) -> str:
        """提取组件的 slug 化基础名称。"""
        category = self._string(component.get("category"))
        component_type = self._component_type(component.get("type"))
        if category:
            base = self._slugify(category)
        else:
            base = self._slugify(component.get("name")) or self._slugify(component.get("desc"))
        if not base:
            base = f"component_{component.get('cid', 'unknown')}"
        if component_type == "global" and not base.endswith("_global"):
            if base == "basic":
                return base
            return f"{base}_global"
        return base

    def _component_type(self, value: Any) -> str | None:
        """将组件类型数值映射为标识字符串。"""
        if value == 0:
            return "custom"
        if value == 1:
            return "global"
        return None

    def _property_type(self, value: Any) -> str | None:
        """将属性类型数值映射为标识字符串。"""
        if value == 0:
            return "apply"
        if value == 1:
            return "config"
        return None

    def _property_kind(self, payload: Mapping[str, Any]) -> str:
        """推断属性语义类别（info / config / state / control）。"""
        prop_id = self._string(payload.get("propId"))
        property_type = self._property_type(payload.get("type"))
        if prop_id in {"fv", "name", "icon", "mac"}:
            return "info"
        if property_type == "config":
            return "config"
        if payload.get("access") == 4:
            return "state"
        return "control"

    def _property_access(self, payload: Mapping[str, Any]) -> str:
        """推断属性读写访问级别。"""
        operators = payload.get("operators") or []
        if payload.get("access") == 4:
            return "read_only"
        if any(item in {"set", "toggle", "adjust"} for item in operators):
            return "read_write"
        return "read_only"

    def _derive_component_capabilities(self, component: Mapping[str, Any]) -> list[str]:
        """从组件的属性与动作中派生能力标识列表。"""
        category = self._string(component.get("category"))
        capabilities: list[str] = []
        if category:
            capabilities.append(category)

        for prop in component.get("properties") or []:
            if not isinstance(prop, Mapping):
                continue
            if self._property_kind(prop) != "control":
                continue
            prop_id = self._string(prop.get("propId"))
            token = f"{category}.{prop_id}" if category else prop_id
            if token and token not in capabilities:
                capabilities.append(token)

        for action in component.get("supportActions") or []:
            if not isinstance(action, Mapping):
                continue
            action_name = self._string(action.get("actionName"))
            if action_name and action_name not in capabilities:
                capabilities.append(action_name)

        return capabilities

    def _normalize_protocol(self, value: Any) -> str | None:
        """将协议描述标准化为小写标识。"""
        text = self._string(value).lower()
        if "matter" in text:
            return "matter"
        if "mesh" in text:
            return "mesh"
        if "thread" in text:
            return "thread"
        return text or None

    def _normalized_unit(self, value: Any) -> str | None:
        """标准化单位字符串。"""
        unit = self._string(value)
        return unit or None

    def _slugify(self, value: Any) -> str:
        """将任意文本转换为小写下划线 slug。"""
        text = self._string(value)
        if not text:
            return ""
        return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", text.lower())).strip("_")

    def _string(self, value: Any) -> str | None:
        """将值安全转换为非空字符串或 None。"""
        if value is None:
            return None
        text = str(value).strip()
        return text or None
