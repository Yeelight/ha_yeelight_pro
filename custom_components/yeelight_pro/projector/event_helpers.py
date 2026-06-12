"""Yeelight Pro event projector helper rules."""

from __future__ import annotations

from typing import Any, Mapping

from homeassistant.components.event import EventDeviceClass

from ..canonical.models import ComponentInstanceModel, ComponentModel, HAProductModel
from ..device_display import channel_name_label
from ..event_identity import (
    SAFETY_EVENT_COMPONENT_ID,
    SAFETY_EVENT_TYPES,
    is_safety_event_device,
)
from ..utils import matches_category, to_bool, to_category, to_str
from .common import component_index, humanize_component_id, schema_backed_component_available
from .device import project_payload_device_info
from .event_identity_helpers import (
    category_key as _category_key,
    event_identity_tokens as _event_identity_tokens,
    event_input_category as _event_input_category,
    event_types as _identity_event_types,
    fallback_event_input_category as _fallback_event_input_category,
    has_known_registry_events as _has_known_registry_events,
    has_registry_supported_events as _has_registry_supported_events,
)

MOTION_COMPONENT_TOKENS = ("motion", "presence", "occupancy")
DOORBELL_COMPONENT_TOKENS = ("doorbell",)
SCENE_PANEL_FALLBACK_EVENTS = ("click", "hold", "release_after_hold")
KNOB_SWITCH_FALLBACK_EVENTS = ("knob_spin",)


def event_components(
    product_model: HAProductModel,
    device_payload: Mapping[str, Any],
) -> list[ComponentModel]:
    """筛选产品模型中应投影为 event 的组件列表。"""
    return [
        component
        for component in product_model.components
        if _should_project_event_component(component, product_model, device_payload)
    ]


def event_types(component: ComponentModel) -> list[str]:
    """提取组件的规范化事件类型列表。"""
    return _identity_event_types(component)


def event_name(
    component: ComponentModel,
    *,
    total: int,
    product_model: HAProductModel,
    device_payload: Mapping[str, Any] | None = None,
) -> str | None:
    """生成 event 实体名称。"""
    if component.component_id == SAFETY_EVENT_COMPONENT_ID:
        return "报警事件"

    if _event_input_category(component, product_model):
        index = component_index(component.component_id)
        channel = channel_name_label(
            index=index,
            component=component,
            device_payload=device_payload,
        )
        if channel is not None:
            return _channel_event_name(channel)
    if total <= 1:
        return None

    desc = to_str(component.desc)
    if desc:
        return desc.removesuffix("组件")
    return humanize_component_id(component.component_id)


def event_device_class(
    component: ComponentModel,
    product_model: HAProductModel,
) -> EventDeviceClass | None:
    """根据组件/产品类别推断 event device class。"""
    tokens = _event_identity_tokens(component, product_model)
    if matches_category(tokens, DOORBELL_COMPONENT_TOKENS):
        return EventDeviceClass.DOORBELL
    if matches_category(tokens, MOTION_COMPONENT_TOKENS):
        return EventDeviceClass.MOTION
    if _event_input_category(component, product_model) or _has_registry_supported_events(
        component,
        product_model,
    ):
        return EventDeviceClass.BUTTON
    return None


def event_icon(component: ComponentModel, product_model: HAProductModel) -> str | None:
    """根据组件/产品类别推断 event 图标。"""
    if component.component_id == SAFETY_EVENT_COMPONENT_ID:
        return "mdi:smoke-detector"

    category = _event_input_category(component, product_model)
    if category == "knob_switch":
        return "mdi:knob"
    if category == "scene_panel" or _has_registry_supported_events(component, product_model):
        return "mdi:gesture-tap-button"
    tokens = _event_identity_tokens(component, product_model)
    if "doorbell" in tokens:
        return "mdi:doorbell"
    if matches_category(tokens, MOTION_COMPONENT_TOKENS):
        return "mdi:motion-sensor"
    return None


def component_available(
    component: ComponentInstanceModel | None,
    schema_component: ComponentModel | None = None,
) -> bool:
    """判断组件实例是否可用。"""
    return schema_backed_component_available(
        True,
        component,
        schema_component=schema_component,
    )


