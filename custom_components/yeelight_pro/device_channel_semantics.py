"""Channel input/output semantics for Yeelight Pro component labels."""

from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any

from .utils import to_str

OUTPUT_CHANNEL_CATEGORIES = {"relay_switch", "switch"}
EVENT_INPUT_CATEGORIES = {"scene_panel", "knob_switch"}
OUTPUT_COMPONENT_KEYS = {
    "switch",
    "switch control",
    "relay switch",
    "relay_switch",
    "开关",
}
EVENT_INPUT_COMPONENT_KEYS = {
    "button",
    "key",
    "knob switch",
    "scene button",
    "scene_button",
    "scene control button",
    "scene_control_button",
    "dali scene control button",
    "dali_scene_control_button",
    "wireless switch channel",
    "wireless_switch_channel",
    "情景按键",
    "无线开关通道",
    "旋钮开关",
}
OUTPUT_IO_TYPES = {"output", "out", "输出"}
INPUT_IO_TYPES = {"input", "in", "输入"}
COMPONENT_INDEX_SUFFIX_RE = re.compile(r"_(?P<index>\d+)$")


def uses_output_channel_label(
    component: Any | None,
    device_payload: Mapping[str, Any] | None,
) -> bool:
    """Return true when the channel is an output relay path, not an input key."""
    io_type = _io_type(component)
    if io_type in INPUT_IO_TYPES:
        return False
    if io_type in OUTPUT_IO_TYPES:
        return True
    component_key = _component_identity_key(component)
    if component_key in EVENT_INPUT_COMPONENT_KEYS:
        return False
    component_category = _category_from_component(component)
    if component_category in EVENT_INPUT_CATEGORIES:
        return False
    if component_category in OUTPUT_CHANNEL_CATEGORIES:
        return True
    if component_key in OUTPUT_COMPONENT_KEYS:
        return True
    payload_category = _category_from_payload(device_payload)
    if payload_category in EVENT_INPUT_CATEGORIES:
        return False
    if payload_category in OUTPUT_CHANNEL_CATEGORIES:
        return True
    return component_key in OUTPUT_COMPONENT_KEYS


def is_channel_component(component: Any | None) -> bool:
    """Return true when component metadata represents an input/output channel."""
    if component is None:
        return False
    io_type = _io_type(component)
    if io_type in INPUT_IO_TYPES or io_type in OUTPUT_IO_TYPES:
        return True
    component_category = _category_from_component(component)
    if component_category in EVENT_INPUT_CATEGORIES | OUTPUT_CHANNEL_CATEGORIES:
        return True
    component_key = _component_identity_key(component)
    if component_key in EVENT_INPUT_COMPONENT_KEYS or component_key in OUTPUT_COMPONENT_KEYS:
        return True
    return False


def component_text(component: Any | None, keys: tuple[str, ...]) -> str | None:
    """Return first non-empty text field from mapping/dataclass component metadata."""
    if component is None:
        return None
    for key in keys:
        value = (
            component.get(key)
            if isinstance(component, Mapping)
            else getattr(component, key, None)
        )
        if text := to_str(value):
            return text
    for key in ("component_id", "componentId", "id"):
        value = (
            component.get(key)
            if isinstance(component, Mapping)
            else getattr(component, key, None)
        )
        if text := to_str(value):
            return text
    return None


def component_name_key(value: Any) -> str:
    """Normalize component identity text for exact membership checks."""
    text = to_str(value)
    return text.strip().lower() if text else ""


def _category_from_component(component: Any | None) -> str | None:
    if component is None:
        return None
    for key in ("category", "iot_category", "type"):
        value = (
            component.get(key)
            if isinstance(component, Mapping)
            else getattr(component, key, None)
        )
        if text := to_str(value):
            return _normalized_category(text)
    return None


def _category_from_payload(payload: Mapping[str, Any] | None) -> str | None:
    if payload is None:
        return None
    return _normalized_category(
        _first_text(payload, ("iot_category", "category", "type"))
    )


def _component_identity_key(component: Any | None) -> str:
    key = component_name_key(
        component_text(
            component,
            (
                "component_id",
                "componentId",
                "id",
                "alias",
                "component_alias",
                "name",
                "desc",
            ),
        )
    )
    if key in EVENT_INPUT_COMPONENT_KEYS or key in OUTPUT_COMPONENT_KEYS:
        return key
    without_suffix = COMPONENT_INDEX_SUFFIX_RE.sub("", key)
    if without_suffix in EVENT_INPUT_COMPONENT_KEYS:
        return without_suffix
    return key


def _io_type(component: Any | None) -> str | None:
    value = component_text(component, ("io_type", "ioType", "io"))
    if value is None:
        return None
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def _normalized_category(value: Any) -> str | None:
    text = to_str(value)
    if text is None:
        return None
    category = text.lower().replace("-", "_").replace(" ", "_")
    return "relay_switch" if category == "switch" else category


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        if value := to_str(payload.get(key)):
            return value
    return None


__all__ = [
    "component_name_key",
    "component_text",
    "is_channel_component",
    "uses_output_channel_label",
]
