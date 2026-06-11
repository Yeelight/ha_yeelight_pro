"""User-facing display helpers for Yeelight Pro devices and channels."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .capabilities.registry import platform_for_category
from .core.device_classification import (
    friendly_model_name,
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
    "other": "易来设备",
}
_CATEGORY_TYPE_LABELS = {
    **_CATEGORY_LABELS,
    "binary_sensor": "易来传感设备",
    "light": "易来照明设备",
    "relay_switch": "易来开关设备",
    "sensor": "易来传感设备",
    "temp_control": "易来温控设备",
    "other": "易来扩展设备",
}
_PLATFORM_LABELS = {
    "binary_sensor": "二元传感器",
    "climate": "温控",
    "cover": "窗帘",
    "event": "事件",
    "fan": "风扇",
    "light": "灯",
    "sensor": "传感器",
    "switch": "开关",
}
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

    category = infer_iot_category(payload)
    if category in _CATEGORY_TYPE_LABELS:
        return _CATEGORY_TYPE_LABELS[category]

    platform = platform_for_category(category)
    if platform in _PLATFORM_LABELS and platform not in {"binary_sensor", "sensor"}:
        return _PLATFORM_LABELS[platform]
    model = friendly_model_name(payload)
    if model and not is_generic_model_label(model):
        return model
    return None


def device_model_name(payload: Mapping[str, Any]) -> str:
    """Return model text that avoids broad HA platform/category labels."""
    friendly = friendly_specific_model_name(payload)
    if friendly:
        return friendly
    explicit = _specific_text(payload, _MODEL_NAME_KEYS)
    if explicit is not None:
        return explicit
    return friendly


def registry_model_value(
    device_info: Mapping[str, Any],
    current_model: Any,
) -> str | None:
    """Return a HA registry-safe model value, replacing broad fallback labels."""
    model = device_info.get("model")
    if model is not None and not is_generic_model_label(model):
        return str(model)

    inferred = device_model_name(device_info)
    if inferred and not is_generic_model_label(inferred):
        return inferred

    if model is None:
        return str(current_model) if current_model is not None else None
    if is_generic_model_label(current_model):
        if category_model := _category_model_value(device_info):
            return category_model
        return "Yeelight Pro 设备"
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
    return f"{device_name} {suffix}"


def switch_channel_count_hint(payload: Mapping[str, Any]) -> int | None:
    """Return product-name channel count hints such as 双键/三键."""
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
    if category in _CATEGORY_TYPE_LABELS:
        return _CATEGORY_TYPE_LABELS[category]
    model = _first_text(device_info, ("model", "modelName", "productName"))
    if model is None:
        return None
    generic_payload = {"category": model}
    category = infer_iot_category(generic_payload)
    if category in _CATEGORY_TYPE_LABELS:
        return _CATEGORY_TYPE_LABELS[category]
    return None
