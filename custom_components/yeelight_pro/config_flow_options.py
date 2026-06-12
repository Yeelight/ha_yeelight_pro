"""Options-flow schema and merge helpers for Yeelight Pro."""
from __future__ import annotations

from typing import Any, Mapping

import voluptuous as vol

from .const import (
    CONF_CONNECTION_MODE,
    CONF_DEBUG_MODE,
    CONF_HIDE_UNKNOWN_ENTITIES,
    CONF_HOUSE_ID,
    CONF_LIVE_UPDATES,
    CONF_LOCAL_GATEWAY_CONTROL,
    CONF_LOCAL_GATEWAY_HOST,
    CONF_LOCAL_GATEWAY_PORT,
    CONF_OPEN_API_CLIENT_ID,
    CONF_SCAN_INTERVAL,
    CONF_TOPOLOGY_CHANGE_REPAIRS,
    CONF_CLOUD_DOMAIN,
    CONNECTION_MODE_CLOUD,
    CONNECTION_MODE_LAN,
    DEFAULT_DEBUG_MODE,
    DEFAULT_HIDE_UNKNOWN_ENTITIES,
    DEFAULT_LIVE_UPDATES,
    DEFAULT_LOCAL_GATEWAY_CONTROL,
    DEFAULT_LOCAL_GATEWAY_HOST,
    DEFAULT_LOCAL_GATEWAY_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TOPOLOGY_CHANGE_REPAIRS,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .entry_migration import normalize_entry_options

_OPTION_FORM_KEYS = (
    CONF_SCAN_INTERVAL,
    CONF_DEBUG_MODE,
    CONF_HIDE_UNKNOWN_ENTITIES,
    CONF_TOPOLOGY_CHANGE_REPAIRS,
    CONF_LIVE_UPDATES,
    CONF_LOCAL_GATEWAY_CONTROL,
    CONF_LOCAL_GATEWAY_HOST,
    CONF_LOCAL_GATEWAY_PORT,
)


def entry_options(entry: object) -> dict[str, Any]:
    """防御性读取 config entry options，并保留隐藏高级字段."""
    options = getattr(entry, "options", None)
    return dict(options) if isinstance(options, Mapping) else {}


def options_schema(options: Mapping[str, Any], entry: object | None = None) -> vol.Schema:
    """使用归一化默认值返回运行时 options 表单 schema."""
    normalized = normalize_entry_options(options)

    # 判断连接模式
    is_lan_mode = False
    if entry is not None:
        data = getattr(entry, "data", None)
        if isinstance(data, Mapping):
            is_lan_mode = data.get(CONF_CONNECTION_MODE) == CONNECTION_MODE_LAN

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
    }

    if not is_lan_mode:
        # 云端/私有部署模式：显示 WebSocket 选项
        fields[vol.Required(
            CONF_LIVE_UPDATES,
            default=normalized.get(CONF_LIVE_UPDATES, DEFAULT_LIVE_UPDATES),
        )] = bool
        fields[vol.Required(
            CONF_LOCAL_GATEWAY_CONTROL,
            default=normalized.get(
                CONF_LOCAL_GATEWAY_CONTROL,
                DEFAULT_LOCAL_GATEWAY_CONTROL,
            ),
        )] = bool
        fields[vol.Optional(
            CONF_LOCAL_GATEWAY_HOST,
            default=normalized.get(
                CONF_LOCAL_GATEWAY_HOST,
                DEFAULT_LOCAL_GATEWAY_HOST,
            ),
        )] = str
        fields[vol.Optional(
            CONF_LOCAL_GATEWAY_PORT,
            default=normalized.get(
                CONF_LOCAL_GATEWAY_PORT,
                DEFAULT_LOCAL_GATEWAY_PORT,
            ),
        )] = vol.All(vol.Coerce(int), vol.Range(min=1, max=65535))

    # 设备导入过滤由 options_flow 的多步向导处理，不在主表单中显示
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
    return sum(current.get(key) != pending.get(key) for key in _OPTION_FORM_KEYS)


def merge_options(
    current_options: Mapping[str, Any],
    user_input: Mapping[str, Any],
) -> dict[str, Any]:
    """将可见表单字段合入既有 options，避免丢弃隐藏高级字段."""
    data = dict(current_options)
    data.pop("experimental_platforms", None)
    normalized = normalize_entry_options(data)
    data.update({
        key: user_input[key] if key in user_input else normalized[key]
        for key in _OPTION_FORM_KEYS
    })
    return data


def options_support_device_filter(entry: object) -> bool:
    """Return whether an entry supports device import filtering."""
    data = getattr(entry, "data", None)
    if not isinstance(data, Mapping):
        return False
    mode = data.get(CONF_CONNECTION_MODE)
    # 云端和私有部署支持过滤；LAN 模式不需要（设备自动发现）
    return mode in (CONNECTION_MODE_CLOUD, "private")
