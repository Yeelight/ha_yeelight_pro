"""Yeelight Pro event projector helper rules."""

from __future__ import annotations

import re
from typing import Any, Mapping

from homeassistant.components.event import EventDeviceClass

from ..canonical.models import ComponentInstanceModel, ComponentModel, HAProductModel
from ..capabilities.events import normalize_event_type
from ..capabilities.registry import iot_registry
from ..device_display import channel_name_label
from ..utils import matches_category, to_bool, to_category, to_str
from .common import component_index, humanize_component_id, schema_backed_component_available
from .device import project_payload_device_info

# 事件型组件 token。
EVENT_COMPONENT_TOKENS = ("scene_panel", "knob_switch", "button", "remote", "knob", "dial")
BUTTON_COMPONENT_TOKENS = ("scene_panel", "button", "remote")
MOTION_COMPONENT_TOKENS = ("motion", "presence", "occupancy")
DOORBELL_COMPONENT_TOKENS = ("doorbell",)
SCENE_PANEL_FALLBACK_EVENTS = ("click", "hold", "release_after_hold")
KNOB_SWITCH_FALLBACK_EVENTS = ("knob_spin", "multi_spin", "absolut_spin")
EVENT_DEVICE_NAME_TOKENS = (
    "全面屏",
    "智慧屏",
    "智能面板",
    "情景面板",
    "控制面板",
    "scene panel",
    "control panel",
)
KNOB_DEVICE_NAME_TOKENS = ("旋钮", "knob", "dial")


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
    projected: list[str] = []
    seen: set[str] = set()
    for event in component.events:
        event_type = (
            normalize_event_type(event.semantic)
            or normalize_event_type(event.name)
            or normalize_event_type(event.desc)
        )
        if event_type is None and event.event_id is not None:
            event_type = normalize_event_type(event.event_id)
        if not event_type or event_type in seen:
            continue
        seen.add(event_type)
        projected.append(event_type)
    return projected


def event_name(
    component: ComponentModel,
    *,
    total: int,
    device_payload: Mapping[str, Any] | None = None,
) -> str | None:
    """生成 event 实体名称。"""
    index = component_index(component.component_id)
    if index is not None:
        channel = channel_name_label(
            index=index,
            component=component,
            device_payload=device_payload,
        )
        return f"{channel}事件" if channel else None
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
    if matches_category(tokens, BUTTON_COMPONENT_TOKENS) or _has_registry_supported_events(component):
        return EventDeviceClass.BUTTON
    return None


def event_icon(component: ComponentModel, product_model: HAProductModel) -> str | None:
    """根据组件/产品类别推断 event 图标。"""
    tokens = _event_identity_tokens(component, product_model)
    if "knob" in tokens or "dial" in tokens or "旋钮" in tokens:
        return "mdi:knob"
    if (
        "scene_panel" in tokens
        or "button" in tokens
        or "remote" in tokens
        or "情景" in tokens
        or _has_registry_supported_events(component)
    ):
        return "mdi:gesture-tap-button"
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
    event_types = _fallback_event_types(device_payload, product_model)
    if not event_types:
        return None

    from .event import HAEventProjection

    component_id = _fallback_component_id(product_model)
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
        event_types=list(event_types),
        device_info=project_payload_device_info(device_payload, instance),
        device_class=EventDeviceClass.BUTTON,
        icon="mdi:gesture-tap-button",
    )


def _should_project_event_component(
    component: ComponentModel,
    product_model: HAProductModel,
    device_payload: Mapping[str, Any],
) -> bool:
    """判断组件是否应投影为 event 实体。"""
    if not component.events:
        return False

    category = to_category(component.category)
    component_id = component.component_id.lower()
    product_category = to_category(product_model.product.category)
    source_type = to_category(device_payload.get("type"))

    # 运动类组件由 binary_sensor 处理；schema 事件仍可经 registry 明确覆盖。
    if matches_category(category, MOTION_COMPONENT_TOKENS):
        return False

    has_registry_supported_events = _has_registry_supported_events(component)
    has_known_registry_events = _has_known_registry_events(component)

    if source_type in {"sensor", "binary_sensor"} and not (
        matches_category(category, EVENT_COMPONENT_TOKENS)
        or matches_category(component_id, EVENT_COMPONENT_TOKENS)
        or matches_category(product_category, EVENT_COMPONENT_TOKENS)
        or has_known_registry_events
    ):
        return False

    if (
        matches_category(category, EVENT_COMPONENT_TOKENS)
        or matches_category(component_id, EVENT_COMPONENT_TOKENS)
        or matches_category(product_category, EVENT_COMPONENT_TOKENS)
    ):
        return True

    return has_registry_supported_events or has_known_registry_events


