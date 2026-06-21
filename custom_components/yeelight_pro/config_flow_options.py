"""Options-flow schema and merge helpers for Yeelight Pro."""
from __future__ import annotations

from typing import Any, Mapping

import voluptuous as vol

from .const import (
    CONF_CONNECTION_MODE,
    CONF_DEBUG_MODE,
    CONF_DEVICE_IMPORT_FILTER,
    CONF_HIDE_UNKNOWN_ENTITIES,
    CONF_LIVE_UPDATES,
    CONF_LOCAL_GATEWAY_CONTROL,
    CONF_LOCAL_GATEWAY_HOST,
    CONF_LOCAL_GATEWAY_PORT,
    CONF_PRIVATE_DOMAIN,
    CONF_PRIVATE_PUSH_DOMAIN,
    CONF_SCAN_INTERVAL,
    CONF_TOPOLOGY_CHANGE_REPAIRS,
    CONNECTION_MODE_CLOUD,
    CONNECTION_MODE_LAN,
    CONNECTION_MODE_PRIVATE,
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
from .device_filter_options import (
    build_filter_config,
    filter_dimension_schema,
)
from .deployment_urls import deployment_private_push_base_url, deployment_push_base_url
from .entry_migration import normalize_entry_options

_BASE_OPTION_FORM_KEYS = (
    CONF_SCAN_INTERVAL,
    CONF_DEBUG_MODE,
    CONF_HIDE_UNKNOWN_ENTITIES,
    CONF_TOPOLOGY_CHANGE_REPAIRS,
)
_CLOUD_OPTION_FORM_KEYS = (CONF_LIVE_UPDATES,)
_LAN_OPTION_FORM_KEYS = (
    CONF_LOCAL_GATEWAY_CONTROL,
    CONF_LOCAL_GATEWAY_HOST,
    CONF_LOCAL_GATEWAY_PORT,
)
_OPTION_FORM_KEYS = (
    *_BASE_OPTION_FORM_KEYS,
    *_CLOUD_OPTION_FORM_KEYS,
    *_LAN_OPTION_FORM_KEYS,
)
_PRIVATE_ENTRY_DATA_FORM_KEYS = (CONF_PRIVATE_PUSH_DOMAIN,)


def entry_options(entry: object) -> dict[str, Any]:
    """防御性读取 config entry options，并保留隐藏高级字段."""
    options = getattr(entry, "options", None)
    return dict(options) if isinstance(options, Mapping) else {}


def options_schema(options: Mapping[str, Any], entry: object | None = None) -> vol.Schema:
    """使用归一化默认值返回运行时 options 表单 schema."""
    normalized = normalize_entry_options(options)

    connection_mode = _entry_connection_mode(entry)

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

    if connection_mode in {CONNECTION_MODE_CLOUD, CONNECTION_MODE_PRIVATE}:
        fields[vol.Required(
            CONF_LIVE_UPDATES,
            default=normalized.get(CONF_LIVE_UPDATES, DEFAULT_LIVE_UPDATES),
        )] = bool
        if connection_mode == CONNECTION_MODE_PRIVATE:
            fields[vol.Optional(
                CONF_PRIVATE_PUSH_DOMAIN,
                default=_entry_private_push_domain(entry),
            )] = str

    if connection_mode == CONNECTION_MODE_LAN:
        # 局域网模式才暴露本地网关运行时参数，避免云端 entry 出现无关配置。
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

    return vol.Schema(fields)


def options_confirm_schema() -> vol.Schema:
    """返回 options 确认页的空表单 schema."""
    return vol.Schema({})


def menu_options(entry: object) -> list[str]:
    """返回主菜单步骤 ID，由前端按当前用户语言翻译标签."""
    if options_support_device_filter(entry):
        if _entry_connection_mode(entry) == CONNECTION_MODE_CLOUD:
            return ["general", "cloud_devices", "filter_categories"]
        return ["general", "filter_categories"]
    return ["general"]


def visible_option_change_count(
    current_options: Mapping[str, Any],
    pending_options: Mapping[str, Any],
    entry: object | None = None,
) -> int:
    """返回用户可见 options 字段的变更数量."""
    current = normalize_entry_options(current_options)
    pending = normalize_entry_options(pending_options)
    count = sum(
        current.get(key) != pending.get(key)
        for key in _option_form_keys_for_entry(entry)
    )
    if current.get(CONF_DEVICE_IMPORT_FILTER) != pending.get(CONF_DEVICE_IMPORT_FILTER):
        count += 1
    return count


def visible_entry_data_change_count(
    current_data: Mapping[str, Any],
    pending_data: Mapping[str, Any] | None,
    entry: object | None = None,
) -> int:
    """Return visible config-entry data changes handled by options flow."""
    if pending_data is None or _entry_connection_mode(entry) != CONNECTION_MODE_PRIVATE:
        return 0
    return sum(
        str(current_data.get(key) or "") != str(pending_data.get(key) or "")
        for key in _PRIVATE_ENTRY_DATA_FORM_KEYS
    )


def merge_options(
    current_options: Mapping[str, Any],
    user_input: Mapping[str, Any],
    entry: object | None = None,
) -> dict[str, Any]:
    """将当前连接模式可见字段合入 options，避免写入无关默认项."""
    data = dict(current_options)
    data.pop("experimental_platforms", None)
    normalized = normalize_entry_options(data)
    visible_keys = _option_form_keys_for_entry(entry)
    for key in _OPTION_FORM_KEYS:
        if key in visible_keys:
            data[key] = user_input[key] if key in user_input else normalized[key]
        else:
            data.pop(key, None)
    if CONF_DEVICE_IMPORT_FILTER in normalized:
        data[CONF_DEVICE_IMPORT_FILTER] = normalized[CONF_DEVICE_IMPORT_FILTER]
    return data


def merge_private_entry_data(
    current_data: Mapping[str, Any],
    user_input: Mapping[str, Any],
    entry: object | None = None,
) -> dict[str, Any] | None:
    """Return updated private config-entry data when private push URL changes."""
    if _entry_connection_mode(entry) != CONNECTION_MODE_PRIVATE:
        return None
    normalized_push = _normalize_optional_private_push(
        user_input.get(CONF_PRIVATE_PUSH_DOMAIN),
        entry,
    )
    if normalized_push == str(current_data.get(CONF_PRIVATE_PUSH_DOMAIN) or ""):
        return None
    return {
        **dict(current_data),
        CONF_PRIVATE_PUSH_DOMAIN: normalized_push,
    }


def device_filter_schema_fields(
    choices: list[tuple[str, str]],
    selected: list[str] | None = None,
    *,
    dimension: str = "",
) -> vol.Schema:
    """Return the manual device-filter form schema for one dimension."""
    return filter_dimension_schema(choices, selected, dimension=dimension)


def merge_device_import_filter(
    current_options: Mapping[str, Any],
    selections: dict[str, list[str]],
    all_choices: dict[str, list[str]],
) -> dict[str, Any]:
    """Merge manual device-filter wizard selections into canonical options."""
    return {
        **dict(current_options),
        CONF_DEVICE_IMPORT_FILTER: build_filter_config(selections, all_choices),
    }


def _entry_connection_mode(entry: object | None) -> str:
    """返回 entry 连接模式；测试替身缺省按云端处理."""
    data = getattr(entry, "data", None) if entry is not None else None
    if isinstance(data, Mapping):
        mode = data.get(CONF_CONNECTION_MODE)
        if mode in {CONNECTION_MODE_CLOUD, CONNECTION_MODE_PRIVATE, CONNECTION_MODE_LAN}:
            return str(mode)
    return CONNECTION_MODE_CLOUD


def _entry_private_push_domain(entry: object | None) -> str:
    data = getattr(entry, "data", None) if entry is not None else None
    if isinstance(data, Mapping):
        return str(data.get(CONF_PRIVATE_PUSH_DOMAIN) or "")
    return ""


def _normalize_optional_private_push(value: Any, entry: object | None) -> str:
    text = "" if value is None else str(value).strip()
    if not text:
        return ""
    data = getattr(entry, "data", None) if entry is not None else None
    private_domain = (
        data.get(CONF_PRIVATE_DOMAIN)
        if isinstance(data, Mapping)
        else ""
    )
    normalized_push = deployment_push_base_url(text)
    return deployment_private_push_base_url(private_domain, normalized_push)


def _option_form_keys_for_entry(entry: object | None) -> tuple[str, ...]:
    """Return option keys that are visible for the entry connection mode."""
    connection_mode = _entry_connection_mode(entry)
    if connection_mode == CONNECTION_MODE_LAN:
        return (*_BASE_OPTION_FORM_KEYS, *_LAN_OPTION_FORM_KEYS)
    if connection_mode == CONNECTION_MODE_PRIVATE:
        return (*_BASE_OPTION_FORM_KEYS, *_CLOUD_OPTION_FORM_KEYS)
    return (*_BASE_OPTION_FORM_KEYS, *_CLOUD_OPTION_FORM_KEYS)


def options_support_device_filter(entry: object) -> bool:
    """Return whether an entry supports device import filtering."""
    data = getattr(entry, "data", None)
    if not isinstance(data, Mapping):
        return False
    return data.get(CONF_CONNECTION_MODE) in (
        CONNECTION_MODE_CLOUD,
        CONNECTION_MODE_PRIVATE,
    )
