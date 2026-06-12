"""Options-flow helpers for Yeelight Pro device import filtering."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.helpers import selector

from .const import (
    CONF_DEVICE_IMPORT_FILTER,
)
from .device_filter import (
    canonical_device_import_filter,
    normalize_device_import_filter,
)

# 过滤维度定义：(维度名称, 翻译键, 从设备载荷中提取值的字段名)
FILTER_DIMENSIONS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("categories", "categories", ("iot_category", "category", "ha_platform")),
    ("rooms", "rooms", ("roomId", "room_id")),
    ("gateways", "gateways", ("gatewayId", "gateway_id")),
    ("devices", "devices", ("device_id", "id", "deviceId")),
)

# 所有维度名称
DIMENSION_NAMES = tuple(dim for dim, _, _ in FILTER_DIMENSIONS)


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
    iterable = (
        devices.values() if isinstance(devices, Mapping) else devices
    )
    for device in iterable:
        if not isinstance(device, Mapping):
            continue
        for field in fields:
            raw = device.get(field)
            if raw is None:
                continue
            value = str(raw).strip()
            if value and value not in seen:
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
                translation_key=f"device_filter_{dimension}",
            )
        ),
    })


def build_filter_config(
    selections: dict[str, list[str]],
    all_choices: dict[str, list[str]],
) -> dict[str, Any]:
    """将用户选择组装为规范 filter 配置。

    语义：全选 = 不过滤该维度；部分选择 = 仅导入选中的。
    全部维度都全选时返回 {"enabled": False}。
    """
    include: dict[str, list[str]] = {}

    for dimension in DIMENSION_NAMES:
        selected = selections.get(dimension, [])
        all_values = all_choices.get(dimension, [])

        if not all_values:
            continue

        if set(selected) >= set(all_values):
            # 全选 → 不限制该维度
            continue

        if selected:
            include[dimension] = sorted(selected)

    if not include:
        return {"enabled": False}

    return canonical_device_import_filter({
        "enabled": True,
        "mode": "or",
        "include": include,
        "exclude": {},
    })


def current_filter_selections(
    options: Mapping[str, Any],
) -> dict[str, list[str]]:
    """从存储的 options 中读取当前过滤选择。

    返回 {dimension: [selected_values]} 映射。
    空列表表示该维度无过滤（全选）。
    """
    filter_config = options.get(CONF_DEVICE_IMPORT_FILTER)
    if not isinstance(filter_config, Mapping):
        return {}

    normalized = normalize_device_import_filter(filter_config)
    if not normalized.enabled:
        return {}

    result: dict[str, list[str]] = {}
    include = normalized.include
    for dimension in DIMENSION_NAMES:
        values = include.get(dimension, set())
        if values:
            result[dimension] = sorted(values)
    return result


def stored_device_import_filter_options(
    options: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Return canonical import filter from stored options."""
    value = options.get(CONF_DEVICE_IMPORT_FILTER)
    if not isinstance(value, Mapping):
        return None
    return canonical_device_import_filter(value)


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
    """Return form-only keys used by the device filter UI.

    这些键在 options 合并后需要从存储中清除。
    """
    return tuple(
        f"filter_{dim}" for dim in DIMENSION_NAMES
    )


def _filter_config(options: Mapping[str, Any]) -> Mapping[str, Any]:
    value = options.get(CONF_DEVICE_IMPORT_FILTER)
    return value if isinstance(value, Mapping) else {}


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
