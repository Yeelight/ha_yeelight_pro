"""Runtime classification helpers for Yeelight Open API device rows."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from ..capabilities.platform_contract import primary_platform_for_payload
from ..capabilities.registry import (
    is_iot_category,
    parse_component_property_key,
    product_category_candidates,
)
from ..utils import to_str
from .device_classification_categories import BROAD_CATEGORIES, GENERIC_PLATFORM_CATEGORIES
from .device_runtime_capabilities import (
    LIGHT_SENSOR_CONFIG_PROPS,
    category_from_property_keys,
    infer_runtime_iot_category,
    normalize_iot_category,
    runtime_property_keys,
)
from .device_structural_models import (
    component_categories,
    is_weak_display_model_label,
    structural_model_label,
)

GENERIC_MODEL_LABELS = frozenset({
    "",
    "binary_sensor",
    "climate",
    "contact_sensor",
    "cover",
    "curtain",
    "event",
    "fan",
    "gateway",
    "human_sensor",
    "knob_switch",
    "light",
    "light_sensor",
    "lock",
    "other",
    "relay_switch",
    "scene_panel",
    "sensor",
    "switch",
    "temp_control",
    "yeelight pro 设备",
    "yeelight_pro_设备",
    "二元传感器",
    "事件",
    "传感器",
    "开关",
    "情景面板",
    "控制",
    "易来设备",
    "智能设备",
    "温控",
    "温控设备",
    "灯",
    "灯具",
    "窗帘",
    "继电器开关",
    "网关",
    "设备",
    "风扇",
})

_CATEGORY_LABELS = {
    "binary_sensor": "二元传感器",
    "light": "灯具",
    "sensor": "传感器",
    "relay_switch": "继电器开关",
    "contact_sensor": "门磁传感器",
    "human_sensor": "人体传感器",
    "light_sensor": "照度传感器",
    "curtain": "窗帘",
    "temp_control": "温控设备",
    "scene_panel": "情景面板",
    "knob_switch": "旋钮开关",
    "gateway": "网关",
    "other": "易来设备",
}

_BROAD_CATEGORY_MODEL_LABELS = frozenset({
    "二元传感器",
    "灯具",
    "传感器",
    "继电器开关",
    "温控设备",
    "易来设备",
})

def infer_iot_category(payload: Mapping[str, Any]) -> str | None:
    """Infer a Yeelight IoT category from documented category/property evidence."""
    current = _category_text(payload.get("category")) or _category_text(payload.get("type"))
    runtime_category = infer_runtime_iot_category(payload)
    if runtime_category is not None:
        return runtime_category

    component_category = _category_from_components(payload)
    if component_category is not None:
        return component_category

    prop_category = _category_from_props(_property_keys(payload))
    if prop_category is not None:
        return prop_category

    product_category = _category_from_product_catalog(payload)
    if product_category is not None:
        return product_category

    if current and current not in BROAD_CATEGORIES:
        return current

    if current in GENERIC_PLATFORM_CATEGORIES:
        return None
    if current == "switch":
        return None
    if current in BROAD_CATEGORIES:
        return None if current == "" else current
    return current or None


def infer_specific_iot_category(payload: Mapping[str, Any]) -> str | None:
    """Infer the most specific category from properties while preserving broad category."""
    return infer_iot_category(payload)


def ha_platform_for_payload(payload: Mapping[str, Any]) -> str | None:
    """Return the HA primary platform implied by a Yeelight payload."""
    return primary_platform_for_payload(payload)


def friendly_model_name(payload: Mapping[str, Any]) -> str:
    """Return a user-facing product/model label for HA's device registry."""
    explicit = _first_text(
        payload,
        (
            "productName",
            "product_name",
            "modelName",
            "model_name",
            "deviceModel",
        ),
    )
    if explicit and not is_generic_model_label(explicit):
        return explicit

    structural_label = structural_model_label(payload)
    if structural_label is not None:
        return structural_label

    explicit = _first_text(payload, ("model",))
    if (
        explicit
        and not is_generic_model_label(explicit)
        and not is_weak_display_model_label(explicit)
    ):
        return explicit

    property_label = _property_model_label(payload, runtime_property_keys(payload))
    if property_label is not None:
        return property_label

    schema_name = _schema_model_name(payload)
    if schema_name:
        return schema_name

    property_label = _property_model_label(payload, _property_keys(payload))
    if property_label is not None:
        return property_label

    category = infer_iot_category(payload)
    if category in _CATEGORY_LABELS:
        return _CATEGORY_LABELS[category]
    return "易来设备"


def friendly_specific_model_name(payload: Mapping[str, Any]) -> str:
    """Return a registry-safe model label that is never a broad category word."""
    model = friendly_model_name(payload)
    if model not in _BROAD_CATEGORY_MODEL_LABELS:
        return model
    return ""


def friendly_model_id(payload: Mapping[str, Any]) -> str:
    """Return a stable model id without falling back to broad HA platforms."""
    if pid := _first_text(payload, ("pid", "productId", "product_id")):
        model_id = _first_text(payload, ("model_id", "modelId"))
        if model_id is None or model_id.startswith("runtime-"):
            return f"YL-{pid}"
    if model_id := _first_text(payload, ("model_id", "modelId")):
        return model_id
    if pid:
        return f"YL-{pid}"
    category = infer_iot_category(payload) or "device"
    return f"runtime-{category}"


def is_generic_model_label(value: Any) -> bool:
    """Return true for broad HA platform/category labels, not product models."""
    text = _text(value)
    if text is None:
        return False
    normalized = text.strip().lower()
    canonical = normalized.replace("-", "_").replace(" ", "_")
    return normalized in GENERIC_MODEL_LABELS or canonical in GENERIC_MODEL_LABELS


