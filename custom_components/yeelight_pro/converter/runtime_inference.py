"""从运行时载荷推断临时规范产品模型。"""

from __future__ import annotations

from typing import Any, Mapping

from ..canonical.models import (
    ComponentModel,
    HAProductModel,
    ProductModel,
)
from ..capabilities.registry import is_iot_category, product_model_from_catalog
from .runtime_inference_helpers import infer_runtime_components, string_value


class RuntimeInferredProductModelBuilder:
    """从运行时载荷构建临时规范产品模型。

    在正式产品模式源接入 Home Assistant 集成之前，
    此构建器使运行时链路保持模式感知能力。
    """

    def build(self, payload: Mapping[str, Any]) -> HAProductModel | None:
        """从运行时载荷推断并构建产品模型。"""
        model_id = _model_id(payload)
        if not model_id:
            return None

        components = infer_runtime_components(payload)
        catalog_model = product_model_from_catalog(payload.get("pid"))
        if catalog_model is not None and components and not _has_live_capability_evidence(payload):
            return catalog_model
        if not components:
            if catalog_model is not None:
                return catalog_model
            return _metadata_only_model(payload, model_id)

        iot_category = _effective_category(payload)
        product_type = iot_category or string_value(payload.get("type")) or "unknown"

        runtime_model = HAProductModel(
            schema_version="runtime-v1",
            product=ProductModel(
                model_id=model_id,
                manufacturer="Yeelight",
                model=_runtime_model_name(payload, catalog_model, iot_category, model_id),
                description="Runtime inferred product model",
                category=product_type,
                categories=[product_type] if product_type != "unknown" else [],
                bridge=catalog_model.product.bridge if catalog_model is not None else None,
            ),
            components=components,
            device_actions=[],
            notes=[
                "This product model is inferred from runtime payloads.",
                "Replace it with the official product schema source when available.",
            ],
        )
        return self._merge_catalog(runtime_model, catalog_model)

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

    def _merge_catalog(
        self,
        runtime_model: HAProductModel,
        catalog_model: HAProductModel | None,
    ) -> HAProductModel:
        """用产品构成目录补齐运行时模型缺少的组件轮廓."""
        if catalog_model is None:
            return runtime_model
        return self._merge_product_models(catalog_model, runtime_model)

    def _merge_product_models(
        self,
        current: HAProductModel,
        inferred: HAProductModel,
    ) -> HAProductModel:
        """合并两个已构建的产品模型."""
        merged_components: dict[str, ComponentModel] = {
            component.component_id: component for component in current.components
        }
        for component in inferred.components:
            existing = merged_components.get(component.component_id)
            merged_components[component.component_id] = (
                component if existing is None else self._merge_component(existing, component)
            )

        notes = list(current.notes)
        for note in inferred.notes:
            if note not in notes:
                notes.append(note)

        product = current.product
        category = (
            inferred.product.category
            if inferred.product.category and inferred.product.category != "unknown"
            else product.category
        )
        return HAProductModel(
            schema_version=current.schema_version,
            product=ProductModel(
                model_id=product.model_id or inferred.product.model_id,
                manufacturer=product.manufacturer or inferred.product.manufacturer,
                model=product.model or inferred.product.model,
                description=product.description or inferred.product.description,
                category=category,
                categories=self._merge_text_list(
                    inferred.product.categories,
                    product.categories,
                ),
                bridge=product.bridge or inferred.product.bridge,
            ),
            components=list(merged_components.values()),
            device_actions=current.device_actions or inferred.device_actions,
            notes=notes,
        )


def _runtime_model_id(payload: Mapping[str, Any]) -> str | None:
    """为缺少官方 schema 的运行时设备生成稳定型号标识."""
    pid = string_value(payload.get("pid"))
    if pid:
        return f"YL-{pid}"
    product_id = string_value(payload.get("productId") or payload.get("product_id"))
    if product_id:
        return f"YL-{product_id}"
    category = _effective_category(payload) or string_value(payload.get("type"))
    if category:
        return f"runtime-{category}"
    return None


def _has_live_capability_evidence(payload: Mapping[str, Any]) -> bool:
    """Return true when runtime data carries live properties, components, or events."""
    params = payload.get("params")
    if isinstance(params, Mapping) and bool(params):
        return True
    for key in ("properties", "subDeviceList", "events"):
        value = payload.get(key)
        if isinstance(value, list) and bool(value):
            return True
    return False


def _metadata_only_model(
    payload: Mapping[str, Any],
    model_id: str,
) -> HAProductModel | None:
    """Build a category-only model without inventing unsupported entities."""
    category = _documented_payload_category(payload)
    if category is None:
        return None
    return HAProductModel(
        schema_version="runtime-v1",
        product=ProductModel(
            model_id=model_id,
            manufacturer="Yeelight",
            model=_runtime_model_name(payload, None, category, model_id),
            description="Runtime inferred metadata-only product model",
            category=category,
            categories=[category],
            bridge=None,
        ),
        components=[],
        device_actions=[],
        notes=[
            "This product model keeps documented Yeelight category metadata only.",
            "No entities are projected until component properties or events are available.",
        ],
    )


def _documented_payload_category(payload: Mapping[str, Any]) -> str | None:
    """Return an explicit Yeelight category declared by structured payload fields."""
    for key in ("effective_category", "iot_category", "category", "type"):
        category = _normalized_category(payload.get(key))
        if category is not None:
            return category
    return None


def _normalized_category(value: Any) -> str | None:
    text = string_value(value)
    if text is None:
        return None
    category = text.lower().replace("-", "_").replace(" ", "_")
    if category == "switch":
        category = "relay_switch"
    return category if is_iot_category(category) else None


def _model_id(payload: Mapping[str, Any]) -> str | None:
    """Return the best registry-facing model id for runtime-inferred models."""
    product_model_id = _product_model_id(payload)
    if product_model_id is not None:
        return product_model_id
    explicit = string_value(payload.get("model_id"))
    if explicit and not explicit.startswith("runtime-"):
        return explicit
    return explicit or _runtime_model_id(payload)


def _product_model_id(payload: Mapping[str, Any]) -> str | None:
    """Return a product-id based model id when OpenAPI exposes a product key."""
    pid = string_value(payload.get("pid"))
    if pid:
        return f"YL-{pid}"
    product_id = string_value(payload.get("productId") or payload.get("product_id"))
    if product_id:
        return f"YL-{product_id}"
    return None


def _runtime_model_name(
    payload: Mapping[str, Any],
    catalog_model: HAProductModel | None,
    iot_category: str | None,
    model_id: str,
) -> str:
    """Return a model name without using the user-editable device name."""
    if catalog_model is not None and catalog_model.product.model:
        return catalog_model.product.model
    return iot_category or model_id


def _effective_category(payload: Mapping[str, Any]) -> str | None:
    """Return capability-derived category, falling back to raw category."""
    return (
        string_value(payload.get("effective_category"))
        or string_value(payload.get("iot_category"))
        or string_value(payload.get("category"))
    )
