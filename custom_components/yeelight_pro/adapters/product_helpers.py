"""Helper functions for Yeelight product schema adapters."""

from __future__ import annotations

import re
from typing import Any, Mapping

from ..capabilities.spec_correction import normalize_component_type
from ..utils import normalize_unit as normalize_shared_unit
from ..utils import normalize_scale as normalize_shared_scale
from ..utils import normalize_zoom as normalize_shared_zoom
from ..utils import to_int
from .models import (
    SourceComponentInput,
    SourceValueItemInput,
    SourceValueRangeInput,
)


def adapt_value_range(payload: Mapping[str, Any] | None) -> SourceValueRangeInput | None:
    """适配数值范围元数据。"""
    if not payload:
        return None
    minimum = to_int(payload.get("min"))
    maximum = to_int(payload.get("max"))
    step = to_int(payload.get("step"))
    if minimum is None and maximum is None and step is None:
        return None
    return SourceValueRangeInput(
        min=minimum,
        max=maximum,
        step=step,
    )


def adapt_value_list(payload: Any) -> list[SourceValueItemInput]:
    """适配枚举值列表。"""
    items: list[SourceValueItemInput] = []
    seen_codes: set[str] = set()
    for item in payload or []:
        if not isinstance(item, Mapping):
            continue
        code = string(item.get("code"))
        if code is None or code in seen_codes:
            continue
        seen_codes.add(code)
        items.append(
            SourceValueItemInput(
                code=code,
                desc=string(item.get("desc")),
            )
        )
    return items


def collect_categories(components: list[SourceComponentInput]) -> list[str]:
    """收集组件中不重复的类别列表。"""
    categories: list[str] = []
    for component in components:
        if component.category and component.category not in categories:
            categories.append(component.category)
    return categories


def build_model_id(pid: Any) -> str | None:
    """根据产品 ID 构建模型标识。"""
    return f"YL-{pid}" if pid is not None else None


def build_component_key(
    component: Mapping[str, Any],
    *,
    base_name: str,
    duplicate_count: int,
    occurrence: int,
) -> str:
    """构建组件唯一键，处理同名组件的歧义。"""
    index = component.get("index")
    if duplicate_count <= 1:
        return base_name
    if index is not None:
        return f"{base_name}_{index}"
    return f"{base_name}_{occurrence}"


def component_base_name(component: Mapping[str, Any]) -> str:
    """提取组件的 slug 化基础名称。"""
    category = string(component.get("category"))
    component_type = normalize_component_type(component.get("type"))
    if category:
        base = slugify(category)
    else:
        base = slugify(component.get("name")) or slugify(component.get("desc"))
    if not base:
        base = f"component_{component.get('cid', 'unknown')}"
    if component_type == "global" and not base.endswith("_global"):
        if base == "basic":
            return base
        return f"{base}_global"
    return base


def merge_components(*sources: Any) -> list[Mapping[str, Any]]:
    """合并多个组件来源并按身份去重。"""
    merged: list[Mapping[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()

    for source in sources:
        for item in source or []:
            if not isinstance(item, Mapping):
                continue
            identity = (
                item.get("cid"),
                item.get("index"),
                item.get("type"),
                string(item.get("category")),
                string(item.get("name")),
            )
            if identity in seen:
                continue
            seen.add(identity)
            merged.append(item)

    return merged


def normalize_protocol(value: Any) -> str | None:
    """将协议描述标准化为小写标识。"""
    text = (string(value) or "").lower()
    if "matter" in text:
        return "matter"
    if "mesh" in text:
        return "mesh"
    if "thread" in text:
        return "thread"
    return text or None


def normalized_unit(value: Any) -> str | None:
    """标准化单位字符串。"""
    return normalize_shared_unit(value)


def normalized_scale(value: Any) -> int:
    """标准化 Yeelight 物模型缩放比例元数据。"""
    return normalize_shared_scale(value)


def normalized_zoom(value: Any) -> int:
    """标准化 Yeelight 物模型缩放方向元数据。"""
    return normalize_shared_zoom(value)


def slugify(value: Any) -> str:
    """将任意文本转换为小写下划线 slug。"""
    text = string(value)
    if not text:
        return ""
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", text.lower())).strip("_")


def string(value: Any) -> str | None:
    """将值安全转换为非空字符串或 None。"""
    if value is None:
        return None
    text = str(value).strip()
    return text or None