def _category_from_props(keys: set[str]) -> str | None:
    return category_from_property_keys(keys)


def _property_model_label(payload: Mapping[str, Any], keys: set[str]) -> str | None:
    """Return a concrete model label only from property evidence."""
    component_category = _category_from_components(payload)
    if component_category == "relay_switch" and keys & {"p", "sp"}:
        return "开关控制器"
    category = _category_from_props(runtime_property_keys(payload)) or _category_from_props(keys)
    category = category or _category_text(payload.get("category")) or _category_text(payload.get("type"))
    if keys & LIGHT_SENSOR_CONFIG_PROPS and keys & {"luminance", "mv"}:
        return "照度传感器"
    if keys & {"dc"}:
        return "门磁传感器"
    if keys & {"mv"}:
        return "人体传感器"
    if keys & {"cp", "tp", "rd"}:
        return "窗帘"
    if keys & {"acp", "acm", "actt", "acct", "acf", "aco", "acdfltr"}:
        return "空调控制器"
    if keys & {"rfhp", "rfhct", "rfhtt"}:
        return "地暖控制器"
    if keys & {"vmcp", "vmcf"}:
        return "新风控制器"
    if keys & {"bhm", "do", "ve", "tgt", "fa", "he"}:
        return "温控器"
    if (keys & {"t", "temp"}) and keys & {"h"}:
        return "温湿度传感器"
    if keys & {"t", "temp"}:
        return "温度传感器"
    if keys & {"h"}:
        return "湿度传感器"
    if keys & {"luminance", "level"}:
        return "照度传感器"
    if category == "light":
        if keys & {"c"}:
            return "彩光灯"
        if keys & {"ct"}:
            return "色温灯"
        if keys & {"l"}:
            return "亮度灯"
        if keys & {"p"}:
            return "开关灯"
    if category in {"relay_switch", "switch"} and keys & {"p", "sp"}:
        return "开关控制器"
    return None


def _property_keys(payload: Mapping[str, Any]) -> set[str]:
    keys: set[str] = set()
    keys.update(_params(payload))
    for prop in _property_rows(payload.get("properties")):
        keys.add(_prop_name(_property_id(prop)))
    for subdevice in _property_rows(payload.get("subDeviceList")):
        for prop in _property_rows(subdevice.get("properties")):
            keys.add(_prop_name(_property_id(prop)))
    keys.update(_product_model_property_keys(payload.get("ha_product_model")))
    keys.update(_schema_property_keys(payload.get("product_schema")))
    keys.discard("")
    return keys


def _category_from_components(payload: Mapping[str, Any]) -> str | None:
    categories = [
        category
        for category in _component_categories(payload)
        if is_iot_category(category) and category not in {"light", "switch", "other"}
    ]
    specific_categories = [
        category for category in categories if category != "relay_switch"
    ]
    for category in specific_categories:
        return category
    if categories and set(categories) == {"relay_switch"}:
        return "relay_switch"
    return None


def _category_from_product_catalog(payload: Mapping[str, Any]) -> str | None:
    """Return a category from documented product composition only as fallback."""
    categories = product_category_candidates(payload.get("pid"))
    if len(categories) != 1:
        return None
    category = categories[0]
    if is_iot_category(category) and category != "other":
        return category
    return None


def _component_categories(payload: Mapping[str, Any]) -> Iterable[str]:
    yield from component_categories(payload)


def _params(payload: Mapping[str, Any]) -> dict[str, Any]:
    raw_params = payload.get("params")
    return dict(raw_params) if isinstance(raw_params, Mapping) else {}


def _schema_model_name(payload: Mapping[str, Any]) -> str | None:
    schema = payload.get("product_schema")
    if not isinstance(schema, Mapping):
        return None
    model = _first_text(
        schema,
        ("productName", "product_name", "name", "modelName", "model_name", "model"),
    )
    if model is None or is_generic_model_label(model):
        return None
    return model


def _product_model_property_keys(value: Any) -> set[str]:
    if not isinstance(value, Mapping):
        return set()
    keys: set[str] = set()
    for component in _property_rows(value.get("components")):
        if not _category_text(component.get("category")):
            continue
        for prop in _property_rows(component.get("properties")):
            keys.add(_prop_name(_property_id(prop)))
    return keys


def _schema_property_keys(value: Any) -> set[str]:
    if not isinstance(value, Mapping):
        return set()
    keys: set[str] = set()
    for component in _schema_components(value):
        if not _category_text(component.get("category")):
            continue
        for prop in _property_rows(component.get("properties")):
            keys.add(_prop_name(_property_id(prop)))
    return keys


def _schema_components(schema: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    components: list[Mapping[str, Any]] = []
    for key in ("components", "customComponents"):
        components.extend(_property_rows(schema.get(key)))
    return components


def _property_rows(value: Any) -> list[Mapping[str, Any]]:
    return [item for item in value or [] if isinstance(item, Mapping)]


def _property_id(prop: Mapping[str, Any]) -> Any:
    return prop.get("prop_id", prop.get("propId", prop.get("propName")))


def _prop_name(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    try:
        return parse_component_property_key(text).prop_name
    except ValueError:
        return text


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        if value := _text(payload.get(key)):
            return value
    return None


def _text(value: Any) -> str | None:
    return to_str(value)


def _category_text(value: Any) -> str | None:
    return normalize_iot_category(value)

__all__ = [
    "friendly_model_id",
    "friendly_model_name",
    "friendly_specific_model_name",
    "ha_platform_for_payload",
    "infer_iot_category",
    "infer_specific_iot_category",
    "is_generic_model_label",
    "structural_model_label",
]
