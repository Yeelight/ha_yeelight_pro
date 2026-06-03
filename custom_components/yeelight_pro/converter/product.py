"""转换器：将源侧契约标准化为规范产品模型，并支持运行时推断。"""

from __future__ import annotations

import re
from typing import Any, Mapping

from ..adapters.models import (
    SourceActionInput,
    SourceActionParamInput,
    SourceComponentInput,
    SourceEventInput,
    SourceProductSchemaInput,
    SourcePropertyInput,
    SourceValueItemInput,
    SourceValueRangeInput,
)
from ..adapters.product import YeelightProductSchemaAdapter
from ..canonical.models import (
    ActionModel,
    ActionParamModel,
    BridgeModel,
    ComponentModel,
    EventModel,
    HAProductModel,
    ProductModel,
    PropertyModel,
    ValueItemModel,
    ValueRangeModel,
)

# 默认亮度范围 (min, max, step)
DEFAULT_BRIGHTNESS_RANGE = (1, 100, 1)
# 默认色温范围 (min_kelvin, max_kelvin, step)
DEFAULT_COLOR_TEMP_RANGE_KELVIN = (2700, 6500, None)
# 索引式开关键匹配正则：形如 "1-p", "2-sp"
INDEXED_SWITCH_KEY_RE = re.compile(r"^(?P<index>\d+)-(?P<prop>p|sp)$")

# 运行时属性模板：覆盖 9 种设备类型的属性定义
RUNTIME_PROPERTY_TEMPLATES: dict[str, dict[str, dict[str, Any]]] = {
    "light": {
        "p": {"name": "开关", "kind": "control", "property_type": "apply", "format": "boolean", "access": "read_write"},
        "sp": {"name": "软开关", "kind": "control", "property_type": "apply", "format": "boolean", "access": "read_write"},
        "l": {
            "name": "亮度",
            "kind": "control",
            "property_type": "apply",
            "format": "uint8",
            "unit": "%",
            "access": "read_write",
            "value_range": DEFAULT_BRIGHTNESS_RANGE,
        },
        "ct": {
            "name": "色温",
            "kind": "control",
            "property_type": "apply",
            "format": "uint16",
            "unit": "kelvin",
            "access": "read_write",
            "value_range": DEFAULT_COLOR_TEMP_RANGE_KELVIN,
        },
        "c": {"name": "颜色", "kind": "control", "property_type": "apply", "format": "uint32", "access": "read_write"},
        "m": {"name": "模式", "kind": "state", "property_type": "apply", "format": "uint8", "access": "read_write"},
    },
    "fan": {
        "p": {"name": "开关", "kind": "control", "property_type": "apply", "format": "boolean", "access": "read_write"},
        "lv": {"name": "风速", "kind": "control", "property_type": "apply", "format": "uint8", "access": "read_write"},
        "dir": {"name": "风向", "kind": "control", "property_type": "apply", "format": "string", "access": "read_write"},
        "m": {"name": "模式", "kind": "control", "property_type": "apply", "format": "string", "access": "read_write"},
    },
    "switch": {
        "p": {"name": "开关", "kind": "control", "property_type": "apply", "format": "boolean", "access": "read_write"},
        "sp": {"name": "软开关", "kind": "control", "property_type": "apply", "format": "boolean", "access": "read_write"},
        "on": {"name": "开关", "kind": "control", "property_type": "apply", "format": "boolean", "access": "read_write"},
    },
    "cover": {
        "cp": {"name": "当前位置", "kind": "state", "property_type": "apply", "format": "uint8", "unit": "%", "access": "read_only"},
        "tp": {"name": "目标位置", "kind": "control", "property_type": "apply", "format": "uint8", "unit": "%", "access": "read_write"},
    },
    "binary_sensor": {
        "mv": {"name": "人体移动", "kind": "state", "property_type": "apply", "format": "boolean", "access": "read_only"},
        "dc": {"name": "门窗状态", "kind": "state", "property_type": "apply", "format": "boolean", "access": "read_only"},
        "alm": {"name": "防拆", "kind": "state", "property_type": "apply", "format": "boolean", "access": "read_only"},
    },
    "sensor": {
        "t": {"name": "温度", "kind": "state", "property_type": "apply", "format": "float", "unit": "°C", "access": "read_only"},
        "h": {"name": "湿度", "kind": "state", "property_type": "apply", "format": "float", "unit": "%", "access": "read_only"},
        "luminance": {"name": "照度", "kind": "state", "property_type": "apply", "format": "float", "unit": "lx", "access": "read_only"},
        "level": {"name": "等级", "kind": "state", "property_type": "apply", "format": "int", "access": "read_only"},
    },
    "climate": {
        "acm": {"name": "模式", "kind": "control", "property_type": "apply", "format": "uint8", "access": "read_write"},
        "actt": {"name": "目标温度", "kind": "control", "property_type": "apply", "format": "float", "unit": "°C", "access": "read_write"},
        "acct": {"name": "当前温度", "kind": "state", "property_type": "apply", "format": "float", "unit": "°C", "access": "read_only"},
        "acf": {"name": "风速", "kind": "control", "property_type": "apply", "format": "uint8", "access": "read_write"},
        "aco": {"name": "开关", "kind": "control", "property_type": "apply", "format": "boolean", "access": "read_write"},
    },
    "lock": {
        "lock": {"name": "门锁", "kind": "control", "property_type": "apply", "format": "boolean", "access": "read_write"},
        "locked": {"name": "门锁状态", "kind": "state", "property_type": "apply", "format": "boolean", "access": "read_only"},
        "lck": {"name": "门锁状态", "kind": "state", "property_type": "apply", "format": "boolean", "access": "read_only"},
    },
}


