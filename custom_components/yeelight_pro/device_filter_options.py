"""Options-flow helpers for Yeelight Pro device import filtering."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.helpers import selector

from .const import CONF_DEVICE_IMPORT_FILTER
from .device_filter import (
    canonical_device_import_filter,
    normalize_device_import_filter,
)
from .device_filter_rules import normalize_bool

# 过滤维度定义：(维度名称, 翻译键, 从设备载荷中提取值的字段名)
FILTER_DIMENSIONS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("categories", "categories", ("category", "iot_category", "ha_platform")),
    ("rooms", "rooms", ("roomId", "room_id", "roomIdList", "roomIds")),
    ("gateways", "gateways", ("gatewayId", "gateway_id", "gatewayDeviceId")),
    ("devices", "devices", ("device_id", "id", "deviceId")),
)

# 所有向导维度名称，按页面顺序排列。
DIMENSION_NAMES = tuple(dim for dim, _, _ in FILTER_DIMENSIONS)
_LEGACY_DEVICE_FILTER_FORM_MAP: tuple[tuple[str, str, str], ...] = (
    ("device_import_filter_include_categories", "include", "categories"),
    ("device_import_filter_exclude_categories", "exclude", "categories"),
    ("device_import_filter_include_rooms", "include", "rooms"),
    ("device_import_filter_exclude_rooms", "exclude", "rooms"),
    ("device_import_filter_include_gateways", "include", "gateways"),
    ("device_import_filter_exclude_gateways", "exclude", "gateways"),
    ("device_import_filter_include_product_ids", "include", "product_ids"),
    ("device_import_filter_exclude_product_ids", "exclude", "product_ids"),
    ("device_import_filter_include_devices", "include", "devices"),
    ("device_import_filter_exclude_devices", "exclude", "devices"),
)
_LEGACY_DEVICE_FILTER_FORM_KEYS = (
    "device_import_filter_enabled",
    "device_import_filter_mode",
    "device_import_filter_picker",
    *(form_key for form_key, _, _ in _LEGACY_DEVICE_FILTER_FORM_MAP),
)


def filter_dimension_choices(
    devices: Mapping[str, Any] | list[dict[str, Any]],
    dimension: str,
) -> list[tuple[str, str]]:
    """从设备数据中提取指定维度的去重可选值。

    返回 [(value, label), ...] 排序列表。
    """
    fields = next(
        (fields for name, _, fields in FILTER_DIMENSIONS if name == dimension),
        (),
    )
    if not fields:
        return []

    seen: dict[str, str] = {}
    iterable = devices.values() if isinstance(devices, Mapping) else devices
    for device in iterable:
        if not isinstance(device, Mapping):
            continue
        for value in _device_field_values(device, fields):
            if value not in seen:
                seen[value] = _dimension_label(dimension, value, device)
                break

    return sorted(seen.items(), key=lambda item: item[1])


def filter_dimension_schema(
    choices: list[tuple[str, str]],
    selected: list[str] | None = None,
    *,
    dimension: str = "",
) -> vol.Schema:
    """构建维度多选列表 schema。

    - choices: [(value, label), ...]
    - selected: 当前已选值列表，None 表示全选
    """
    all_values = [value for value, _ in choices]
    effective = selected if selected is not None else all_values

    options = [
        selector.SelectOptionDict(value=value, label=label)
        for value, label in choices
    ]

    return vol.Schema({
        vol.Optional(
            f"filter_{dimension}",
            default=effective,
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=options,
                multiple=True,
                mode=selector.SelectSelectorMode.LIST,
            )
        ),
    })


def build_filter_config(
    selections: dict[str, list[str]],
    all_choices: dict[str, list[str]],
) -> dict[str, Any]:
    """将用户选择组装为规范 filter 配置。

    语义：全选 = 不过滤该维度；取消选择 = 写入 exclude 规则。
    全部维度都全选时返回规范的 disabled filter。
    """
    exclude: dict[str, list[str]] = {}

    for dimension in DIMENSION_NAMES:
        selected = set(selections.get(dimension, []))
        all_values = all_choices.get(dimension, [])
        unselected = [value for value in all_values if value not in selected]
        if unselected:
            exclude[dimension] = sorted(unselected)

    return canonical_device_import_filter({
        "enabled": bool(exclude),
        "mode": "or",
        "include": {},
        "exclude": exclude,
    })


def current_filter_selections(
    options: Mapping[str, Any],
    all_choices: Mapping[str, list[str]] | None = None,
) -> dict[str, list[str]]:
    """从存储的 options 中读取当前过滤选择。"""
    filter_config = options.get(CONF_DEVICE_IMPORT_FILTER)
    if not isinstance(filter_config, Mapping):
        return {}

    normalized = normalize_device_import_filter(filter_config)
    if not normalized.enabled:
        return {}

    result: dict[str, list[str]] = {}
    choices = all_choices or {}
    for dimension in DIMENSION_NAMES:
        included = normalized.include.get(dimension, set())
        if included:
            result[dimension] = sorted(included)
            continue
        excluded = normalized.exclude.get(dimension, set())
        all_values = choices.get(dimension, [])
        if excluded and all_values:
            result[dimension] = [
                value for value in all_values if value not in excluded
            ]
    return result


def stored_device_import_filter_options(
    options: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Return canonical import filter from stored options."""
    value = options.get(CONF_DEVICE_IMPORT_FILTER)
    if not isinstance(value, Mapping):
        return None
    return canonical_device_import_filter(value)


