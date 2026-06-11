"""Config entry option verification."""

from __future__ import annotations

import ast
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from .constants import SOURCE_COMPONENT_ROOT
from .report import VerificationReport

REQUIRED_CONFIG_ENTRY_OPTION_KEYS = {
    "debug_mode",
    "hide_unknown_entities",
    "scan_interval",
    "topology_change_repairs",
}
OPTIONAL_CONFIG_ENTRY_OPTION_KEYS = {"device_import_filter"}


def verify_config_entry_options(
    entries: Iterable[Mapping[str, Any]],
    report: VerificationReport,
) -> None:
    """Verify config entry options are normalized without exposing option values."""
    entry_list = list(entries)
    if not entry_list:
        return

    option_defaults = _expected_option_defaults()
    if option_defaults is None:
        report.fail("entry option constants are not literal")
        return

    missing_by_key = _missing_option_keys(
        entry_list,
        required_keys=REQUIRED_CONFIG_ENTRY_OPTION_KEYS,
    )
    if missing_by_key:
        report.fail(f"config entry options missing required keys: {missing_by_key}")
    else:
        report.fact(
            "config entry required option keys present: "
            f"{sorted(REQUIRED_CONFIG_ENTRY_OPTION_KEYS)}"
        )

    invalid_by_key = _invalid_option_values(entry_list, option_defaults)
    if invalid_by_key:
        report.fail(f"config entry options outside allowed bounds: {invalid_by_key}")
    else:
        report.fact(
            "config entry option bounds valid: "
            f"scan_interval {option_defaults['min_scan_interval']}-"
            f"{option_defaults['max_scan_interval']}"
        )

    optional_missing_by_key = _missing_option_keys(
        entry_list,
        required_keys=OPTIONAL_CONFIG_ENTRY_OPTION_KEYS,
    )
    if optional_missing_by_key:
        report.fact(f"config entry optional option keys absent: {optional_missing_by_key}")
    else:
        report.fact(
            "config entry optional option keys present: "
            f"{sorted(OPTIONAL_CONFIG_ENTRY_OPTION_KEYS)}"
        )

    enabled_filter_count = _enabled_device_filter_count(entry_list)
    report.fact(
        "config entry option summary: "
        f"debug_true={_true_option_count(entry_list, 'debug_mode')}, "
        f"hide_unknown_true={_true_option_count(entry_list, 'hide_unknown_entities')}, "
        f"topology_repairs_true={_true_option_count(entry_list, 'topology_change_repairs')}, "
        f"device_filter_enabled={enabled_filter_count}"
    )
    report.metric(
        "config_entry_options",
        {
            "device_filter_enabled": enabled_filter_count,
            "missing_optional": optional_missing_by_key,
            "required_keys": sorted(REQUIRED_CONFIG_ENTRY_OPTION_KEYS),
        },
    )


def _missing_option_keys(
    entries: Iterable[Mapping[str, Any]],
    *,
    required_keys: set[str],
) -> dict[str, int]:
    """Return required option keys missing from enabled entries."""
    missing_counter: Counter[str] = Counter()
    for entry in entries:
        options = entry.get("options")
        if not isinstance(options, Mapping):
            for key in required_keys:
                missing_counter[key] += 1
            continue
        for key in required_keys:
            if key not in options:
                missing_counter[key] += 1
    return dict(sorted(missing_counter.items()))


def _invalid_option_values(
    entries: Iterable[Mapping[str, Any]],
    option_defaults: Mapping[str, int | bool],
) -> dict[str, int]:
    """Return option value validation failures without exposing raw values."""
    invalid_counter: Counter[str] = Counter()
    min_scan_interval = option_defaults["min_scan_interval"]
    max_scan_interval = option_defaults["max_scan_interval"]
    for entry in entries:
        options = entry.get("options")
        if not isinstance(options, Mapping):
            continue
        scan_interval = options.get("scan_interval")
        if (
            isinstance(scan_interval, bool)
            or not isinstance(scan_interval, int)
            or scan_interval < min_scan_interval
            or scan_interval > max_scan_interval
        ):
            invalid_counter["scan_interval"] += 1
        for key in {
            "debug_mode",
            "hide_unknown_entities",
            "topology_change_repairs",
        }:
            if not isinstance(options.get(key), bool):
                invalid_counter[key] += 1
    return dict(sorted(invalid_counter.items()))


def _true_option_count(entries: Iterable[Mapping[str, Any]], key: str) -> int:
    """Return how many entries have a boolean option enabled."""
    count = 0
    for entry in entries:
        options = entry.get("options")
        if isinstance(options, Mapping) and options.get(key) is True:
            count += 1
    return count


def _enabled_device_filter_count(entries: Iterable[Mapping[str, Any]]) -> int:
    """Return how many entries enable the device import filter."""
    count = 0
    for entry in entries:
        options = entry.get("options")
        filter_config = (
            options.get("device_import_filter") if isinstance(options, Mapping) else None
        )
        if isinstance(filter_config, Mapping) and filter_config.get("enabled") is True:
            count += 1
    return count


def _expected_option_defaults() -> dict[str, int | bool] | None:
    """Read option default constants without importing Home Assistant."""
    constants = _literal_module_values(
        SOURCE_COMPONENT_ROOT / "const.py",
        {
            "DEFAULT_DEBUG_MODE",
            "DEFAULT_HIDE_UNKNOWN_ENTITIES",
            "DEFAULT_SCAN_INTERVAL",
            "DEFAULT_TOPOLOGY_CHANGE_REPAIRS",
            "MAX_SCAN_INTERVAL",
            "MIN_SCAN_INTERVAL",
        },
    )
    required = {
        "default_debug_mode": constants.get("DEFAULT_DEBUG_MODE"),
        "default_hide_unknown_entities": constants.get(
            "DEFAULT_HIDE_UNKNOWN_ENTITIES"
        ),
        "default_scan_interval": constants.get("DEFAULT_SCAN_INTERVAL"),
        "default_topology_change_repairs": constants.get(
            "DEFAULT_TOPOLOGY_CHANGE_REPAIRS"
        ),
        "max_scan_interval": constants.get("MAX_SCAN_INTERVAL"),
        "min_scan_interval": constants.get("MIN_SCAN_INTERVAL"),
    }
    if any(not isinstance(value, int | bool) for value in required.values()):
        return None
    return required  # type: ignore[return-value]


def _literal_module_values(path: Path, names: set[str]) -> dict[str, int | bool]:
    """Return selected module-level literal int/bool constants."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    values: dict[str, int | bool] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not isinstance(node.value, ast.Constant) or not isinstance(
            node.value.value,
            int | bool,
        ):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in names:
                values[target.id] = node.value.value
    return values