class CanonicalProductBuilder:
    """从标准化源侧输入构建规范产品模型。"""

    def build(self, source: SourceProductSchemaInput) -> HAProductModel:
        """从标准化源侧输入构建规范产品模型。"""
        return HAProductModel(
            schema_version="v1",
            product=ProductModel(
                model_id=source.model_id or source.product_key,
                manufacturer=source.manufacturer,
                model=source.name,
                description=source.description,
                category=source.category,
                categories=list(source.categories),
                bridge=self._build_bridge(source.bridge),
            ),
            components=[self._build_component(component) for component in source.components],
            device_actions=[self._build_action(action) for action in source.device_actions],
        )

    def _build_bridge(self, bridge: Any) -> BridgeModel | None:
        """构建桥接模型。"""
        if bridge is None:
            return None
        return BridgeModel(protocols=list(bridge.protocols))

    def _build_component(self, component: SourceComponentInput) -> ComponentModel:
        """构建组件模型。"""
        return ComponentModel(
            component_id=component.component_key,
            cid=component.cid,
            index=component.index,
            name=component.name,
            desc=component.desc,
            component_type=component.component_type,
            category=component.category,
            capabilities=list(component.capabilities),
            properties=[self._build_property(prop) for prop in component.properties],
            events=[self._build_event(event) for event in component.events],
            actions=[self._build_action(action) for action in component.actions],
        )

    def _build_property(self, prop: SourcePropertyInput) -> PropertyModel:
        """构建属性模型。"""
        return PropertyModel(
            prop_id=prop.property_key,
            name=prop.name,
            desc=prop.desc,
            semantic=prop.semantic,
            kind=prop.kind,
            property_type=prop.property_type,
            format=prop.format,
            unit=prop.unit,
            access=prop.access,
            default=prop.default,
            value_range=self._build_value_range(prop.value_range),
            value_list=[self._build_value_item(item) for item in prop.value_list],
        )

    def _build_event(self, event: SourceEventInput) -> EventModel:
        """构建事件模型。"""
        event_id = None
        try:
            event_id = int(event.event_key)
        except (TypeError, ValueError):
            event_id = event.metadata.get("eventId")
        return EventModel(
            event_id=event_id,
            name=event.name,
            desc=event.desc,
            semantic=event.semantic,
            params=[self._build_property(prop) for prop in event.params],
        )

    def _build_action(self, action: SourceActionInput) -> ActionModel:
        """构建动作模型。"""
        return ActionModel(
            action_name=action.action_key,
            name=action.name,
            desc=action.desc,
            semantic=action.semantic,
            scope=action.scope,
            targets=list(action.targets),
            params=[self._build_action_param(param) for param in action.params],
        )

    def _build_action_param(self, param: SourceActionParamInput) -> ActionParamModel:
        """构建动作参数模型。"""
        return ActionParamModel(
            prop_id=param.param_key,
            name=param.name,
            desc=param.desc,
            format=param.format,
            unit=param.unit,
            default=param.default,
            value_range=self._build_value_range(param.value_range),
            value_list=[self._build_value_item(item) for item in param.value_list],
        )

    def _build_value_range(
        self, value_range: SourceValueRangeInput | None
    ) -> ValueRangeModel | None:
        """构建数值范围模型。"""
        if value_range is None:
            return None
        return ValueRangeModel(
            min=value_range.min,
            max=value_range.max,
            step=value_range.step,
        )

    def _build_value_item(self, item: SourceValueItemInput) -> ValueItemModel:
        """构建枚举值模型。"""
        return ValueItemModel(code=item.code, desc=item.desc)


