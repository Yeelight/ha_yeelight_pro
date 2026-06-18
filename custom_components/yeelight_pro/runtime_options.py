"""Runtime option update handling for Yeelight Pro config entries."""
from __future__ import annotations

from typing import Any, Mapping

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_CONNECTION_MODE,
    CONF_HIDE_UNKNOWN_ENTITIES,
    CONF_LIVE_UPDATES,
    CONF_LOCAL_GATEWAY_CONTROL,
    CONF_LOCAL_GATEWAY_HOST,
    CONF_LOCAL_GATEWAY_PORT,
    CONF_PRIVATE_DOMAIN,
    CONF_PRIVATE_PUSH_DOMAIN,
    CONF_TOPOLOGY_CHANGE_REPAIRS,
    DEFAULT_TOPOLOGY_CHANGE_REPAIRS,
    DOMAIN,
)
from .device_filter_options import device_import_filter_changed
from .entry_migration import normalize_entry_options
from .repair_issues import async_delete_topology_changed_issues


def entry_options(entry: ConfigEntry) -> Mapping[str, Any]:
    """安全读取配置条目 options，兼容测试替身和旧数据."""
    return normalize_entry_options(getattr(entry, "options", None))


def topology_change_repairs_enabled(entry: ConfigEntry) -> bool:
    """返回拓扑变化时是否创建 Repairs 提示."""
    return bool(
        entry_options(entry).get(
            CONF_TOPOLOGY_CHANGE_REPAIRS,
            DEFAULT_TOPOLOGY_CHANGE_REPAIRS,
        )
    )


def options_require_reload(
    old_options: Mapping[str, Any],
    new_options: Mapping[str, Any],
) -> bool:
    """Return whether changed options affect loaded platforms or entities."""
    old = normalize_entry_options(old_options)
    new = normalize_entry_options(new_options)
    reload_keys = {
        CONF_HIDE_UNKNOWN_ENTITIES,
        CONF_LIVE_UPDATES,
        CONF_LOCAL_GATEWAY_CONTROL,
        CONF_LOCAL_GATEWAY_HOST,
        CONF_LOCAL_GATEWAY_PORT,
    }
    if any(old.get(key) != new.get(key) for key in reload_keys):
        return True
    return device_import_filter_changed(old, new)


def entry_data_requires_reload(
    old_data: Mapping[str, Any] | None,
    new_data: Mapping[str, Any],
) -> bool:
    """Return whether config-entry data changes affect background transports."""
    if old_data is None:
        return False
    reload_keys = {
        CONF_CONNECTION_MODE,
        CONF_PRIVATE_DOMAIN,
        CONF_PRIVATE_PUSH_DOMAIN,
    }
    return any(old_data.get(key) != new_data.get(key) for key in reload_keys)


def _runtime_options_coordinator(value: Any) -> Any | None:
    """Return a coordinator-like object that can apply runtime options."""
    if hasattr(value, "options") and callable(getattr(value, "apply_options", None)):
        return value
    return None


async def async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """配置选项更新后选择性刷新运行时或重载配置条目."""
    if not topology_change_repairs_enabled(entry):
        async_delete_topology_changed_issues(hass, entry)

    loaded = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    coordinator = _runtime_options_coordinator(
        loaded.get("coordinator") if isinstance(loaded, Mapping) else None
    )
    if coordinator is None:
        await hass.config_entries.async_reload(entry.entry_id)
        return

    new_options = entry_options(entry)
    loaded_data = loaded.get("entry_data") if isinstance(loaded, Mapping) else None
    if not isinstance(loaded_data, Mapping):
        loaded_data = None
    if entry_data_requires_reload(loaded_data, getattr(entry, "data", {})):
        await hass.config_entries.async_reload(entry.entry_id)
        return

    if options_require_reload(coordinator.options, new_options):
        await hass.config_entries.async_reload(entry.entry_id)
        return

    coordinator.apply_options(new_options)
    runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if isinstance(runtime, dict):
        runtime["entry"] = entry
        runtime["entry_data"] = dict(getattr(entry, "data", {}))
