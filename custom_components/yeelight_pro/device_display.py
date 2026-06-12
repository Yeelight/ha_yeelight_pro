"""User-facing display helpers for Yeelight Pro devices and channels."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .core.device_classification import (
    friendly_specific_model_name,
    infer_iot_category,
    is_generic_model_label,
)
from . import device_channels
from .utils import to_str

_CATEGORY_LABELS = {
    "light": "灯具",
    "contact_sensor": "门磁传感器",
    "human_sensor": "人体传感器",
    "light_sensor": "照度传感器",
    "curtain": "窗帘",
    "temp_control": "温控设备",
    "relay_switch": "继电器开关",
    "scene_panel": "情景面板",
    "knob_switch": "旋钮开关",
    "gateway": "网关",
    "other": "其他设备",
}
_CATEGORY_MODEL_LABELS = frozenset(_CATEGORY_LABELS.values())
_MODEL_NAME_KEYS = (
    "productName",
    "product_name",
    "modelName",
    "model_name",
    "model",
)


def device_name_label(payload: Mapping[str, Any], fallback_id: str) -> str:
    """Return a stable device label for forms without exposing raw payloads."""
    return (
        _first_text(payload, ("name", "deviceName", "device_name", "n"))
        or f"Device {fallback_id}"
    )


def device_type_label(payload: Mapping[str, Any]) -> str | None:
    """Return a user-facing model/category/platform summary for picker details."""
    explicit = _specific_text(payload, _MODEL_NAME_KEYS)
    if explicit is not None:
        return explicit

    model = friendly_specific_model_name(payload)
    if model and not is_generic_model_label(model):
        return model

    category = infer_iot_category(payload)
    return _CATEGORY_LABELS.get(category) if category is not None else None


def device_model_name(payload: Mapping[str, Any]) -> str:
    """Return concrete model text, with category as the final documented fallback."""
    friendly = friendly_specific_model_name(payload)
    if friendly:
        return friendly
    explicit = _specific_text(payload, _MODEL_NAME_KEYS)
    if explicit is not None:
        return explicit
    category = infer_iot_category(payload)
    return _CATEGORY_LABELS.get(category, "") if category is not None else ""


def registry_model_value(
    device_info: Mapping[str, Any],
    current_model: Any,
) -> str | None:
    """Return a HA registry-safe model value, replacing broad fallback labels."""
    model = device_info.get("model")
    if model is not None:
        model_text = str(model)
        if not is_generic_model_label(model) or model_text in _CATEGORY_MODEL_LABELS:
            return model_text

    inferred = device_model_name(device_info)
    if inferred and not is_generic_model_label(inferred):
        return inferred

    if model is None:
        if current_model is not None and not is_generic_model_label(current_model):
            return str(current_model)
        return None
    if is_generic_model_label(current_model):
        return _category_model_value(device_info)
    return None


def channel_name_label(
    *,
    index: int | None,
    component: Any | None = None,
    device_payload: Mapping[str, Any] | None = None,
) -> str | None:
    """Return a readable sub-entity label for indexed controls."""
    return device_channels.channel_name_label(
        index=index,
        component=component,
        device_payload=device_payload,
    )


def suggested_entity_object_id(
    payload: Mapping[str, Any] | None,
    *,
    entity_name: Any = None,
    fallback_id: Any = None,
) -> str | None:
    """Return a friendly HA object-id seed for device-backed entities."""
    if not isinstance(payload, Mapping):
        return None

    fallback_text = _first_text(payload, ("device_id", "id", "did")) or _text(fallback_id)
    if fallback_text is None:
        return None

    device_name = device_name_label(payload, fallback_text)
    suffix = _text(entity_name)
    if suffix is None or suffix == "照明":
        return device_name
    if suffix in device_name:
        return device_name
    if device_name in suffix:
        return suffix
    return f"{device_name} {suffix}"


def switch_channel_count_hint(payload: Mapping[str, Any]) -> int | None:
    """Return channel count from official product/runtime capability evidence."""
    return device_channels.switch_channel_count_hint(payload)


def _specific_text(
    payload: Mapping[str, Any],
    keys: tuple[str, ...],
) -> str | None:
    value = _first_text(payload, keys)
    if value is None or is_generic_model_label(value):
        return None
    return value


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        if value := to_str(payload.get(key)):
            return value
    return None


def _text(value: Any) -> str | None:
    text = to_str(value)
    return text or None


def _category_model_value(device_info: Mapping[str, Any]) -> str | None:
    category = infer_iot_category(device_info)
    return _CATEGORY_LABELS.get(category) if category is not None else None
