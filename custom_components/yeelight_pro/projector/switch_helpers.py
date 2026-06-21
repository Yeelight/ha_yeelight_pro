"""Switch-specific helper functions for Yeelight Pro projections."""

from __future__ import annotations

from typing import Any, Mapping

from ..canonical.models import ComponentInstanceModel, ComponentModel, HADeviceInstanceModel
from ..capabilities.registry import (
    component_platform_hint,
    platform_for_category,
)
from ..device_channel_catalog import payload_product_spec, product_channel_count
from ..device_channel_semantics import component_name_key, component_text
from ..device_display import switch_channel_count_hint
from ..utils import to_category, to_int
from .common import component_index, component_state_key_map
from .common import load_product_model, product_component
from .event_input import is_event_input_category, is_event_input_component
from .platform_evidence import component_has_switch_evidence

from .switch_helper_constants import RAW_SWITCH_KEY_RE
from .switch_name_helpers import (
    _build_switch_name,
    _params,
    _raw_switch_sort_key,
)

DIRECT_SWITCH_PROPS = ("p", "sp")
WIRELESS_SWITCH_CHANNEL_KEYS = {
    "wireless switch channel",
    "wireless_switch_channel",
    "无线开关通道",
}
RELAY_SWITCH_COMPONENT_KEYS = {
    "switch",
    "switch control",
    "switch_control",
    "开关",
}
SWITCH_PARENT_CATEGORIES = {"relay_switch", "switch"}
NON_SWITCH_PARENT_CATEGORIES = {
    "binary_sensor",
    "climate",
    "contact_sensor",
    "cover",
    "curtain",
    "fan",
    "gateway",
    "human_sensor",
    "knob_switch",
    "light",
    "light_sensor",
    "scene_panel",
    "sensor",
    "temp_control",
}

def _allows_switch_projection(device_payload: Mapping[str, Any]) -> bool:
    """Return false when the parent device category owns another HA platform."""
    parent_category = to_category(
        device_payload.get("iot_category") or device_payload.get("category")
    )
    if parent_category in NON_SWITCH_PARENT_CATEGORIES:
        return False
    return True


def _allows_component_switch_projection(
    device_payload: Mapping[str, Any],
    instance: HADeviceInstanceModel,
) -> bool:
    """Allow schema-backed switch components on mixed-category products."""
    if _allows_switch_projection(device_payload):
        return True
    product_model = load_product_model(device_payload)
    return any(
        _looks_like_switch_component(
            component,
            product_component(product_model, component.component_id),
        )
        for component in instance.components
    )


def _allows_raw_switch_fallback(device_payload: Mapping[str, Any]) -> bool:
    """Return true when legacy raw params belong to a known switch device."""
    if not _allows_switch_projection(device_payload):
        return False

    parent_category = to_category(
        device_payload.get("iot_category") or device_payload.get("category")
    )
    if parent_category in SWITCH_PARENT_CATEGORIES:
        return True

    if platform_for_category(parent_category) == "switch":
        return True

    component_hint_values = (
        device_payload.get("component_id"),
        device_payload.get("component"),
    )
    if any(component_platform_hint(value) == "switch" for value in component_hint_values):
        return True

    if parent_category:
        return False
    return device_payload.get("type") == "switch"


def _component_state_key_map(
    instance: HADeviceInstanceModel,
) -> dict[str, dict[str, str]]:
    """构建 component_id -> {prop_id: raw_key} 的映射表."""
    return component_state_key_map(instance)


def _looks_like_switch_component(
    component: ComponentInstanceModel,
    product_component: ComponentModel | None = None,
) -> bool:
    """判断组件是否具备官方 relay switch 证据."""
    category = to_category(component.category)

    if is_event_input_category(category) and not _relay_event_component_has_power(
        component,
        product_component,
    ):
        return False
    if is_event_input_component(
        component.component_id
    ) and not _relay_event_component_has_power(component, product_component):
        return False

    features = {
        str(item).strip().lower()
        for item in (
            component.instance_capabilities.features
            if component.instance_capabilities is not None
            else []
        )
        if str(item).strip()
    }
    non_switch_features = {
        "brightness",
        "color_temp",
        "rgb",
        "speed",
        "direction",
        "mode",
        "position",
    }
    if non_switch_features & features:
        return False

    if _relay_event_component_has_power(component, product_component):
        return True
    if component_has_switch_evidence(component, product_component):
        return True
    if _looks_like_indexed_switch_channel(component, category):
        return True
    return bool(
        category.replace("_", " ") == "switch control"
        and _direct_switch_prop(component.state)
        and component_index(component.component_id) is not None
    )


def _prefers_switch_power_prop(
    device_payload: Mapping[str, Any],
    component: ComponentInstanceModel,
    product_component: ComponentModel | None = None,
) -> bool:
    """Return true when documented channel evidence says to control N-sp."""
    if _is_wireless_switch_channel_component(component):
        return True
    if _is_wireless_switch_channel_component(product_component):
        return True

    index = component_index(component.component_id)
    for item in _iter_subdevices(device_payload.get("subDeviceList")):
        if index is not None and to_int(item.get("index")) != index:
            continue
        if _is_wireless_switch_channel_component(item):
            return True

    spec = payload_product_spec(device_payload)
    if spec is None or product_channel_count(spec) is None:
        return False
    components = tuple(spec.normal_components) + tuple(
        component_name for component_name, _count in spec.normal_component_counts
    )
    return bool(components) and all(
        component_name_key(component_name) in WIRELESS_SWITCH_CHANNEL_KEYS
        for component_name in components
    )


