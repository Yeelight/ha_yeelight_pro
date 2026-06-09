"""运行时产品模型推断的纯 helper。"""

from __future__ import annotations

from typing import Any, Mapping

from ..canonical.models import ComponentModel, PropertyModel, ValueRangeModel
from .runtime_templates import INDEXED_SWITCH_KEY_RE, RUNTIME_PROPERTY_TEMPLATES


def infer_runtime_components(payload: Mapping[str, Any]) -> list[ComponentModel]:
    """从载荷推断组件列表。"""
    raw_params = payload.get("params")
    params: Mapping[str, Any] = raw_params if isinstance(raw_params, Mapping) else {}
    device_type = string_value(payload.get("type"))
    category = string_value(payload.get("category"))

    if device_type == "switch":
        indexed_components = infer_indexed_switch_components(category, params)
        if indexed_components:
            return indexed_components

    properties = infer_runtime_properties(device_type, params)
    if not properties:
        return []

    component_id = default_component_id(device_type)
    return [
        ComponentModel(
            component_id=component_id,
            name=component_id,
            component_type="custom",
            category=category or device_type,
            capabilities=infer_runtime_capabilities(device_type, properties),
            properties=properties,
            events=[],
            actions=[],
        )
    ]


def infer_indexed_switch_components(
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
        properties = []
        for prop in sorted(buckets[index]):
            property_model = build_runtime_property_model(prop, "switch")
            if property_model is not None:
                properties.append(property_model)
        if not properties:
            continue
        components.append(
            ComponentModel(
                component_id=f"switch_{index}",
                index=index,
                name=f"switch_{index}",
                component_type="custom",
                category=category or "switch",
                capabilities=infer_runtime_capabilities("switch", properties),
                properties=properties,
                events=[],
                actions=[],
            )
        )
    return components


def infer_runtime_properties(
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
        property_model = build_runtime_property_model(prop_id, device_type or "")
        if property_model is not None:
            properties.append(property_model)
    return properties


def build_runtime_property_model(
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


def infer_runtime_capabilities(
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


def default_component_id(device_type: str | None) -> str:
    """获取默认组件标识。"""
    if device_type:
        return device_type
    return "main"


def string_value(value: Any) -> str | None:
    """将值安全转换为非空字符串或 None。"""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


__all__ = [
    "build_runtime_property_model",
    "default_component_id",
    "infer_indexed_switch_components",
    "infer_runtime_capabilities",
    "infer_runtime_components",
    "infer_runtime_properties",
    "string_value",
]
