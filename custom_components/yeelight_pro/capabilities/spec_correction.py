"""Yeelight IoT 产品 schema 修正规则.

规则层只做保守的 filter/modify：修正上游字段形态，标记不应进入
运行时实体状态的属性；不凭空补能力。
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from .spec_correction_normalizers import (
    normalize_component_type,
    normalize_property_access,
    normalize_property_format,
    normalize_property_operators,
    normalize_property_type,
    normalize_source_property_type,
    text_value,
)

INFO_PROPERTY_IDS = frozenset({"fv", "hwv", "icon", "mac", "name", "o", "online", "sn"})
CONFIG_PROPERTY_IDS = frozenset({"c_n_c", "cfg", "component_num_config"})
SENSITIVE_PROPERTY_IDS = frozenset(
    {
        "devicekey",
        "hrbk",
        "localtoken",
        "local_token",
        "ltk",
        "mibk",
        "midk",
        "psk",
        "token",
    }
)
RUNTIME_FILTERED_KINDS = frozenset({"config", "diagnostic", "info"})


@dataclass(frozen=True, slots=True)
class YeelightPropertyCorrection:
    """属性 schema 修正结果."""

    kind: str
    property_type: str | None
    format: str | None
    access: str
    runtime_filtered: bool


@dataclass(frozen=True, slots=True)
class YeelightSpecCorrectionSummary:
    """产品 schema 修正聚合摘要."""

    components_seen: int = 0
    properties_seen: int = 0
    runtime_filtered_properties: int = 0
    normalized_format_properties: int = 0
    writable_properties: int = 0
    readonly_properties: int = 0

    def as_dict(self) -> dict[str, int]:
        """返回 diagnostics-safe 字典."""
        return {
            "components_seen": self.components_seen,
            "properties_seen": self.properties_seen,
            "runtime_filtered_properties": self.runtime_filtered_properties,
            "normalized_format_properties": self.normalized_format_properties,
            "writable_properties": self.writable_properties,
            "readonly_properties": self.readonly_properties,
        }


def correct_property_schema(
    component: Mapping[str, Any] | None,
    prop: Mapping[str, Any],
    *,
    property_type: str | None,
) -> YeelightPropertyCorrection:
    """返回属性修正后的投影元数据."""
    prop_id = text_value(prop.get("propId"))
    normalized_type = normalize_property_type(property_type)
    access = normalize_property_access(prop.get("access"), prop.get("operators"))
    kind = _property_kind(
        component,
        prop_id=prop_id,
        property_type=normalized_type,
        access=access,
    )
    return YeelightPropertyCorrection(
        kind=kind,
        property_type=normalized_type,
        format=normalize_property_format(prop.get("format")),
        access=access,
        runtime_filtered=should_filter_runtime_component(component)
        or kind in RUNTIME_FILTERED_KINDS,
    )


def summarize_product_schema_corrections(schema: Mapping[str, Any]) -> dict[str, int]:
    """聚合原始 product schema 的 correction 结果."""
    components = _iter_schema_components(schema)
    if not components:
        return YeelightSpecCorrectionSummary().as_dict()

    components_seen = 0
    properties_seen = 0
    runtime_filtered = 0
    normalized_format = 0
    writable = 0
    readonly = 0

    for component in components:
        components_seen += 1
        for prop in _iter_component_properties(component):
            correction = correct_property_schema(
                component,
                prop,
                property_type=normalize_source_property_type(prop.get("type")),
            )
            properties_seen += 1
            if correction.format == "boolean":
                normalized_format += 1
            if correction.runtime_filtered:
                runtime_filtered += 1
                continue
            if correction.access == "read_write":
                writable += 1
            elif correction.access == "read_only":
                readonly += 1

    return YeelightSpecCorrectionSummary(
        components_seen=components_seen,
        properties_seen=properties_seen,
        runtime_filtered_properties=runtime_filtered,
        normalized_format_properties=normalized_format,
        writable_properties=writable,
        readonly_properties=readonly,
    ).as_dict()


def should_filter_runtime_component(component: Mapping[str, Any] | None) -> bool:
    """判断组件是否应从运行时实体状态中排除."""
    if component is None:
        return False
    return normalize_component_type(component.get("type")) == "global"


def derive_component_capabilities(component: Mapping[str, Any]) -> list[str]:
    """从修正后的组件属性与动作中派生能力标识."""
    category = text_value(component.get("category"))
    capabilities: list[str] = []
    if category:
        capabilities.append(category)

    for prop in component.get("properties") or []:
        if not isinstance(prop, Mapping):
            continue
        correction = correct_property_schema(
            component,
            prop,
            property_type=normalize_source_property_type(prop.get("type")),
        )
        if correction.kind != "control":
            continue
        prop_id = text_value(prop.get("propId"))
        token = f"{category}.{prop_id}" if category else prop_id
        if token and token not in capabilities:
            capabilities.append(token)

    for action in component.get("supportActions") or []:
        if not isinstance(action, Mapping):
            continue
        action_name = text_value(action.get("actionName"))
        if action_name and action_name not in capabilities:
            capabilities.append(action_name)

    return capabilities


def _property_kind(
    component: Mapping[str, Any] | None,
    *,
    prop_id: str | None,
    property_type: str | None,
    access: str,
) -> str:
    """推断属性语义类别."""
    normalized_prop_id = _normalized_prop_id(prop_id)
    if normalized_prop_id in SENSITIVE_PROPERTY_IDS:
        return "config"
    if normalized_prop_id in INFO_PROPERTY_IDS:
        return "info"
    if normalized_prop_id in CONFIG_PROPERTY_IDS or property_type == "config":
        return "config"
    if should_filter_runtime_component(component):
        return "info"
    if access != "read_write":
        return "state"
    return "control"


def _iter_schema_components(schema: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """遍历 product schema 的组件列表."""
    components: list[Mapping[str, Any]] = []
    for key in ("components", "customComponents"):
        raw_components = schema.get(key)
        if not isinstance(raw_components, list):
            continue
        components.extend(item for item in raw_components if isinstance(item, Mapping))
    return components


def _iter_component_properties(component: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """遍历 component 的属性列表."""
    properties = component.get("properties")
    if not isinstance(properties, list):
        return ()
    return (item for item in properties if isinstance(item, Mapping))


def _normalized_prop_id(value: str | None) -> str | None:
    """返回属性 ID 的大小写无关匹配键."""
    return value.lower() if value is not None else None


__all__ = [
    "YeelightPropertyCorrection",
    "YeelightSpecCorrectionSummary",
    "correct_property_schema",
    "derive_component_capabilities",
    "normalize_component_type",
    "normalize_property_access",
    "normalize_property_format",
    "normalize_property_operators",
    "normalize_property_type",
    "normalize_source_property_type",
    "should_filter_runtime_component",
    "summarize_product_schema_corrections",
]
