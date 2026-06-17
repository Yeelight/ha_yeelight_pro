"""Structural whole-device model labels for Yeelight runtime payloads."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from ..utils import to_str
from .device_runtime_capabilities import normalize_iot_category

_STRUCTURAL_COMPONENT_MODEL_LABELS = {
    "air_conditioner": "空调控制器",
    "air conditioner": "空调控制器",
    "空调": "空调控制器",
    "curtain": "窗帘",
    "zebra_blinds": "窗帘",
    "zebra blinds": "窗帘",
    "梦幻帘": "窗帘",
    "temp_control": "温控器",
    "temp control": "温控器",
    "温控器组件": "温控器",
    "fresh_air": "新风控制器",
    "fresh air": "新风控制器",
    "新风": "新风控制器",
    "floor_heating": "地暖控制器",
    "floor heating": "地暖控制器",
    "地暖": "地暖控制器",
    "hvac_gateway": "HVAC网关",
    "hvac gateway": "HVAC网关",
    "HVAC网关": "HVAC网关",
    "wifi_screen": "全面屏",
    "wifi screen": "全面屏",
    "wifi屏组件": "全面屏",
    "mesh_screen": "全面屏",
    "mesh screen": "全面屏",
    "mesh屏组件": "全面屏",
    "panorama_screen": "全景屏",
    "panorama screen": "全景屏",
    "全景屏组件": "全景屏",
    "smart_screen": "智慧屏",
    "smart screen": "智慧屏",
    "智慧屏组件": "智慧屏",
    "knob_screen": "旋钮屏",
    "knob screen": "旋钮屏",
    "旋钮屏组件": "旋钮屏",
}

_DISPLAY_COMPONENT_LABELS = {
    "human_sensor": "人体传感器",
    "human sensor": "人体传感器",
    "human_detection_sensor": "人体传感器",
    "human detection sensor": "人体传感器",
    "human_illuminance_sensor": "人体传感器",
    "human illuminance sensor": "人体传感器",
    "light_sensor": "照度传感器",
    "light sensor": "照度传感器",
    "illuminance": "照度传感器",
    "contact_sensor": "门磁传感器",
    "contact sensor": "门磁传感器",
}

_STRUCTURAL_COMPONENT_IDS = {
    19: "空调控制器",
    42: "新风控制器",
    43: "地暖控制器",
    55: "HVAC网关",
    56: "全面屏",
    57: "全面屏",
    61: "旋钮屏",
    62: "全景屏",
    63: "温控器",
    75: "智慧屏",
}

_COMPOSITE_CONTROL_CATEGORIES = {
    "human_sensor",
    "light_sensor",
    "contact_sensor",
    "scene_panel",
    "knob_switch",
}

_DISPLAY_NAME_MODEL_LABELS = (
    ("旋钮屏", "旋钮屏"),
    ("全景屏", "全景屏"),
    ("智慧屏", "智慧屏"),
    ("全面屏", "全面屏"),
    ("knob screen", "旋钮屏"),
    ("panorama screen", "全景屏"),
    ("smart screen", "智慧屏"),
    ("wifi screen", "全面屏"),
    ("mesh screen", "全面屏"),
)

_DISPLAY_NAME_KEYS = ("name", "deviceName", "device_name", "n")

_WEAK_DISPLAY_MODEL_LABELS = {
    "",
    "light",
    "relay_switch",
    "switch",
    "开关",
    "开关灯",
    "开关控制器",
    "亮度灯",
    "色温灯",
    "彩光灯",
    "灯具",
    "继电器开关",
    "控制",
    "设备",
    "易来设备",
    "智能设备",
}


def structural_model_label(payload: Mapping[str, Any]) -> str | None:
    """Return a whole-device model label when component structure proves it."""
    return _structural_component_model_label(payload) or _composite_component_model_label(
        payload
    )


def structural_component_label(component: Mapping[str, Any]) -> str | None:
    """Return a user-facing label for documented structural components."""
    return _structural_component_label(component) or _display_component_label(component)


def display_structural_model_label(payload: Mapping[str, Any]) -> str | None:
    """Return a registry-display-only structure label from official screen words."""
    return structural_model_label(payload) or _name_structural_model_label(payload)


def is_weak_display_model_label(value: Any) -> bool:
    """Return true for model labels inferred only from simple control capability."""
    text = _text(value)
    if text is None:
        return True
    normalized = text.strip().casefold()
    canonical = normalized.replace("-", "_").replace(" ", "_")
    return normalized in _WEAK_DISPLAY_MODEL_LABELS or canonical in _WEAK_DISPLAY_MODEL_LABELS


def component_categories(payload: Mapping[str, Any]) -> Iterable[str]:
    """Yield normalized component categories from runtime/schema payloads."""
    for component in _all_components(payload):
        category = _category_text(component.get("category"))
        if category:
            yield category


def _structural_component_model_label(payload: Mapping[str, Any]) -> str | None:
    """Return a whole-device label from documented global screen components."""
    for component in _all_components(payload):
        if label := _structural_component_label(component):
            return label
    return None


def _structural_component_label(component: Mapping[str, Any]) -> str | None:
    cid = _component_numeric_id(component)
    if cid in _STRUCTURAL_COMPONENT_IDS:
        return _STRUCTURAL_COMPONENT_IDS[cid]
    for key in (
        "component_id",
        "componentId",
        "alias",
        "name",
        "desc",
        "category",
        "component_type",
        "componentType",
        "component",
        "componentName",
    ):
        text = _text(component.get(key))
        if not text:
            continue
        normalized = text.strip().lower().replace("-", "_")
        label = _STRUCTURAL_COMPONENT_MODEL_LABELS.get(normalized)
        if label is not None:
            return label
        label = _STRUCTURAL_COMPONENT_MODEL_LABELS.get(text.strip())
        if label is not None:
            return label
    return None


def _display_component_label(component: Mapping[str, Any]) -> str | None:
    """Return a component-only display label that must not imply whole-device type."""
    for key in (
        "component_id",
        "componentId",
        "alias",
        "name",
        "desc",
        "category",
        "component_type",
        "componentType",
        "component",
        "componentName",
    ):
        text = _text(component.get(key))
        if not text:
            continue
        normalized = text.strip().lower().replace("-", "_")
        label = _DISPLAY_COMPONENT_LABELS.get(normalized)
        if label is not None:
            return label
        label = _DISPLAY_COMPONENT_LABELS.get(text.strip())
        if label is not None:
            return label
    return None


def _composite_component_model_label(payload: Mapping[str, Any]) -> str | None:
    """Return a conservative label for documented mixed sensor/control devices."""
    categories = {
        category
        for category in component_categories(payload)
        if category and category not in {"other", "gateway"}
    }
    if "relay_switch" in categories and categories & _COMPOSITE_CONTROL_CATEGORIES:
        return "复合控制器"
    return None


def _name_structural_model_label(payload: Mapping[str, Any]) -> str | None:
    for key in _DISPLAY_NAME_KEYS:
        text = _text(payload.get(key))
        if not text:
            continue
        normalized = text.casefold()
        for marker, label in _DISPLAY_NAME_MODEL_LABELS:
            if marker.casefold() in normalized:
                return label
    return None


def _component_numeric_id(component: Mapping[str, Any]) -> int | None:
    for key in ("cid", "componentId", "component_id"):
        value = component.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        if isinstance(value, str) and value.strip().isdecimal():
            return int(value.strip())
    return None


def _all_components(payload: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    for subdevice in _property_rows(payload.get("subDeviceList")):
        yield subdevice
    schema = payload.get("product_schema")
    if isinstance(schema, Mapping):
        for component in _schema_components(schema):
            yield component
    product_model = payload.get("ha_product_model")
    if isinstance(product_model, Mapping):
        for component in _property_rows(product_model.get("components")):
            yield component


def _schema_components(schema: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    components: list[Mapping[str, Any]] = []
    for key in ("components", "customComponents"):
        components.extend(_property_rows(schema.get(key)))
    return components


def _property_rows(value: Any) -> list[Mapping[str, Any]]:
    return [item for item in value or [] if isinstance(item, Mapping)]


def _text(value: Any) -> str | None:
    return to_str(value)


def _category_text(value: Any) -> str | None:
    return normalize_iot_category(value)


__all__ = [
    "component_categories",
    "display_structural_model_label",
    "is_weak_display_model_label",
    "structural_component_label",
    "structural_model_label",
]
