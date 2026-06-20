"""I/O helpers for the private-house coverage audit script."""

from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path
from typing import Any

from custom_components.yeelight_pro.core.exceptions import safe_error_summary
from custom_components.yeelight_pro.utils import to_str
from scripts.local_ha_verification.constants import SOURCE_COMPONENT_ROOT
from scripts.local_ha_verification.install import runtime_diff


def load_target_entry(
    config_dir: Path,
    *,
    entry_id: str,
    entry_title: str,
) -> dict[str, Any]:
    """Load the target Yeelight Pro config entry from HA storage."""
    entries_path = config_dir / ".storage" / "core.config_entries"
    payload = json.loads(entries_path.read_text(encoding="utf-8"))
    entries = payload.get("data", {}).get("entries", [])
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("domain") != "yeelight_pro":
            continue
        if entry_id and entry.get("entry_id") == entry_id:
            return entry
        if not entry_id and entry.get("title") == entry_title:
            return entry
    raise SystemExit("target Yeelight Pro config entry not found")


def entity_registry_by_unique_id(
    config_dir: Path,
    entry_id: str,
) -> dict[str, dict[str, Any]]:
    """Return enabled registry rows for one config entry keyed by unique_id."""
    registry_path = config_dir / ".storage" / "core.entity_registry"
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    rows = payload.get("data", {}).get("entities", [])
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("config_entry_id") != entry_id:
            continue
        if row.get("disabled_by") not in (None, ""):
            continue
        unique_id = to_str(row.get("unique_id"))
        if not unique_id:
            continue
        result[unique_id] = row
    return result


def installed_runtime_status(config_dir: Path) -> dict[str, Any]:
    """Return source-vs-installed runtime drift facts for the local HA config."""
    install_root = config_dir / "custom_components" / "yeelight_pro"
    diff = runtime_diff(SOURCE_COMPONENT_ROOT, install_root)
    return {
        "matched_source": diff.ok,
        "missing_files": len(diff.missing),
        "extra_files": len(diff.extra),
        "changed_files": len(diff.changed),
        "missing_samples": list(diff.missing[:12]),
        "extra_samples": list(diff.extra[:12]),
        "changed_samples": list(diff.changed[:12]),
    }


def print_summary(report: Mapping[str, Any], *, top: int) -> None:
    """Print a concise human-readable summary."""
    summary = report["summary"]
    print(json.dumps({"summary": summary}, ensure_ascii=False, sort_keys=True))
    devices = report.get("devices") or []
    problem_rows = [
        item
        for item in devices
        if isinstance(item, Mapping) and int(item.get("missing_total") or 0) > 0
    ]
    problem_rows.sort(
        key=lambda item: (
            -int(item.get("missing_total") or 0),
            str(item.get("category") or ""),
            str(item.get("name") or ""),
        )
    )
    for row in problem_rows[:top]:
        print(json.dumps(row, ensure_ascii=False, sort_keys=True))

    low_rows = [
        item
        for item in devices
        if isinstance(item, Mapping) and item.get("low_coverage_reasons")
    ]
    low_rows.sort(
        key=lambda item: (
            len(item.get("low_coverage_reasons") or ()),
            int(item.get("expected_total") or 0),
            str(item.get("category") or ""),
            str(item.get("name") or ""),
        ),
        reverse=True,
    )
    for row in low_rows[:top]:
        print(json.dumps({"low_coverage": row}, ensure_ascii=False, sort_keys=True))

    unprojected_rows = [
        item
        for item in devices
        if isinstance(item, Mapping)
        and (
            item.get("unprojected_readable_properties")
            or item.get("unprojected_writable_properties")
            or item.get("unprojected_events")
        )
    ]
    unprojected_rows.sort(
        key=lambda item: (
            len(item.get("unprojected_writable_properties") or ()),
            len(item.get("unprojected_readable_properties") or ()),
            len(item.get("unprojected_events") or ()),
            str(item.get("category") or ""),
            str(item.get("name") or ""),
        ),
        reverse=True,
    )
    for row in unprojected_rows[:top]:
        print(json.dumps({"unprojected": row}, ensure_ascii=False, sort_keys=True))


async def safe_list(
    name: str,
    awaitable: Any,
    endpoint_errors: dict[str, str],
) -> list[dict[str, Any]]:
    """Return a list endpoint result, recording ordinary failures."""
    try:
        rows = await awaitable
    except Exception as err:
        endpoint_errors[name] = safe_error_summary(err)
        return []
    return [dict(row) for row in rows if isinstance(row, Mapping)]


async def safe_mapping(
    name: str,
    awaitable: Any,
    endpoint_errors: dict[str, str],
) -> dict[int, dict[str, Any]]:
    """Return a mapping endpoint result, recording ordinary failures."""
    from custom_components.yeelight_pro.utils import to_int

    try:
        rows = await awaitable
    except Exception as err:
        endpoint_errors[name] = safe_error_summary(err)
        return {}
    result: dict[int, dict[str, Any]] = {}
    if isinstance(rows, Mapping):
        for key, value in rows.items():
            numeric = to_int(key)
            if numeric is not None and isinstance(value, Mapping):
                result[numeric] = dict(value)
    return result
