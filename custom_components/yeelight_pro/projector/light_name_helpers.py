"""Light component naming helpers for Yeelight Pro projections."""

from __future__ import annotations

from ..canonical.models import ComponentInstanceModel
from ..device_channel_generated_names import looks_like_generated_channel_name
from ..device_display import channel_name_label
from ..utils import to_int, to_str
from .common import component_index, humanize_component_id

LIGHT_TECHNICAL_NAME_LABELS = {
    "color temperature light": "色温灯",
    "color light": "彩光灯",
    "brightness light": "亮度灯",
    "dimming light": "亮度灯",
}


def _project_light_name(component: ComponentInstanceModel, *, total: int = 1) -> str | None:
    """从组件 ID 推断灯光显示名称。"""
    friendly_name = _friendly_component_name(component)
    if friendly_name and total > 1:
        return friendly_name

    index = component_index(component.component_id)
    if index is not None:
        return _indexed_channel_name(index, total=total)

    lowered = component.component_id.lower()
    if lowered in {"light", "main", "main_light"}:
        return None
    if lowered.startswith("light_"):
        suffix = lowered.removeprefix("light_").strip("_")
        if suffix.isdigit():
            return _indexed_channel_name(to_int(suffix), total=total)
        return humanize_component_id(suffix)
    if lowered.startswith("light"):
        suffix = lowered.removeprefix("light")
        if suffix.isdigit():
            return _indexed_channel_name(to_int(suffix), total=total)
        return None
    return humanize_component_id(component.component_id)


def _indexed_channel_name(index: int | None, *, total: int) -> str | None:
    """为多路灯光生成稳定的通道名，单路主实体交给设备名承载。"""
    if index is None or total <= 1:
        return None
    return channel_name_label(index=index, component={"io": "output"})


def _friendly_component_name(component: ComponentInstanceModel) -> str | None:
    """返回来自产品 schema 的组件友好名称，过滤技术占位名。"""
    index = component_index(component.component_id)
    for value in (getattr(component, "desc", None), getattr(component, "name", None)):
        text = to_str(value)
        if not text:
            continue
        friendly = text.removesuffix("组件").strip()
        if not friendly:
            continue
        if friendly.lower() in {"light", "main", "main_light"}:
            continue
        if looks_like_generated_channel_name(friendly, index):
            continue
        if label := _technical_light_name_label(friendly):
            return label
        return friendly
    return None


def _technical_light_name_label(value: str) -> str | None:
    """把产品 schema 中常见英文技术组件名转换为本地显示名。"""
    normalized = value.strip().lower().replace("-", " ").replace("_", " ")
    normalized = " ".join(normalized.split())
    return LIGHT_TECHNICAL_NAME_LABELS.get(normalized)
