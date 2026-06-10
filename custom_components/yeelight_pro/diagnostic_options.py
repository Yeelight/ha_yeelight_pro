"""Runtime option diagnostics for Yeelight Pro."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .const import (
    CONF_DEBUG_MODE,
    CONF_DEVICE_IMPORT_FILTER,
    CONF_EXPERIMENTAL_PLATFORMS,
    CONF_HIDE_UNKNOWN_ENTITIES,
    CONF_LIVE_UPDATES,
    CONF_LOCAL_GATEWAY_CONTROL,
    CONF_SCAN_INTERVAL,
    CONF_TOPOLOGY_CHANGE_REPAIRS,
    DEFAULT_DEBUG_MODE,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TOPOLOGY_CHANGE_REPAIRS,
    get_enabled_platforms,
)
from .diagnostic_summaries import mapping_values
from .device_filter import preview_device_import_filter
from .entry_migration import normalize_entry_options
from .runtime_options import options_require_reload


def option_status_diagnostics(
    entry: Any,
    runtime: Mapping[str, Any],
    coordinator: Any | None,
) -> dict[str, Any]:
    """返回 options 与当前运行时状态是否一致的聚合诊断."""
    entry_options = _entry_options(entry)
    normalized_entry_options = normalize_entry_options(entry_options)
    coordinator_options = getattr(coordinator, "options", None)
    normalized_coordinator_options = (
        normalize_entry_options(coordinator_options)
        if isinstance(coordinator_options, Mapping)
        else None
    )
    loaded_platforms = {
        str(platform)
        for platform in (runtime.get("platforms") or [])
        if isinstance(platform, str)
    }
    expected_platforms = set(get_enabled_platforms(normalized_entry_options))
    reload_required = (
        True
        if normalized_coordinator_options is None
        else options_require_reload(normalized_coordinator_options, normalized_entry_options)
    )
    device_import_preview = preview_device_import_filter(
        mapping_values(getattr(coordinator, "devices", {})) if coordinator else (),
        entry_options.get(CONF_DEVICE_IMPORT_FILTER),
    )
    return {
        "runtime_loaded": coordinator is not None,
        "runtime_reload_required": reload_required,
        "platforms_match_options": loaded_platforms == expected_platforms,
        "loaded_platform_count": len(loaded_platforms),
        "expected_platform_count": len(expected_platforms),
        "debug_mode_enabled": bool(
            normalized_entry_options.get(CONF_DEBUG_MODE, DEFAULT_DEBUG_MODE)
        ),
        "scan_interval_seconds": int(
            normalized_entry_options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        ),
        "experimental_platforms_enabled": bool(
            normalized_entry_options.get(CONF_EXPERIMENTAL_PLATFORMS, False)
        ),
        "hide_unknown_entities": bool(
            normalized_entry_options.get(CONF_HIDE_UNKNOWN_ENTITIES, False)
        ),
        "topology_change_repairs": bool(
            normalized_entry_options.get(
                CONF_TOPOLOGY_CHANGE_REPAIRS,
                DEFAULT_TOPOLOGY_CHANGE_REPAIRS,
            )
        ),
        "live_updates_enabled": bool(
            normalized_entry_options.get(CONF_LIVE_UPDATES, False)
        ),
        "local_gateway_control_enabled": bool(
            normalized_entry_options.get(CONF_LOCAL_GATEWAY_CONTROL, False)
        ),
        "import_filter_active": device_import_preview.enabled,
        "import_filter_rule_count": device_import_preview.rules_count,
        "import_filter_ignored_rule_count": device_import_preview.ignored_rule_count,
    }


def _entry_options(entry: Any) -> dict[str, Any]:
    """安全读取配置条目 options，兼容 HA runtime 和测试替身."""
    options = getattr(entry, "options", None)
    return dict(options) if isinstance(options, Mapping) else {}