def stored_or_legacy_device_import_filter_options(
    options: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Return canonical import filter from stored config or legacy form keys."""
    stored = stored_device_import_filter_options(options)
    if stored is not None:
        return stored
    if any(key in options for key in _LEGACY_DEVICE_FILTER_FORM_KEYS):
        return canonical_device_import_filter(_legacy_device_import_filter_from_form(options))
    return None


def device_import_filter_changed(
    current_options: Mapping[str, Any],
    pending_options: Mapping[str, Any],
) -> bool:
    """Return whether the effective stored device filter changed."""
    current = normalize_device_import_filter(
        _filter_config(current_options),
    )
    pending = normalize_device_import_filter(
        _filter_config(pending_options),
    )
    return current != pending


def device_filter_form_keys() -> tuple[str, ...]:
    """Return form-only keys used by legacy and wizard device filter UI."""
    return (
        *_LEGACY_DEVICE_FILTER_FORM_KEYS,
        *(f"filter_{dim}" for dim in DIMENSION_NAMES),
    )


def _filter_config(options: Mapping[str, Any]) -> Mapping[str, Any]:
    value = options.get(CONF_DEVICE_IMPORT_FILTER)
    return value if isinstance(value, Mapping) else {}


def _legacy_device_import_filter_from_form(options: Mapping[str, Any]) -> dict[str, Any]:
    """从旧版文本字段恢复规范 filter，供迁移阶段清理旧 options."""
    include: dict[str, list[str]] = {}
    exclude: dict[str, list[str]] = {}

    for form_key, bucket, value_key in _LEGACY_DEVICE_FILTER_FORM_MAP:
        values = _split_csv(options.get(form_key))
        if not values:
            continue
        if bucket == "include":
            include[value_key] = values
        else:
            exclude[value_key] = values

    mode = str(options.get("device_import_filter_mode", "or")).strip().lower()
    return {
        "enabled": normalize_bool(options.get("device_import_filter_enabled", False)),
        "mode": "and" if mode == "and" else "or",
        "include": include,
        "exclude": exclude,
    }


def _split_csv(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        items = value
    else:
        items = str(value).split(",")
    return sorted({str(item).strip() for item in items if str(item).strip()})


def _device_field_values(device: Mapping[str, Any], fields: tuple[str, ...]) -> list[str]:
    values: list[str] = []
    for field in fields:
        raw = device.get(field)
        if isinstance(raw, (list, tuple, set)):
            values.extend(str(item).strip() for item in raw if str(item).strip())
        elif raw is not None and (value := str(raw).strip()):
            values.append(value)
    return values


def _dimension_label(dimension: str, value: str, device: Mapping[str, Any]) -> str:
    """为维度值生成人类可读标签。"""
    if dimension == "devices":
        name = device.get("name") or device.get("deviceName", "")
        if name:
            return f"{name} ({value})"
        return value
    if dimension == "rooms":
        name = device.get("roomName") or device.get("room_name", "")
        if name:
            return f"{name} ({value})"
        return value
    if dimension == "gateways":
        name = device.get("gatewayName") or device.get("gateway_name", "")
        if name:
            return f"{name} ({value})"
        return value
    if dimension == "categories":
        return _category_label(value)
    return value


def _category_label(value: str) -> str:
    """品类值的中文标签映射。"""
    labels = {
        "light": "灯具",
        "switch": "开关",
        "curtain": "窗帘",
        "climate": "空调",
        "sensor": "传感器",
        "cover": "窗帘电机",
        "fan": "风扇",
        "binary_sensor": "二进制传感器",
        "event": "事件",
        "number": "数值",
        "select": "选择器",
        "button": "按钮",
    }
    return labels.get(value, value)