def _is_wireless_switch_channel_component(component: Any | None) -> bool:
    """Return true for documented wireless switch channel metadata."""
    if component is None:
        return False
    values = (
        component_text(component, ("component_id", "componentId", "id")),
        component_text(component, ("name", "componentName", "component_name", "desc")),
        component_text(component, ("category",)),
    )
    return any(component_name_key(value) in WIRELESS_SWITCH_CHANNEL_KEYS for value in values)


def _iter_subdevices(value: Any) -> tuple[Mapping[str, Any], ...]:
    """Yield OpenAPI sub-device mappings without trusting arbitrary payload shapes."""
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


def _relay_event_component_has_power(
    component: ComponentInstanceModel,
    product_component: ComponentModel | None = None,
) -> bool:
    """Return true when an event-like relay component also owns power control."""
    category = to_category(component.category)
    if category != "relay_switch":
        return False
    if not _has_relay_switch_identity(component, product_component):
        return False
    prop_ids = {str(prop) for prop in component.state}
    if product_component is not None:
        prop_ids.update(prop.prop_id for prop in product_component.properties)
    return "p" in prop_ids


def _has_relay_switch_identity(
    component: ComponentInstanceModel,
    product_component: ComponentModel | None = None,
) -> bool:
    """Return true for documented relay switch components, not broad categories."""
    if component_has_switch_evidence(component, product_component):
        return True
    if _is_relay_switch_component(component):
        return True
    if _looks_like_indexed_switch_channel(component, to_category(component.category)):
        return True
    if _is_wireless_switch_channel_component(component):
        return True
    return _is_wireless_switch_channel_component(product_component)


def _is_relay_switch_component(component: Any | None) -> bool:
    """Return true for documented relay switch component identities."""
    if component is None:
        return False
    values = (
        component_text(component, ("component_id", "componentId", "id")),
        component_text(component, ("name", "componentName", "component_name", "desc")),
    )
    return any(component_name_key(value) in RELAY_SWITCH_COMPONENT_KEYS for value in values)


def _looks_like_indexed_switch_channel(
    component: ComponentInstanceModel,
    category: str,
) -> bool:
    """Return true for canonical indexed relay-switch channels."""
    if category not in {"relay_switch", "switch"}:
        return False
    if not _direct_switch_prop(component.state):
        return False
    index = component_index(component.component_id)
    if index is None:
        return False
    return component.component_id.startswith(("relay_switch_", "switch_"))


def _direct_switch_prop(state: Mapping[str, Any]) -> str | None:
    """返回 state 中的直接开关属性（p/sp），存在索引键时返回 None."""
    if _extract_indexed_switch_keys(state):
        return None
    for prop in DIRECT_SWITCH_PROPS:
        if prop in state:
            return prop
    return None


def _extract_indexed_switch_keys(state: Mapping[str, Any]) -> list[str]:
    """提取并排序所有匹配 N-p/N-sp 模式的索引开关键."""
    keys = [str(key) for key in state.keys() if RAW_SWITCH_KEY_RE.match(str(key))]
    keys.sort(key=_raw_switch_sort_key)
    return keys


def _switch_channel_allowed(device_payload: Mapping[str, Any], index: int | None) -> bool:
    """Return false when product naming explicitly limits switch channel count."""
    if index is None:
        return True
    count = switch_channel_count_hint(device_payload)
    return count is None or index <= count


def _resolve_component_control_key(
    component_id: str,
    prop: str,
    *,
    params: Mapping[str, Any],
    key_map: Mapping[str, Mapping[str, str]],
) -> str:
    """解析组件的实际控制键，优先使用显式 key_map."""
    mapped = key_map.get(component_id, {}).get(prop)
    if mapped:
        return mapped

    index = component_index(component_id)
    if index is not None:
        candidate = f"{index}-{prop}"
        if candidate in params or not params:
            return candidate
    return prop


def _component_id_from_raw_key(raw_key: str) -> str:
    """将原始键（如 '1-p'）转换为 component_id（如 'switch_1'）."""
    match = RAW_SWITCH_KEY_RE.match(raw_key)
    if not match:
        return "switch"
    return f"switch_{match.group('index')}"


def _index_from_raw_key(raw_key: str) -> int | None:
    """Return indexed switch key index from N-p/N-sp control keys."""
    match = RAW_SWITCH_KEY_RE.match(raw_key)
    if match is None:
        return None
    return to_int(match.group("index"))


__all__ = [
    "_allows_component_switch_projection",
    "_allows_raw_switch_fallback",
    "_build_switch_name",
    "_component_id_from_raw_key",
    "_component_state_key_map",
    "_direct_switch_prop",
    "_extract_indexed_switch_keys",
    "_index_from_raw_key",
    "_looks_like_switch_component",
    "_params",
    "_prefers_switch_power_prop",
    "_resolve_component_control_key",
    "_switch_channel_allowed",
]
