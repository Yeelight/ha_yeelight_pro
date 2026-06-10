"""Options-flow schema and merge helpers for Yeelight Pro."""
from __future__ import annotations

from typing import Any, Mapping

import voluptuous as vol

from .const import (
    CONF_CONNECTION_MODE,
    CONF_CLOUD_DOMAIN,
    CONF_DEBUG_MODE,
    CONF_DEVICE_IMPORT_FILTER,
    CONF_EXPERIMENTAL_PLATFORMS,
    CONF_HIDE_UNKNOWN_ENTITIES,
    CONF_DEVICE_IMPORT_FILTER_PICKER,
    CONF_HOUSE_ID,
    CONF_LIVE_UPDATES,
    CONF_LOCAL_GATEWAY_CONTROL,
    CONF_LOCAL_GATEWAY_HOST,
    CONF_LOCAL_GATEWAY_PORT,
    CONF_OPEN_API_CLIENT_ID,
    CONF_SCAN_INTERVAL,
    CONF_TOPOLOGY_CHANGE_REPAIRS,
    CONNECTION_MODE_CLOUD,
    DEFAULT_DEBUG_MODE,
    DEFAULT_EXPERIMENTAL_PLATFORMS,
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
from .config_flow_device_picker import (
    DevicePickerChoice,
    device_import_filter_for_selected_devices,
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
)


def entry_options(entry: object) -> dict[str, Any]:
    """防御性读取 config entry options，并保留隐藏高级字段."""
    options = getattr(entry, "options", None)
    return dict(options) if isinstance(options, Mapping) else {}


def options_schema(options: Mapping[str, Any], entry: object | None = None) -> vol.Schema:
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
    }
    fields.update(device_filter_schema_fields(normalized))
    if entry is not None:
        fields.update(device_picker_schema_fields(entry))
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
    data.pop(CONF_DEVICE_IMPORT_FILTER_PICKER, None)
    return data


def options_device_picker_requested(user_input: Mapping[str, Any]) -> bool:
    """Return whether the user asked to open the real-device picker step."""
    return bool(user_input.get(CONF_DEVICE_IMPORT_FILTER_PICKER))


def options_support_device_picker(entry: object) -> bool:
    """Return whether an entry has enough cloud context to load real devices."""
    data = getattr(entry, "data", None)
    if not isinstance(data, Mapping):
        return False
    return (
        data.get(CONF_CONNECTION_MODE) == CONNECTION_MODE_CLOUD
        and bool(str(data.get(CONF_CLOUD_DOMAIN, "")).strip())
        and bool(str(data.get(CONF_HOUSE_ID, "")).strip())
    )


def device_picker_schema_fields(entry: object) -> dict[Any, Any]:
    """Return the optional real-device picker opener for cloud entries."""
    if not options_support_device_picker(entry):
        return {}
    return {vol.Optional(CONF_DEVICE_IMPORT_FILTER_PICKER, default=False): bool}


def selected_device_ids_from_options(
    options: Mapping[str, Any],
    choices: tuple[DevicePickerChoice, ...],
) -> list[str]:
    """Return current picker selections from stored import-filter options."""
    all_device_ids = [choice.device_id for choice in choices]
    if not all_device_ids:
        return []
    normalized = normalize_entry_options(options)
    filter_config = normalized.get(CONF_DEVICE_IMPORT_FILTER)
    if not isinstance(filter_config, Mapping):
        return all_device_ids
    if not filter_config.get("enabled"):
        return all_device_ids
    include = filter_config.get("include")
    if not isinstance(include, Mapping):
        return all_device_ids
    raw_devices = include.get("devices")
    if not isinstance(raw_devices, (list, tuple, set)):
        return all_device_ids
    allowed = set(all_device_ids)
    selected = [
        text
        for value in raw_devices
        if (text := str(value).strip()) and text in allowed
    ]
    return selected


def merge_options_device_picker(
    current_options: Mapping[str, Any],
    selected_device_ids: list[str],
    choices: tuple[DevicePickerChoice, ...],
) -> dict[str, Any]:
    """Store a real-device picker selection as the canonical import filter."""
    data = dict(current_options)
    data[CONF_DEVICE_IMPORT_FILTER] = device_import_filter_for_selected_devices(
        selected_device_ids,
        choices,
    )
    for key in device_filter_form_keys():
        data.pop(key, None)
    data.pop(CONF_DEVICE_IMPORT_FILTER_PICKER, None)
    return data


def device_picker_context(entry: object) -> tuple[str, int, str | None]:
    """Return domain, house id, and client id for an options real-device picker."""
    data = getattr(entry, "data", None)
    if not isinstance(data, Mapping):
        raise ValueError("cloud entry data is required for device picker")
    domain = str(data.get(CONF_CLOUD_DOMAIN, "")).strip()
    try:
        house_id = int(str(data.get(CONF_HOUSE_ID, "")).strip())
    except (TypeError, ValueError) as err:
        raise ValueError("cloud house id is required for device picker") from err
    client_id = str(data.get(CONF_OPEN_API_CLIENT_ID, "")).strip() or None
    if not domain:
        raise ValueError("cloud domain is required for device picker")
    return domain, house_id, client_id
