"""OpenAPI sub-device runtime model inference helpers."""

from __future__ import annotations

import re
from typing import Any, Callable, Mapping

from ..canonical.models import ComponentModel, EventModel, PropertyModel
from ..capabilities.registry import normalize_event_type, platform_for_category
from ..device_display import switch_channel_count_hint
from ..utils import to_int
from .openapi_properties import openapi_property_model

_EVENT_KEY_RE = re.compile(r"^key(?P<index>\d+)\s+(?P<event>.+)$", re.IGNORECASE)

PropertyBuilder = Callable[[str, str], PropertyModel | None]
CapabilityInferer = Callable[[str | None, list[PropertyModel]], list[str]]
ComponentIdResolver = Callable[[str | None], str]
StringNormalizer = Callable[[Any], str | None]


def infer_subdevice_components(
    payload: Mapping[str, Any],
    *,
    build_property: PropertyBuilder,
    infer_capabilities: CapabilityInferer,
    default_component_id: ComponentIdResolver,
    string_value: StringNormalizer,
) -> list[ComponentModel]:
    """从 OpenAPI ``subDeviceList`` 构建组件模型。"""
    subdevices = [
        item for item in payload.get("subDeviceList") or [] if isinstance(item, Mapping)
    ]
    if not subdevices:
        return []

    events_by_index = _events_by_subdevice_index(payload.get("events"), string_value)
    components: list[ComponentModel] = []
    used_ids: set[str] = set()
    parent_category = (
        string_value(payload.get("effective_category"))
        or string_value(payload.get("iot_category"))
        or string_value(payload.get("category"))
    )
    switch_channel_count = switch_channel_count_hint(payload)

    for subdevice in subdevices:
        index = to_int(subdevice.get("index"))
        category = string_value(subdevice.get("category")) or parent_category
        if (
            switch_channel_count is not None
            and index is not None
            and index > switch_channel_count
            and platform_for_category(category) == "switch"
        ):
            continue
        properties = _runtime_subdevice_properties(
            subdevice,
            category,
            build_property=build_property,
            string_value=string_value,
        )
        events = _runtime_events(
            [
                *_event_items(subdevice.get("events")),
                *events_by_index.get(index, []),
            ],
            string_value=string_value,
        )
        component_id = _component_id(
            category,
            index,
            used_ids,
            default_component_id=default_component_id,
        )
        components.append(
            ComponentModel(
                component_id=component_id,
                cid=to_int(subdevice.get("cid", subdevice.get("id"))),
                index=index,
                name=string_value(subdevice.get("name")),
                desc=string_value(subdevice.get("desc")),
                component_type=_component_type_for_category(category),
                category=category,
                capabilities=infer_capabilities(category, properties),
                properties=properties,
                events=events,
                actions=[],
            )
        )

    return components


def _runtime_subdevice_properties(
    subdevice: Mapping[str, Any],
    category: str | None,
    *,
    build_property: PropertyBuilder,
    string_value: StringNormalizer,
) -> list[PropertyModel]:
    """将 sub-device 属性定义转换为 canonical property。"""
    properties: list[PropertyModel] = []
    for prop in subdevice.get("properties") or []:
        if not isinstance(prop, Mapping):
            continue
        prop_id = string_value(prop.get("propId", prop.get("propName")))
        if not prop_id:
            continue
        properties.append(
            openapi_property_model(
                prop_id,
                prop,
                category=category,
                build_property=build_property,
                string_value=string_value,
            )
            or build_property(prop_id, category or "")
            or PropertyModel(
                prop_id=prop_id,
                name=string_value(prop.get("name")) or string_value(prop.get("desc")),
                desc=string_value(prop.get("desc")),
                kind=_property_kind(prop, string_value),
                property_type="apply",
                format=string_value(prop.get("format", prop.get("fomat"))),
                unit=None,
                access=_property_access(prop, string_value),
            )
        )
    return properties


