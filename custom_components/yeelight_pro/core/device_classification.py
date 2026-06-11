"""Runtime classification helpers for Yeelight Open API device rows."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..capabilities.platform_contract import primary_platform_for_payload
from ..utils import to_str
from .device_classification_categories import BROAD_CATEGORIES, CATEGORY_ALIASES

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

_CONTACT_NAME_TOKENS = ("门磁", "门窗", "接触", "contact")
_HUMAN_NAME_TOKENS = ("人体", "人感", "存在", "motion", "presence")
_LIGHT_SENSOR_NAME_TOKENS = ("照度", "光照", "照明传感", "illuminance")
_SAFETY_SENSOR_NAME_TOKENS = (
    "烟雾",
    "烟感",
    "烟雾传感",
    "烟感传感",
    "可燃气",
    "燃气",
    "水浸",
    "漏水",
    "smoke",
    "gas",
    "water leak",
)
_TELEMETRY_SENSOR_NAME_TOKENS = (
    "温湿度",
    "温度传感",
    "湿度传感",
    "temperature sensor",
    "humidity sensor",
)
_CURTAIN_NAME_TOKENS = ("窗帘", "卷帘", "百叶", "电机", "curtain", "blind")
_TEMP_CONTROL_NAME_TOKENS = ("空调", "地暖", "温控", "新风", "climate", "thermostat")
_BATH_HEATER_NAME_TOKENS = ("暖风", "浴霸", "heater", "bath heater")
_SCENE_PANEL_NAME_TOKENS = (
    "全面屏",
    "智慧屏",
    "智能面板",
    "情景面板",
    "控制面板",
    "scene panel",
    "control panel",
)
_SWITCH_NAME_TOKENS = ("开关", "插座", "继电器", "switch", "relay")
_LIGHT_NAME_TOKENS = (
    "灯",
    "射灯",
    "筒灯",
    "灯带",
    "吸顶",
    "泛光",
    "青空",
    "light",
    "lamp",
)

_FRIENDLY_MODEL_PATTERNS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("E20", "射灯"), "E20 射灯"),
    (("单键", "开关"), "单键开关"),
    (("双键", "开关"), "双键开关"),
    (("三键", "开关"), "三键开关"),
    (("四键", "开关"), "四键开关"),
    (("智能", "开关"), "智能开关"),
    (("墙壁", "开关"), "墙壁开关"),
    (("全面屏",), "全面屏面板"),
    (("智慧屏",), "智慧屏面板"),
    (("智能面板",), "智能面板"),
    (("控制面板",), "控制面板"),
    (("窗帘", "电机"), "窗帘电机"),
    (("温控器",), "温控器"),
    (("暖风机",), "暖风机"),
    (("浴霸",), "浴霸"),
    (("温湿度", "传感器"), "温湿度传感器"),
    (("门磁",), "门磁传感器"),
    (("人体",), "人体传感器"),
    (("人感",), "人体传感器"),
    (("烟雾",), "烟雾传感器"),
    (("烟感",), "烟雾传感器"),
    (("燃气",), "燃气传感器"),
    (("水浸",), "水浸传感器"),
    (("漏水",), "水浸传感器"),
    (("照度",), "照度传感器"),
    (("光照",), "照度传感器"),
    (("青空灯",), "青空灯"),
    (("吸顶灯",), "吸顶灯"),
    (("镜前灯",), "镜前灯"),
    (("操作台灯",), "操作台灯"),
    (("衣柜灯",), "衣柜灯"),
    (("主灯",), "主灯"),
    (("床头灯",), "床头灯"),
    (("晾晒灯",), "晾晒灯"),
    (("氛围灯",), "氛围灯"),
    (("感应夜灯",), "感应夜灯"),
    (("夜灯",), "夜灯"),
    (("台灯",), "台灯"),
    (("吊灯",), "吊灯"),
    (("筒灯",), "筒灯"),
    (("射灯",), "射灯"),
    (("灯带",), "灯带"),
)

_CATEGORY_LABELS = {
    "light": "灯具",
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

_BROAD_CATEGORY_MODEL_REPLACEMENTS = {
    "light": "易来照明设备",
    "relay_switch": "易来开关设备",
    "temp_control": "易来温控设备",
    "other": "易来扩展设备",
}
_BROAD_CATEGORY_MODEL_LABELS = frozenset({
    "灯具",
    "继电器开关",
    "温控设备",
    "易来设备",
})


def infer_iot_category(payload: Mapping[str, Any]) -> str | None:
    """Infer a Yeelight IoT category from documented properties and names."""
    current = _category_text(payload.get("category")) or _category_text(payload.get("type"))
    params = _params(payload)
    keys = set(params)
    name = _device_name(payload)

    prop_category = _category_from_props(keys, name)
    if prop_category is not None:
        return prop_category

    if current and current not in BROAD_CATEGORIES:
        return current

    name_category = _category_from_name(name)
    if name_category is not None:
        return name_category

    if current == "switch":
        return "relay_switch"
    if current in BROAD_CATEGORIES:
        return None if current in {"", "binary_sensor", "sensor"} else current
    return current or None


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
            "model",
            "deviceModel",
        ),
    )
    if explicit and not is_generic_model_label(explicit):
        return explicit

    schema_name = _schema_model_name(payload)
    if schema_name:
        return schema_name

    name = _device_name(payload)
    for tokens, label in _FRIENDLY_MODEL_PATTERNS:
        if all(token.lower() in name.lower() for token in tokens):
            return label

    category = infer_iot_category(payload)
    if category in _CATEGORY_LABELS:
        return _CATEGORY_LABELS[category]
    return "易来设备"


def friendly_specific_model_name(payload: Mapping[str, Any]) -> str:
    """Return a registry-safe model label that is never a broad category word."""
    model = friendly_model_name(payload)
    if model not in _BROAD_CATEGORY_MODEL_LABELS:
        return model
    category = infer_iot_category(payload)
    if category in _BROAD_CATEGORY_MODEL_REPLACEMENTS:
        return _BROAD_CATEGORY_MODEL_REPLACEMENTS[category]
    name = _device_name(payload)
    return f"易来{name}设备" if name else "易来扩展设备"


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


def _category_from_props(keys: set[str], name: str) -> str | None:
    if keys & {"mv"}:
        return "human_sensor"
    if keys & {"dc"}:
        return "contact_sensor"
    if keys & {"cp", "tp", "rd"}:
        return "curtain"
    if keys & {"acp", "acm", "actt", "acct", "acf", "aco", "rfhp", "rfhct", "rfhtt"}:
        return "temp_control"
    if keys & {"tgt", "fa", "he"} and _has_any(name, _TEMP_CONTROL_NAME_TOKENS):
        return "temp_control"
    if (
        keys <= {"luminance", "level", "o", "bl", "bc", "bcg"}
        and keys & {"luminance", "level"}
    ):
        return "light_sensor"
    if keys & {"curp", "iec", "ap", "ae", "t", "h", "temp", "bl", "bc", "bcg"}:
        if not keys & {"p", "sp", "l", "ct", "c"}:
            return "other"
    if keys & {"alm"}:
        return _category_from_name(name) or "contact_sensor"
    return None


def _category_from_name(name: str) -> str | None:
    for tokens, category in (
        (_CONTACT_NAME_TOKENS, "contact_sensor"),
        (_HUMAN_NAME_TOKENS, "human_sensor"),
        (_LIGHT_SENSOR_NAME_TOKENS, "light_sensor"),
        (_SAFETY_SENSOR_NAME_TOKENS, "other"),
        (_TELEMETRY_SENSOR_NAME_TOKENS, "other"),
        (_CURTAIN_NAME_TOKENS, "curtain"),
        (_TEMP_CONTROL_NAME_TOKENS, "temp_control"),
        (_BATH_HEATER_NAME_TOKENS, "temp_control"),
        (_SCENE_PANEL_NAME_TOKENS, "scene_panel"),
        (_SWITCH_NAME_TOKENS, "relay_switch"),
        (_LIGHT_NAME_TOKENS, "light"),
    ):
        if _has_any(name, tokens):
            return category
    return None


def _params(payload: Mapping[str, Any]) -> dict[str, Any]:
    raw_params = payload.get("params")
    return dict(raw_params) if isinstance(raw_params, Mapping) else {}


def _device_name(payload: Mapping[str, Any]) -> str:
    return _first_text(payload, ("name", "deviceName", "device_name", "n")) or ""


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


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        if value := _text(payload.get(key)):
            return value
    return None


def _text(value: Any) -> str | None:
    return to_str(value)


def _category_text(value: Any) -> str | None:
    text = _text(value)
    if text is None:
        return None
    normalized = text.strip().lower().replace("_", " ").replace("-", " ")
    return CATEGORY_ALIASES.get(normalized, normalized.replace(" ", "_"))


def _has_any(text: str, tokens: tuple[str, ...]) -> bool:
    lower = text.lower()
    return any(token.lower() in lower for token in tokens)


__all__ = [
    "friendly_model_id",
    "friendly_model_name",
    "friendly_specific_model_name",
    "ha_platform_for_payload",
    "infer_iot_category",
    "is_generic_model_label",
]