def _fallback_event_types(
    device_payload: Mapping[str, Any],
    product_model: HAProductModel,
) -> tuple[str, ...]:
    """Return default events only for documented event-input categories."""
    tokens = _fallback_identity_tokens(device_payload, product_model)
    if matches_category(tokens, ("knob_switch",)) or matches_category(
        tokens,
        KNOB_DEVICE_NAME_TOKENS,
    ):
        return KNOB_SWITCH_FALLBACK_EVENTS
    if matches_category(tokens, ("scene_panel",)) or matches_category(
        tokens,
        EVENT_DEVICE_NAME_TOKENS,
    ):
        return SCENE_PANEL_FALLBACK_EVENTS
    return ()


def _fallback_component_id(product_model: HAProductModel) -> str:
    """Return a stable component id for fallback event entities."""
    for component in product_model.components:
        tokens = _event_identity_tokens(component, product_model)
        if matches_category(tokens, ("knob_switch",)) or matches_category(
            tokens,
            KNOB_DEVICE_NAME_TOKENS,
        ):
            return component.component_id
        if matches_category(tokens, ("scene_panel",)) or matches_category(
            tokens,
            EVENT_DEVICE_NAME_TOKENS,
        ):
            return component.component_id
    category = to_category(product_model.product.category)
    if matches_category(category, ("knob_switch",)) or matches_category(
        category,
        KNOB_DEVICE_NAME_TOKENS,
    ):
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
    tokens = _fallback_identity_tokens(device_payload, product_model)
    if matches_category(tokens, ("knob_switch",)) or matches_category(
        tokens,
        KNOB_DEVICE_NAME_TOKENS,
    ):
        return f"{channel}旋钮事件" if channel else "旋钮事件"
    if channel:
        return f"{channel}事件"
    if matches_category(tokens, EVENT_DEVICE_NAME_TOKENS):
        return "面板事件"
    return "设备事件"


def _fallback_identity_tokens(
    device_payload: Mapping[str, Any],
    product_model: HAProductModel,
) -> str:
    """Combine product and runtime identity fields for fallback event detection."""
    return " ".join(
        value
        for value in (
            to_category(device_payload.get("iot_category")),
            to_category(device_payload.get("category")),
            to_category(product_model.product.category),
            to_category(product_model.product.model),
            to_category(device_payload.get("name")),
            to_category(device_payload.get("deviceName")),
            to_category(device_payload.get("n")),
        )
        if value
    )


def _has_registry_supported_events(component: ComponentModel) -> bool:
    """判断组件 schema 事件是否属于 registry 明确支持的组件关系。"""
    component_keys = _registry_component_keys(component)
    if not component_keys:
        return False

    registry = iot_registry()
    for event_type in event_types(component):
        event_spec = next(
            (event for event in registry.events if event.normalized == event_type),
            None,
        )
        if event_spec is None:
            continue
        for component_alias in event_spec.components:
            if _normalize_component_alias(component_alias) in component_keys:
                return True
    return False


def _has_known_registry_events(component: ComponentModel) -> bool:
    """判断组件 schema 是否声明了 registry 已知事件类型。"""
    registry_event_types = {event.normalized for event in iot_registry().events}
    return any(event_type in registry_event_types for event_type in event_types(component))


def _event_identity_tokens(component: ComponentModel, product_model: HAProductModel) -> str:
    """合并 event 推断需要的组件与产品身份 token。"""
    return " ".join(
        value
        for value in (
            to_category(component.category),
            component.component_id.lower(),
            to_category(product_model.product.category),
        )
        if value
    )


def _registry_component_keys(component: ComponentModel) -> set[str]:
    """返回用于匹配 registry 组件别名的规范化身份集合。"""
    keys = {
        key
        for key in (
            _normalize_component_alias(component.component_id),
            _normalize_component_alias(component.name),
            _normalize_component_alias(component.desc),
            _normalize_component_alias(component.category),
            _normalize_component_alias(component.cid),
        )
        if key
    }
    registry = iot_registry()
    for key in tuple(keys):
        spec = registry.component_map.get(key)
        if spec is None:
            continue
        keys.update(
            key
            for key in (
                _normalize_component_alias(spec.alias),
                _normalize_component_alias(spec.name),
                _normalize_component_alias(spec.component_id),
            )
            if key
        )
    return keys


def _normalize_component_alias(value: Any) -> str:
    """归一化组件别名，兼容英文、中文、下划线和数字 id。"""
    text = to_str(value)
    if not text:
        return ""
    return re.sub(r"[\s_-]+", " ", text.lower()).strip()
