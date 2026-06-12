"""运行时产品模型推断的纯 helper。"""

from __future__ import annotations

from typing import Any, Mapping

from ..canonical.models import ComponentModel, EventModel, PropertyModel, ValueRangeModel
from ..capabilities.events import normalize_event_type
from ..event_identity import SAFETY_EVENT_COMPONENT_ID, SAFETY_EVENT_TYPES
from .openapi_properties import openapi_runtime_properties
from .runtime_templates import INDEXED_SWITCH_KEY_RE, RUNTIME_PROPERTY_TEMPLATES
from .runtime_template_selector import (
    runtime_property_ids_from_params,
    runtime_template_key,
)
from .runtime_subdevices import infer_subdevice_components as _infer_subdevice_components

def infer_runtime_components(payload: Mapping[str, Any]) -> list[ComponentModel]:
    """从载荷推断组件列表。"""
    subdevice_components = infer_subdevice_components(payload)
    if subdevice_components:
        return subdevice_components

    raw_params = payload.get("params")
    params: Mapping[str, Any] = raw_params if isinstance(raw_params, Mapping) else {}
    device_type = string_value(payload.get("type"))
    category = (
        string_value(payload.get("effective_category"))
        or string_value(payload.get("iot_category"))
        or string_value(payload.get("category"))
    )
    template_key = runtime_template_key(category or device_type, params)

    if template_key in {"relay_switch", "switch"}:
        indexed_components = infer_indexed_switch_components(category, params)
        if indexed_components:
            return indexed_components

    properties = infer_runtime_properties(template_key, params, payload=payload)
    events = infer_runtime_events(template_key, payload=payload)
    if not events:
        events = infer_openapi_events(payload)
    if not properties and not events:
        return []

    component_id = _runtime_event_component_id(template_key, payload)
    component_name = "新风" if component_id == "fresh_air" else component_id
    component_category = (
        "temp_control" if component_id == "fresh_air" else template_key
    )
    return [
        ComponentModel(
            component_id=component_id,
            name=component_name,
            component_type="custom",
            category=component_category or category or device_type,
            capabilities=infer_runtime_capabilities(template_key, properties),
            properties=properties,
            events=events,
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
            property_model = build_runtime_property_model(prop, "relay_switch")
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
    template_key: str | None,
    params: Mapping[str, Any],
    *,
    payload: Mapping[str, Any] | None = None,
) -> list[PropertyModel]:
    """根据设备类型和运行时参数推断属性列表。"""
    templates = RUNTIME_PROPERTY_TEMPLATES.get(template_key or "")
    if not templates:
        return []

    source_props: set[str]
    if params:
        source_props = runtime_property_ids_from_params(params)
    elif _payload_event_models(payload):
        source_props = set()
    else:
        source_props = set()

    properties = {
        prop.prop_id: prop
        for prop in openapi_runtime_properties(
            template_key,
            payload,
            build_property=build_runtime_property_model,
            string_value=string_value,
        )
    }
    for prop_id in templates:
        if prop_id not in source_props:
            continue
        property_model = build_runtime_property_model(prop_id, template_key or "")
        if property_model is not None:
            properties.setdefault(prop_id, property_model)
    return list(properties.values())


def infer_runtime_events(
    template_key: str | None,
    *,
    payload: Mapping[str, Any] | None = None,
) -> list[EventModel]:
    """根据运行时品类补齐文档支持的事件模型。"""
    payload_events = _payload_event_models(payload)
    if payload_events:
        return payload_events
    return [
        EventModel(name=name, semantic=name, params=[])
        for name in _runtime_event_types(template_key, payload)
    ]


def infer_openapi_events(payload: Mapping[str, Any]) -> list[EventModel]:
    """Build runtime events from explicit OpenAPI event rows."""
    return _payload_event_models(payload)


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
    if device_type in {"relay_switch", "switch"}:
        return ["onoff"]
    if device_type == "fresh_air":
        capabilities = ["onoff"]
        if "vmcf" in prop_ids:
            capabilities.append("speed")
        return capabilities
    if device_type in {"cover", "curtain"}:
        return ["position"]
    if device_type in {"binary_sensor", "contact_sensor", "human_sensor"}:
        return sorted(prop_ids)
    if device_type in {"sensor", "light_sensor", "other"}:
        return sorted(prop_ids)
    if device_type in {"climate", "temp_control"}:
        return sorted(prop_ids)
    return []


def _runtime_event_component_id(
    template_key: str | None,
    payload: Mapping[str, Any],
) -> str:
    """Return the component id implied by runtime-only event identity."""
    event_types = {
        event.semantic
        for event in _payload_event_models(payload)
        if event.semantic
    }
    if set(SAFETY_EVENT_TYPES).issubset(event_types):
        return SAFETY_EVENT_COMPONENT_ID
    return default_component_id(template_key)


def default_component_id(device_type: str | None) -> str:
    """获取默认组件标识。"""
    if device_type == "relay_switch":
        return "switch"
    if device_type == "contact_sensor":
        return "contact_sensor"
    if device_type == "human_sensor":
        return "human_sensor"
    if device_type == "light_sensor":
        return "light_sensor"
    if device_type == "curtain":
        return "curtain"
    if device_type == "temp_control":
        return "temp_control"
    if device_type == "fresh_air":
        return "fresh_air"
    if device_type == "scene_panel":
        return "scene_panel"
    if device_type == "knob_switch":
        return "knob_switch"
    if device_type:
        return device_type
    return "main"


RUNTIME_EVENT_TEMPLATES = {
    "scene_panel": ("click", "hold", "release_after_hold"),
    "knob_switch": ("knob_spin",),
}


def _payload_event_models(payload: Mapping[str, Any] | None) -> list[EventModel]:
    """Convert explicit OpenAPI event rows into canonical event models."""
    if not isinstance(payload, Mapping):
        return []
    projected: list[EventModel] = []
    seen: set[str] = set()
    for event in payload.get("events") or []:
        if not isinstance(event, Mapping):
            continue
        name = string_value(event.get("name"))
        normalized = (
            normalize_event_type(name)
            or normalize_event_type(event.get("semantic"))
            or normalize_event_type(event.get("id", event.get("eventId")))
        )
        key = normalized or name or string_value(event.get("id", event.get("eventId")))
        if not key or key in seen:
            continue
        seen.add(key)
        projected.append(
            EventModel(
                event_id=_int_value(event.get("id", event.get("eventId"))),
                name=name,
                desc=string_value(event.get("desc")),
                semantic=normalized,
                params=[],
            )
        )
    return projected


def _runtime_event_types(
    template_key: str | None,
    payload: Mapping[str, Any] | None,
) -> tuple[str, ...]:
    """Return runtime fallback event types for event-only devices."""
    return RUNTIME_EVENT_TEMPLATES.get(template_key or "", ())


def infer_subdevice_components(payload: Mapping[str, Any]) -> list[ComponentModel]:
    """从 OpenAPI ``subDeviceList`` 构建组件模型。"""
    return _infer_subdevice_components(
        payload,
        build_property=build_runtime_property_model,
        infer_capabilities=infer_runtime_capabilities,
        default_component_id=default_component_id,
        string_value=string_value,
    )


def string_value(value: Any) -> str | None:
    """将值安全转换为非空字符串或 None。"""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _int_value(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


__all__ = [
    "build_runtime_property_model",
    "default_component_id",
    "infer_indexed_switch_components",
    "infer_openapi_events",
    "infer_runtime_capabilities",
    "infer_subdevice_components",
    "infer_runtime_components",
    "infer_runtime_events",
    "infer_runtime_properties",
    "string_value",
]
