"""Runtime option diagnostics helper tests for Yeelight Pro."""
from __future__ import annotations

from custom_components.yeelight_pro.const import (
    CONF_DEBUG_MODE,
    CONF_SCAN_INTERVAL,
    MAX_SCAN_INTERVAL,
    get_enabled_platforms,
)
from custom_components.yeelight_pro.diagnostic_options import (
    option_status_diagnostics,
)

from .diagnostics_helpers import (
    build_diagnostics_entry,
    build_empty_diagnostics_coordinator,
)


def test_option_status_reports_unloaded_runtime() -> None:
    """未加载 runtime 时仍应输出可判断的 options 状态."""
    entry = build_diagnostics_entry()
    expected_platform_count = len(get_enabled_platforms(entry.options))

    assert option_status_diagnostics(entry, {}, None) == {
        "runtime_loaded": False,
        "runtime_reload_required": True,
        "platforms_match_options": False,
        "loaded_platform_count": 0,
        "expected_platform_count": expected_platform_count,
        "debug_mode_enabled": True,
        "scan_interval_seconds": 15,
        "hide_unknown_entities": False,
        "topology_change_repairs": False,
        "live_updates_enabled": False,
        "local_gateway_control_enabled": False,
        "import_filter_active": True,
        "import_filter_rule_count": 2,
        "import_filter_ignored_rule_count": 2,
    }


def test_option_status_normalizes_legacy_runtime_options() -> None:
    """诊断状态应复用 options 归一化，避免旧 entry 和 runtime 语义漂移."""
    entry = build_diagnostics_entry()
    entry.options = {
        **entry.options,
        CONF_SCAN_INTERVAL: "999",
        CONF_DEBUG_MODE: "false",
    }

    status = option_status_diagnostics(entry, {}, None)

    assert status["debug_mode_enabled"] is False
    assert status["scan_interval_seconds"] == MAX_SCAN_INTERVAL
    assert status["import_filter_ignored_rule_count"] == 2


def test_option_status_reports_loaded_runtime_alignment() -> None:
    """已加载 runtime 时应区分平台一致和是否需要重载."""
    entry = build_diagnostics_entry()
    coordinator = build_empty_diagnostics_coordinator()
    coordinator.options = dict(entry.options)
    runtime = {
        "platforms": get_enabled_platforms(entry.options),
    }
    expected_platform_count = len(get_enabled_platforms(entry.options))

    assert option_status_diagnostics(entry, runtime, coordinator) == {
        "runtime_loaded": True,
        "runtime_reload_required": False,
        "platforms_match_options": True,
        "loaded_platform_count": expected_platform_count,
        "expected_platform_count": expected_platform_count,
        "debug_mode_enabled": True,
        "scan_interval_seconds": 15,
        "hide_unknown_entities": False,
        "topology_change_repairs": False,
        "live_updates_enabled": False,
        "local_gateway_control_enabled": False,
        "import_filter_active": True,
        "import_filter_rule_count": 2,
        "import_filter_ignored_rule_count": 2,
    }
