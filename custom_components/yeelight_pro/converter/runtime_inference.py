"""从运行时载荷推断临时规范产品模型。"""

from __future__ import annotations

from typing import Any, Mapping

from ..canonical.models import (
    ComponentModel,
    HAProductModel,
    ProductModel,
)
from .runtime_inference_helpers import infer_runtime_components, string_value


class RuntimeInferredProductModelBuilder:
    """从运行时载荷构建临时规范产品模型。

    在正式产品模式源接入 Home Assistant 集成之前，
    此构建器使运行时链路保持模式感知能力。
    """

    def build(self, payload: Mapping[str, Any]) -> HAProductModel | None:
        """从运行时载荷推断并构建产品模型。"""
        model_id = string_value(payload.get("model_id"))
        if not model_id:
            return None

        components = infer_runtime_components(payload)
        if not components:
            return None

        product_type = string_value(payload.get("type")) or "unknown"
        category = string_value(payload.get("category"))

        return HAProductModel(
            schema_version="runtime-v1",
            product=ProductModel(
                model_id=model_id,
                manufacturer="Yeelight",
                model=category or string_value(payload.get("name")) or model_id,
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
            merged_components[component.component_id] = self._merge_component(
                existing, component
            )

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
                categories=self._merge_text_list(
                    product.categories, inferred.product.categories
                ),
                bridge=product.bridge or inferred.product.bridge,
            ),
            components=list(merged_components.values()),
            device_actions=current.device_actions,
            notes=notes,
        )

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
