"""将 canonical 产品/运行时数据投影为 Home Assistant event 视图."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping

from homeassistant.components.event import EventDeviceClass

from ..canonical.models import ComponentModel, ComponentInstanceModel, HADeviceInstanceModel, HAProductModel
from ..utils import to_bool, to_str, to_category, matches_category
from .device import project_device_info

# 事件型组件 token
EVENT_COMPONENT_TOKENS = ("scene_panel", "knob_switch", "button", "remote", "knob", "dial")
BUTTON_COMPONENT_TOKENS = ("scene_panel", "button", "remote")
MOTION_COMPONENT_TOKENS = ("motion", "presence", "occupancy")
DOORBELL_COMPONENT_TOKENS = ("doorbell",)
INDEX_RE = re.compile(r"_(?P<index>\d+)$")

# 事件类型规范化：非字母数字字符替换 + 别名映射
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_EVENT_TYPE_ALIASES: dict[str, str] = {
    "keyclick": "click",
    "key_click": "click",
    "single_click": "click",
    "longpress": "hold",
    "long_press": "hold",
    "keyhold": "hold",
    "releaseafterhold": "release_after_hold",
    "release_after_long_press": "release_after_hold",
    "keyreleaseafterlongpress": "release_after_hold",
    "freespin": "knob_spin",
    "free_spin": "knob_spin",
    "holdspin": "knob_spin",
    "hold_spin": "knob_spin",
    "knobspin": "knob_spin",
    "spin": "knob_spin",
    "rotate": "knob_spin",
    "motiontrue": "motion_detected",
    "motion_true": "motion_detected",
    "motiondetected": "motion_detected",
    "motionfalse": "motion_undetected",
    "motion_false": "motion_undetected",
    "motionundetected": "motion_undetected",
}


@dataclass(slots=True)
class HAEventProjection:
    """投影后的 Home Assistant event 实体视图."""

    component_id: str
    unique_id: str
    name: str | None
    available: bool
    event_types: list[str]
    device_info: dict[str, Any] | None
    device_class: EventDeviceClass | None = None
    icon: str | None = None


@dataclass(slots=True)
class HADeviceTriggerProjection:
    """投影后的 Home Assistant device trigger 视图."""

    component_id: str
    type: str
    subtype: str


def project_events(device_payload: Mapping[str, Any], *, domain: str) -> list[HAEventProjection]:
    """将 coordinator 设备数据投影为 Home Assistant event 实体列表."""
    instance = _load_instance(device_payload)
    product_model = _load_product_model(device_payload)
    if product_model is None:
        return []

    source_device_id = (
        instance.device_id
        if instance is not None
        else str(device_payload.get("device_id", "unknown"))
    )
    available = to_bool(
        instance.online if instance is not None else device_payload.get("online"),
        default=False,
    )
    instance_components = {
        component.component_id: component for component in (instance.components if instance else [])
    }
    event_components = _event_components(product_model, device_payload)
    device_info = project_device_info(instance) if instance is not None else None

    projections: list[HAEventProjection] = []
    total = len(event_components)
    for component in event_components:
        component_instance = instance_components.get(component.component_id)
        projections.append(
            HAEventProjection(
                component_id=component.component_id,
                unique_id=f"{domain}_{source_device_id}_{component.component_id}_event",
                name=_event_name(component, total=total),
                available=available and _component_available(component_instance),
                event_types=_event_types(component),
                device_info=device_info,
                device_class=_event_device_class(component, product_model),
                icon=_event_icon(component, product_model),
            )
        )
    return projections


def project_device_triggers(device_payload: Mapping[str, Any]) -> list[HADeviceTriggerProjection]:
    """投影 event 类型设备支持的 Home Assistant device trigger 列表."""
    product_model = _load_product_model(device_payload)
    if product_model is None:
        return []

    triggers: list[HADeviceTriggerProjection] = []
    for component in _event_components(product_model, device_payload):
        for event_type in _event_types(component):
            triggers.append(
                HADeviceTriggerProjection(
                    component_id=component.component_id,
                    type=component.component_id,
                    subtype=event_type,
                )
            )
    return triggers


# ---------------------------------------------------------------------------
# 内部辅助函数
# ---------------------------------------------------------------------------


def _load_instance(device_payload: Mapping[str, Any]) -> HADeviceInstanceModel | None:
    """从设备 payload 中加载设备实例模型."""
    payload = device_payload.get("ha_device_instance")
    if not isinstance(payload, Mapping):
        return None
    return HADeviceInstanceModel.from_dict(payload)


def _load_product_model(device_payload: Mapping[str, Any]) -> HAProductModel | None:
    """从设备 payload 中加载产品模型."""
    payload = device_payload.get("ha_product_model")
    if not isinstance(payload, Mapping):
        return None
    return HAProductModel.from_dict(payload)


def _event_components(
    product_model: HAProductModel,
    device_payload: Mapping[str, Any],
) -> list[ComponentModel]:
    """筛选产品模型中应投影为 event 的组件列表."""
    return [
        component
        for component in product_model.components
        if _should_project_event_component(component, product_model, device_payload)
    ]


def _should_project_event_component(
    component: ComponentModel,
    product_model: HAProductModel,
    device_payload: Mapping[str, Any],
) -> bool:
    """判断组件是否应投影为 event 实体."""
    if not component.events:
        return False

    category = to_category(component.category)
    component_id = component.component_id.lower()
    product_category = to_category(product_model.product.category)
    source_type = to_category(device_payload.get("type"))

    # 排除运动类组件（由 binary_sensor 处理）
    if matches_category(category, MOTION_COMPONENT_TOKENS):
        return False
    # sensor/binary_sensor 来源仅在匹配事件 token 时投影
    if source_type in {"sensor", "binary_sensor"} and not (
        matches_category(category, EVENT_COMPONENT_TOKENS)
        or matches_category(component_id, EVENT_COMPONENT_TOKENS)
        or matches_category(product_category, EVENT_COMPONENT_TOKENS)
    ):
        return False

    return (
        matches_category(category, EVENT_COMPONENT_TOKENS)
        or matches_category(component_id, EVENT_COMPONENT_TOKENS)
        or matches_category(product_category, EVENT_COMPONENT_TOKENS)
    )


def _event_types(component: ComponentModel) -> list[str]:
    """提取组件的规范化事件类型列表."""
    event_types: list[str] = []
    seen: set[str] = set()
    for event in component.events:
        event_type = (
            _normalize_event_type(event.semantic)
            or _normalize_event_type(event.name)
            or _normalize_event_type(event.desc)
        )
        if event_type is None and event.event_id is not None:
            event_type = _normalize_event_type(event.event_id)
        if not event_type or event_type in seen:
            continue
        seen.add(event_type)
        event_types.append(event_type)
    return event_types


def _event_name(component: ComponentModel, *, total: int) -> str | None:
    """生成 event 实体名称."""
    index = _component_index(component.component_id)
    if index is not None and total > 1:
        return str(index)
    if total <= 1:
        return None

    desc = to_str(component.desc)
    if desc:
        return desc.removesuffix("组件")
    return _humanize_component_id(component.component_id)


def _event_device_class(
    component: ComponentModel,
    product_model: HAProductModel,
) -> EventDeviceClass | None:
    """根据组件/产品类别推断 event device class."""
    tokens = " ".join(
        value
        for value in (
            to_category(component.category),
            component.component_id.lower(),
            to_category(product_model.product.category),
        )
        if value
    )
    if matches_category(tokens, DOORBELL_COMPONENT_TOKENS):
        return EventDeviceClass.DOORBELL
    if matches_category(tokens, MOTION_COMPONENT_TOKENS):
        return EventDeviceClass.MOTION
    if matches_category(tokens, BUTTON_COMPONENT_TOKENS):
        return EventDeviceClass.BUTTON
    return None


def _event_icon(component: ComponentModel, product_model: HAProductModel) -> str | None:
    """根据组件/产品类别推断 event 图标."""
    tokens = " ".join(
        value
        for value in (
            to_category(component.category),
            component.component_id.lower(),
            to_category(product_model.product.category),
        )
        if value
    )
    if "knob" in tokens or "dial" in tokens or "旋钮" in tokens:
        return "mdi:knob"
    if "scene_panel" in tokens or "button" in tokens or "remote" in tokens or "情景" in tokens:
        return "mdi:gesture-tap-button"
    if "doorbell" in tokens:
        return "mdi:doorbell"
    if matches_category(tokens, MOTION_COMPONENT_TOKENS):
        return "mdi:motion-sensor"
    return None


def _component_available(component: ComponentInstanceModel | None) -> bool:
    """判断组件实例是否可用."""
    if component is None:
        return True
    return bool(component.available)


def _component_index(component_id: str) -> int | None:
    """从组件 ID 中提取数字索引."""
    match = INDEX_RE.search(component_id)
    if not match:
        return None
    try:
        return int(match.group("index"))
    except (TypeError, ValueError):
        return None


def _humanize_component_id(component_id: str) -> str | None:
    """将组件 ID 转换为人类可读名称."""
    text = component_id.replace("_", " ").strip()
    return text or None


def _normalize_event_type(value: Any) -> str | None:
    """将上游事件标签规范化为稳定的 snake_case 值."""
    text = to_str(value)
    if not text:
        return None
    normalized = _NON_ALNUM_RE.sub("_", text.lower()).strip("_")
    if not normalized:
        return None
    return _EVENT_TYPE_ALIASES.get(normalized, normalized)
