"""转换器：将源侧契约标准化为规范产品模型，并支持运行时推断。"""

from __future__ import annotations

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
from .runtime_inference import RuntimeInferredProductModelBuilder

__all__ = [
    "CanonicalProductBuilder",
    "RuntimeInferredProductModelBuilder",
    "YeelightProductSchemaConverter",
]


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
            zoom=prop.metadata.get("zoom", 1),
            scale=prop.metadata.get("scale", 1),
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
            zoom=param.metadata.get("zoom", 1),
            scale=param.metadata.get("scale", 1),
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