def _property_access(
    prop: Mapping[str, Any],
    string_value: StringNormalizer,
) -> str | None:
    """根据 OpenAPI operators/access 推断读写语义。"""
    operators = {
        str(item).strip().lower()
        for item in prop.get("operators") or []
        if str(item).strip()
    }
    if operators & {"set", "toggle", "adjust"}:
        return "read_write"
    access = prop.get("access")
    numeric_access = to_int(access)
    if numeric_access is not None:
        return "read_write" if numeric_access & 2 else "read_only"
    access_text = string_value(access)
    if access_text and _access_allows_write(access_text):
        return "read_write"
    if access_text and _access_is_read_only(access_text):
        return "read_only"
    return access_text


def _property_kind(
    prop: Mapping[str, Any],
    string_value: StringNormalizer,
) -> str:
    """OpenAPI 未显式区分 kind，按 operators 判断控制/状态。"""
    return "control" if _property_access(prop, string_value) == "read_write" else "state"


def _access_allows_write(value: str) -> bool:
    """判断 OpenAPI/CSV 文本权限是否包含写能力."""
    lowered = value.lower()
    return "write" in lowered or "写" in value


def _access_is_read_only(value: str) -> bool:
    """判断 OpenAPI/CSV 文本权限是否明确只读."""
    lowered = value.lower().replace(" ", "").replace("-", "_")
    return lowered in {"read", "read_only", "readonly", "ro", "r"} or value == "读"


def _events_by_subdevice_index(
    value: Any,
    string_value: StringNormalizer,
) -> dict[int | None, list[Mapping[str, Any]]]:
    """把顶层 keyN 事件按子设备 index 归属。"""
    mapped: dict[int | None, list[Mapping[str, Any]]] = {}
    for event in _event_items(value):
        index = _event_subdevice_index(event, string_value)
        mapped.setdefault(index, []).append(event)
    return mapped


def _event_items(value: Any) -> list[Mapping[str, Any]]:
    return [item for item in value or [] if isinstance(item, Mapping)]


def _event_subdevice_index(
    event: Mapping[str, Any],
    string_value: StringNormalizer,
) -> int | None:
    name = string_value(event.get("name"))
    if not name:
        return None
    match = _EVENT_KEY_RE.match(name)
    if match is None:
        return None
    return to_int(match.group("index"))


def _runtime_events(
    events: list[Mapping[str, Any]],
    *,
    string_value: StringNormalizer,
) -> list[EventModel]:
    """将 OpenAPI 事件定义转换为 canonical event。"""
    projected: list[EventModel] = []
    seen: set[str] = set()
    for event in events:
        name = string_value(event.get("name"))
        event_name = _event_name_without_key_prefix(name)
        normalized = normalize_event_type(event_name) or normalize_event_type(
            event.get("id")
        )
        key = normalized or event_name or string_value(event.get("id"))
        if not key or key in seen:
            continue
        seen.add(key)
        projected.append(
            EventModel(
                event_id=to_int(event.get("id", event.get("eventId"))),
                name=event_name or name,
                desc=string_value(event.get("desc")),
                semantic=normalized,
                params=[],
            )
        )
    return projected


def _event_name_without_key_prefix(name: str | None) -> str | None:
    if not name:
        return None
    match = _EVENT_KEY_RE.match(name)
    if match is None:
        return name
    return match.group("event").strip()


def _component_id(
    category: str | None,
    index: int | None,
    used_ids: set[str],
    *,
    default_component_id: ComponentIdResolver,
) -> str:
    """生成稳定且可从后缀解析 index 的组件 id。"""
    platform = platform_for_category(category)
    base = platform or default_component_id(category)
    if platform == "event":
        base = default_component_id(category)
    if not base or base == "button":
        base = default_component_id(category)
    suffix = str(index) if index is not None else str(len(used_ids) + 1)
    candidate = f"{base}_{suffix}"
    while candidate in used_ids:
        suffix = f"{suffix}_dup"
        candidate = f"{base}_{suffix}"
    used_ids.add(candidate)
    return candidate


def _component_type_for_category(category: str | None) -> str:
    """OpenAPI sub-device 是普通可投影组件，不是 global 诊断组件。"""
    return "normal" if category else "custom"


__all__ = ["infer_subdevice_components"]
