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
    category = infer_iot_category(payload)
    model = friendly_model_name(payload)
    if model and not is_generic_model_label(model):
        return model

    if category:
        fallback_model = friendly_specific_model_name(payload)
        if fallback_model and not is_generic_model_label(fallback_model):
            return fallback_model

    if category in _CATEGORY_LABELS:
        return _CATEGORY_LABELS[category]

    platform = platform_for_category(category)
    if platform in _PLATFORM_LABELS and platform not in {"binary_sensor", "sensor"}:
        return _PLATFORM_LABELS[platform]
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

    if is_generic_model_label(current_model):
        return "易来照明设备" if _looks_like_light_device_info(device_info) else "Yeelight Pro 设备"
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


def _looks_like_light_device_info(device_info: Mapping[str, Any]) -> bool:
    text = " ".join(
        value
        for value in (
            _first_text(device_info, ("model", "modelName", "productName")),
            _first_text(device_info, ("name", "deviceName", "device_name", "n")),
        )
        if value
    )
    return "灯" in text or "light" in text.lower()