def event_fallback_projection(
    device_payload: Mapping[str, Any],
    product_model: HAProductModel,
    instance: Any,
    *,
    domain: str,
) -> Any | None:
    """为缺少 schema events 的已知事件输入设备生成保守 event 投影。"""
    fallback_event_types = _fallback_event_types(device_payload, product_model)
    if not fallback_event_types:
        return None

    from .event import HAEventProjection

    component_id = _fallback_component_id(device_payload, product_model)
    is_safety = component_id == SAFETY_EVENT_COMPONENT_ID
    source_device_id = (
        instance.device_id
        if instance is not None
        else str(device_payload.get("device_id", "unknown"))
    )
    available = to_bool(
        instance.online if instance is not None else device_payload.get("online"),
        default=True,
    )
    return HAEventProjection(
        component_id=component_id,
        unique_id=f"{domain}_{source_device_id}_{component_id}_event",
        name=_fallback_event_name(component_id, device_payload, product_model),
        available=available,
        event_types=list(fallback_event_types),
        device_info=project_payload_device_info(device_payload, instance),
        device_class=None if is_safety else EventDeviceClass.BUTTON,
        icon="mdi:smoke-detector" if is_safety else "mdi:gesture-tap-button",
    )


def _should_project_event_component(
    component: ComponentModel,
    product_model: HAProductModel,
    device_payload: Mapping[str, Any],
) -> bool:
    """判断组件是否应投影为 event 实体。"""
    if not component.events:
        return False

    category = _category_key(component.category)
    source_type = to_category(device_payload.get("type"))

    # 运动类组件由 binary_sensor 处理；schema 事件仍可经 registry 明确覆盖。
    if matches_category(category, MOTION_COMPONENT_TOKENS):
        return False

    has_registry_supported_events = _has_registry_supported_events(component, product_model)
    has_known_registry_events = _has_known_registry_events(component)

    if source_type in {"sensor", "binary_sensor"} and not (
        _event_input_category(component, product_model)
        or has_known_registry_events
    ):
        return False

    if _event_input_category(component, product_model):
        return True

    return has_registry_supported_events or has_known_registry_events


def _fallback_event_types(
    device_payload: Mapping[str, Any],
    product_model: HAProductModel,
) -> tuple[str, ...]:
    """Return default events only for documented event-input categories."""
    if is_safety_event_device(device_payload):
        return SAFETY_EVENT_TYPES

    category = _fallback_event_input_category(device_payload, product_model)
    if category == "knob_switch":
        return KNOB_SWITCH_FALLBACK_EVENTS
    if category == "scene_panel":
        return SCENE_PANEL_FALLBACK_EVENTS
    return ()


def _fallback_component_id(
    device_payload: Mapping[str, Any],
    product_model: HAProductModel,
) -> str:
    """Return a stable component id for fallback event entities."""
    if is_safety_event_device(device_payload):
        return SAFETY_EVENT_COMPONENT_ID

    for component in product_model.components:
        category = _event_input_category(component, product_model)
        if category == "knob_switch":
            return component.component_id
        if category == "scene_panel":
            return component.component_id
    category = _fallback_event_input_category(device_payload, product_model)
    if category == "knob_switch":
        return "knob_switch"
    return "scene_panel"


def _fallback_event_name(
    component_id: str,
    device_payload: Mapping[str, Any],
    product_model: HAProductModel,
) -> str:
    """Return readable fallback event names instead of the generic 事件."""
    index = component_index(component_id)
    channel = channel_name_label(index=index)
    category = _fallback_event_input_category(device_payload, product_model)
    if component_id == SAFETY_EVENT_COMPONENT_ID:
        return "报警事件"
    if category == "knob_switch":
        return _channel_event_name(channel, suffix="旋钮事件") if channel else "旋钮事件"
    if channel:
        return _channel_event_name(channel)
    if category == "scene_panel":
        return "面板事件"
    return "设备事件"


def _channel_event_name(channel: str, *, suffix: str = "事件") -> str:
    """Return readable event names without gluing numeric labels to suffixes."""
    separator = " " if any(char.isdecimal() for char in channel) else ""
    return f"{channel}{separator}{suffix}"
