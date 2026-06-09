"""Options-flow schema and merge helpers for Yeelight Pro."""
from __future__ import annotations

from typing import Any, Mapping

import voluptuous as vol

from .const import (
    CONF_ANALYTICS_RETENTION_DAYS,
    CONF_ANALYTICS_RUNTIME,
    CONF_DEBUG_MODE,
    CONF_DEVICE_IMPORT_FILTER,
    CONF_EXPERIMENTAL_PLATFORMS,
    CONF_HIDE_UNKNOWN_ENTITIES,
    CONF_LIVE_UPDATES,
    CONF_LOCAL_GATEWAY_CONTROL,
    CONF_LOCAL_GATEWAY_HOST,
    CONF_LOCAL_GATEWAY_PORT,
    CONF_SCAN_INTERVAL,
    CONF_TOPOLOGY_CHANGE_REPAIRS,
    DEFAULT_ANALYTICS_RETENTION_DAYS,
    DEFAULT_ANALYTICS_RUNTIME,
    DEFAULT_DEBUG_MODE,
    DEFAULT_EXPERIMENTAL_PLATFORMS,
    DEFAULT_HIDE_UNKNOWN_ENTITIES,
    DEFAULT_LIVE_UPDATES,
    DEFAULT_LOCAL_GATEWAY_CONTROL,
    DEFAULT_LOCAL_GATEWAY_HOST,
    DEFAULT_LOCAL_GATEWAY_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TOPOLOGY_CHANGE_REPAIRS,
    MAX_ANALYTICS_RETENTION_DAYS,
    MAX_SCAN_INTERVAL,
    MIN_ANALYTICS_RETENTION_DAYS,
    MIN_SCAN_INTERVAL,
)
from .device_filter_options import (
    device_filter_form_keys,
    device_filter_schema_fields,
    device_import_filter_changed,
    merge_device_import_filter,
)
from .entry_migration import normalize_entry_options

_OPTION_FORM_KEYS = (
    CONF_SCAN_INTERVAL,
    CONF_DEBUG_MODE,
    CONF_EXPERIMENTAL_PLATFORMS,
    CONF_HIDE_UNKNOWN_ENTITIES,
    CONF_TOPOLOGY_CHANGE_REPAIRS,
    CONF_LIVE_UPDATES,
    CONF_LOCAL_GATEWAY_CONTROL,
    CONF_LOCAL_GATEWAY_HOST,
    CONF_LOCAL_GATEWAY_PORT,
    CONF_ANALYTICS_RUNTIME,
    CONF_ANALYTICS_RETENTION_DAYS,
)


def entry_options(entry: object) -> dict[str, Any]:
    """防御性读取 config entry options，并保留隐藏高级字段."""
    options = getattr(entry, "options", None)
    return dict(options) if isinstance(options, Mapping) else {}


def options_schema(options: Mapping[str, Any]) -> vol.Schema:
    """使用归一化默认值返回运行时 options 表单 schema."""
    normalized = normalize_entry_options(options)
    fields = {
        vol.Required(
            CONF_SCAN_INTERVAL,
            default=normalized.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        ): vol.All(
            vol.Coerce(int),
            vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
        ),
        vol.Required(
            CONF_DEBUG_MODE,
            default=normalized.get(CONF_DEBUG_MODE, DEFAULT_DEBUG_MODE),
        ): bool,
        vol.Required(
            CONF_EXPERIMENTAL_PLATFORMS,
            default=normalized.get(
                CONF_EXPERIMENTAL_PLATFORMS,
                DEFAULT_EXPERIMENTAL_PLATFORMS,
            ),
        ): bool,
        vol.Required(
            CONF_HIDE_UNKNOWN_ENTITIES,
            default=normalized.get(
                CONF_HIDE_UNKNOWN_ENTITIES,
                DEFAULT_HIDE_UNKNOWN_ENTITIES,
            ),
        ): bool,
        vol.Required(
            CONF_TOPOLOGY_CHANGE_REPAIRS,
            default=normalized.get(
                CONF_TOPOLOGY_CHANGE_REPAIRS,
                DEFAULT_TOPOLOGY_CHANGE_REPAIRS,
            ),
        ): bool,
        vol.Required(
            CONF_LIVE_UPDATES,
            default=normalized.get(CONF_LIVE_UPDATES, DEFAULT_LIVE_UPDATES),
        ): bool,
        vol.Required(
            CONF_LOCAL_GATEWAY_CONTROL,
            default=normalized.get(
                CONF_LOCAL_GATEWAY_CONTROL,
                DEFAULT_LOCAL_GATEWAY_CONTROL,
            ),
        ): bool,
        vol.Optional(
            CONF_LOCAL_GATEWAY_HOST,
            default=normalized.get(
                CONF_LOCAL_GATEWAY_HOST,
                DEFAULT_LOCAL_GATEWAY_HOST,
            ),
        ): str,
        vol.Optional(
            CONF_LOCAL_GATEWAY_PORT,
            default=normalized.get(
                CONF_LOCAL_GATEWAY_PORT,
                DEFAULT_LOCAL_GATEWAY_PORT,
            ),
        ): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
        vol.Required(
            CONF_ANALYTICS_RUNTIME,
            default=normalized.get(
                CONF_ANALYTICS_RUNTIME,
                DEFAULT_ANALYTICS_RUNTIME,
            ),
        ): bool,
        vol.Optional(
            CONF_ANALYTICS_RETENTION_DAYS,
            default=normalized.get(
                CONF_ANALYTICS_RETENTION_DAYS,
                DEFAULT_ANALYTICS_RETENTION_DAYS,
            ),
        ): vol.All(
            vol.Coerce(int),
            vol.Range(
                min=MIN_ANALYTICS_RETENTION_DAYS,
                max=MAX_ANALYTICS_RETENTION_DAYS,
            ),
        ),
    }
    fields.update(device_filter_schema_fields(normalized))
    return vol.Schema(fields)


def options_confirm_schema() -> vol.Schema:
    """返回 options 确认页的空表单 schema."""
    return vol.Schema({})


def visible_option_change_count(
    current_options: Mapping[str, Any],
    pending_options: Mapping[str, Any],
) -> int:
    """返回用户可见 options 字段的变更数量."""
    current = normalize_entry_options(current_options)
    pending = normalize_entry_options(pending_options)
    changes = sum(current.get(key) != pending.get(key) for key in _OPTION_FORM_KEYS)
    if device_import_filter_changed(current, pending):
        changes += 1
    return changes


def merge_options(
    current_options: Mapping[str, Any],
    user_input: Mapping[str, Any],
) -> dict[str, Any]:
    """将可见表单字段合入既有 options，避免丢弃隐藏高级字段."""
    data = dict(current_options)
    normalized = normalize_entry_options(data)
    data.update({
        key: user_input[key] if key in user_input else normalized[key]
        for key in _OPTION_FORM_KEYS
    })
    data[CONF_DEVICE_IMPORT_FILTER] = merge_device_import_filter(data, user_input)
    for key in device_filter_form_keys():
        data.pop(key, None)
    return data