class YeelightProductSchemaConverter:
    """适配器 + 构建器门面，用于 Yeelight 产品模式转换。"""

    def __init__(
        self,
        manufacturer: str = "Yeelight",
        *,
        adapter: YeelightProductSchemaAdapter | None = None,
        builder: CanonicalProductBuilder | None = None,
    ) -> None:
        self._adapter = adapter or YeelightProductSchemaAdapter(manufacturer=manufacturer)
        self._builder = builder or CanonicalProductBuilder()

    def convert(self, schema: Mapping[str, Any]) -> HAProductModel:
        """将 ProductSchemaDtoV2 类映射转换为规范模型。"""
        return self._builder.build(self._adapter.adapt(schema))


class RuntimeInferredProductModelBuilder:
    """从运行时载荷构建临时规范产品模型。

    在正式产品模式源接入 Home Assistant 集成之前，
    此构建器使运行时链路保持模式感知能力。
    """

    def build(self, payload: Mapping[str, Any]) -> HAProductModel | None:
        """从运行时载荷推断并构建产品模型。"""
        model_id = self._string(payload.get("model_id"))
        if not model_id:
            return None

        components = self._infer_components(payload)
        if not components:
            return None

        product_type = self._string(payload.get("type")) or "unknown"
        category = self._string(payload.get("category"))

        return HAProductModel(
            schema_version="runtime-v1",
            product=ProductModel(
                model_id=model_id,
                manufacturer="Yeelight",
                model=category or self._string(payload.get("name")) or model_id,
                description="Runtime inferred product model",
                category=product_type,
                categories=[product_type] if product_type != "unknown" else [],
                bridge=None,
            ),
            components=components,
            device_actions=[],
            notes=[
                "This product model is inferred from runtime payloads.",
                "Replace it with the official product schema source when available.",
            ],
        )

    def merge(
        self,
        current: HAProductModel | None,
        payload: Mapping[str, Any],
    ) -> HAProductModel | None:
        """将运行时推断结果合并到现有产品模型。"""
        inferred = self.build(payload)
        if inferred is None:
            return current
        if current is None:
            return inferred

        merged_components: dict[str, ComponentModel] = {
            component.component_id: component for component in current.components
        }

        for component in inferred.components:
            existing = merged_components.get(component.component_id)
            if existing is None:
                merged_components[component.component_id] = component
                continue
            merged_components[component.component_id] = self._merge_component(existing, component)

        notes = list(current.notes)
        for note in inferred.notes:
            if note not in notes:
                notes.append(note)

        product = current.product
        return HAProductModel(
            schema_version=current.schema_version,
            product=ProductModel(
                model_id=product.model_id,
                manufacturer=product.manufacturer or inferred.product.manufacturer,
                model=product.model or inferred.product.model,
                description=product.description or inferred.product.description,
                category=product.category or inferred.product.category,
                categories=self._merge_text_list(product.categories, inferred.product.categories),
                bridge=product.bridge or inferred.product.bridge,
            ),
            components=list(merged_components.values()),
            device_actions=current.device_actions,
            notes=notes,
        )

    def _infer_components(self, payload: Mapping[str, Any]) -> list[ComponentModel]:
        """从载荷推断组件列表。"""
        params = payload.get("params") if isinstance(payload.get("params"), Mapping) else {}
        device_type = self._string(payload.get("type"))
        category = self._string(payload.get("category"))

        if device_type == "switch":
            indexed_components = self._infer_indexed_switch_components(category, params)
            if indexed_components:
                return indexed_components

        properties = self._infer_properties(device_type, params)
        if not properties:
            return []

        component_id = self._default_component_id(device_type)
        return [
            ComponentModel(
                component_id=component_id,
                name=component_id,
                component_type="custom",
                category=category or device_type,
                capabilities=self._infer_capabilities(device_type, properties),
                properties=properties,
                events=[],
                actions=[],
            )
        ]

    def _infer_indexed_switch_components(
        self,
        category: str | None,
        params: Mapping[str, Any],
    ) -> list[ComponentModel]:
        """推断索引式开关组件（如 1-p, 2-sp）。"""
        buckets: dict[int, set[str]] = {}
        for raw_key in params.keys():
            match = INDEXED_SWITCH_KEY_RE.match(str(raw_key))
            if not match:
                continue
            index = int(match.group("index"))
            prop = match.group("prop")
            buckets.setdefault(index, set()).add(prop)

        components: list[ComponentModel] = []
        for index in sorted(buckets):
            properties = [
                self._build_property_model(prop, "switch")
                for prop in sorted(buckets[index])
                if self._build_property_model(prop, "switch") is not None
            ]
            if not properties:
                continue
            components.append(
                ComponentModel(
                    component_id=f"switch_{index}",
                    index=index,
                    name=f"switch_{index}",
                    component_type="custom",
                    category=category or "switch",
                    capabilities=self._infer_capabilities("switch", properties),
                    properties=properties,
                    events=[],
                    actions=[],
                )
            )
        return components

    def _infer_properties(
        self,
        device_type: str | None,
        params: Mapping[str, Any],
    ) -> list[PropertyModel]:
        """根据设备类型和运行时参数推断属性列表。"""
        templates = RUNTIME_PROPERTY_TEMPLATES.get(device_type or "")
        if not templates:
            return []

        properties: list[PropertyModel] = []
        for prop_id in templates:
            if prop_id not in params:
                continue
            property_model = self._build_property_model(prop_id, device_type or "")
            if property_model is not None:
                properties.append(property_model)
        return properties

    def _build_property_model(
        self,
        prop_id: str,
        device_type: str,
    ) -> PropertyModel | None:
        """根据模板构建属性模型。"""
        template = RUNTIME_PROPERTY_TEMPLATES.get(device_type, {}).get(prop_id)
        if template is None:
            return None

        value_range = template.get("value_range")
        return PropertyModel(
            prop_id=prop_id,
            name=template.get("name"),
            kind=template.get("kind"),
            property_type=template.get("property_type"),
            format=template.get("format"),
            unit=template.get("unit"),
            access=template.get("access"),
            value_range=(
                ValueRangeModel(
                    min=value_range[0],
                    max=value_range[1],
                    step=value_range[2],
                )
                if value_range is not None
                else None
            ),
        )

    def _infer_capabilities(
        self,
        device_type: str | None,
        properties: list[PropertyModel],
    ) -> list[str]:
        """根据设备类型和属性列表推断能力标识。"""
        prop_ids = {prop.prop_id for prop in properties}
        if device_type == "light":
            capabilities = ["onoff"]
            if "l" in prop_ids:
                capabilities.append("brightness")
            if "ct" in prop_ids:
                capabilities.append("color_temp")
            if "c" in prop_ids:
                capabilities.append("rgb")
            return capabilities
        if device_type == "switch":
            return ["onoff"]
        if device_type == "fan":
            capabilities = ["onoff"]
            if "lv" in prop_ids:
                capabilities.append("speed")
            if "dir" in prop_ids:
                capabilities.append("direction")
            if "m" in prop_ids:
                capabilities.append("mode")
            return capabilities
        if device_type == "cover":
            return ["position"]
        if device_type == "binary_sensor":
            return sorted(prop_ids)
        if device_type == "sensor":
            return sorted(prop_ids)
        if device_type == "climate":
            return sorted(prop_ids)
        if device_type == "lock":
            return ["lock"]
        return []

    def _merge_component(
        self,
        current: ComponentModel,
        inferred: ComponentModel,
    ) -> ComponentModel:
        """合并现有组件与推断组件。"""
        properties = {prop.prop_id: prop for prop in current.properties}
        for prop in inferred.properties:
            properties.setdefault(prop.prop_id, prop)

        capabilities = self._merge_text_list(current.capabilities, inferred.capabilities)

        return ComponentModel(
            component_id=current.component_id,
            cid=current.cid or inferred.cid,
            index=current.index if current.index is not None else inferred.index,
            name=current.name or inferred.name,
            desc=current.desc or inferred.desc,
            component_type=current.component_type or inferred.component_type,
            category=current.category or inferred.category,
            capabilities=capabilities,
            properties=list(properties.values()),
            events=current.events or inferred.events,
            actions=current.actions or inferred.actions,
        )

    def _merge_text_list(self, current: list[str], inferred: list[str]) -> list[str]:
        """合并两个文本列表，去重保留顺序。"""
        out = list(current)
        for item in inferred:
            if item not in out:
                out.append(item)
        return out

    def _default_component_id(self, device_type: str | None) -> str:
        """获取默认组件标识。"""
        if device_type:
            return device_type
        return "main"

    def _string(self, value: Any) -> str | None:
        """将值安全转换为非空字符串或 None。"""
        if value is None:
            return None
        text = str(value).strip()
        return text or None
