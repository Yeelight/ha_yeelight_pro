#!/usr/bin/env python3
"""Export a control-first Markdown report from private-house coverage JSON."""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Mapping, Sequence
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.private_house_audit.classification import classify_report  # noqa: E402


CONTROL_ROLE = "primary_control_or_state"
CONTROL_PLATFORMS = ("climate", "cover", "fan", "light", "switch")


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(
        description="Export a Yeelight Pro private-house control coverage report."
    )
    parser.add_argument("classification", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    args = build_parser().parse_args(argv)
    classified = _classified_report(_load_json(args.classification))
    report = render_control_report(classified)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report + "\n", encoding="utf-8")
    print(f"Wrote control coverage report to {args.output}")
    return 0


def render_control_report(classified: Mapping[str, Any]) -> str:
    """Render a Markdown report focused on control coverage review."""
    summary = _mapping(classified.get("summary"))
    devices = [
        item for item in _sequence(classified.get("devices")) if isinstance(item, Mapping)
    ]
    topology_entities = [
        item
        for item in _sequence(classified.get("topology_entities"))
        if isinstance(item, Mapping)
    ]
    lines = [
        "# Yeelight Pro Private House Control Coverage",
        "",
        "## Executive Summary",
        "",
        *_summary_lines(summary, devices, topology_entities),
        "",
        "## Control Findings",
        "",
        *_control_findings_lines(devices),
        "",
        "## Source Data Limited Devices",
        "",
        *_source_limited_lines(devices),
        "",
        "## Per-Device Review Matrix",
        "",
        *_device_matrix_lines(devices),
        "",
        "## Topology Entities",
        "",
        *_topology_lines(topology_entities),
    ]
    return "\n".join(lines).rstrip()


def _summary_lines(
    summary: Mapping[str, Any],
    devices: Sequence[Mapping[str, Any]],
    topology_entities: Sequence[Mapping[str, Any]],
) -> list[str]:
    audit = _mapping(summary.get("audit"))
    control_counts = Counter(_control_status(item) for item in devices)
    status_counts = Counter(_conclusion_status(item) for item in devices)
    return [
        f"- Devices reviewed: {len(devices)}",
        f"- Topology entities reviewed: {len(topology_entities)}",
        "- Device statuses: " + _inline_mapping(status_counts),
        "- Control statuses: " + _inline_mapping(control_counts),
        "- Device entities expected/actual/missing: "
        f"{_int_value(audit.get('expected_entities'))}/"
        f"{_int_value(audit.get('actual_device_entities'))}/"
        f"{_int_value(audit.get('missing_entities'))}",
        "- Topology entities expected/actual/missing: "
        f"{_int_value(audit.get('expected_topology_entities'))}/"
        f"{_int_value(audit.get('actual_topology_entities'))}/"
        f"{_int_value(audit.get('missing_topology_entities'))}",
        "- Unprojected readable/writable/events devices: "
        f"{_int_value(audit.get('devices_with_unprojected_readable_properties'))}/"
        f"{_int_value(audit.get('devices_with_unprojected_writable_properties'))}/"
        f"{_int_value(audit.get('devices_with_unprojected_events'))}",
        "- Installed runtime matches source: "
        + _bool_text(_mapping(summary.get("install_runtime")).get("matched_source")),
    ]


def _control_findings_lines(devices: Sequence[Mapping[str, Any]]) -> list[str]:
    missing = [item for item in devices if _control_missing(item) > 0]
    expected_but_absent = [
        item
        for item in devices
        if _control_expected(item) > 0 and _control_actual(item) <= 0
    ]
    source_limited = [
        item for item in devices if _conclusion_status(item) == "source_data_limited"
    ]
    lines = [
        f"- Control missing devices: {len(missing)}",
        f"- Devices with expected controls but zero actual controls: {len(expected_but_absent)}",
        f"- Source-data-limited devices needing upstream/product-model evidence: {len(source_limited)}",
    ]
    if missing:
        lines.append("- Missing-control device list:")
        for item in missing:
            lines.append(
                "  - "
                f"{_text(item.get('name'))}: expected={_control_expected(item)}, "
                f"actual={_control_actual(item)}, missing={_control_missing(item)}, "
                f"platforms={_inline_mapping(_mapping(item.get('actual_platforms')))}"
            )
    else:
        lines.append("- Missing-control device list: None")
    return lines


def _source_limited_lines(devices: Sequence[Mapping[str, Any]]) -> list[str]:
    items = [
        item for item in devices if _conclusion_status(item) == "source_data_limited"
    ]
    if not items:
        return ["- None"]
    lines = [
        "| # | Device | Category | PID | Expected/Actual | Source Evidence | Reason |",
        "|---:|---|---|---:|---:|---|---|",
    ]
    for index, item in enumerate(items, start=1):
        lines.append(
            "| "
            f"{index} | {_md(_text(item.get('name')))} | {_md(_text(item.get('category')))} | "
            f"{_pid_text(item.get('pid'))} | {_int_value(item.get('expected_total'))}/"
            f"{_int_value(item.get('actual_total'))} | {_source_evidence_text(item)} | "
            f"{_md(_text(_mapping(item.get('conclusion')).get('reason')))} |"
        )
    return lines


def _device_matrix_lines(devices: Sequence[Mapping[str, Any]]) -> list[str]:
    lines = [
        "| # | Device | Category | Control | Diagnostic | Sensor | Config | Event | Entities | Status | Notes |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for index, item in enumerate(devices, start=1):
        lines.append(
            "| "
            f"{index} | {_md(_text(item.get('name')))} | {_md(_text(item.get('category')))} | "
            f"{_role_cell(item, 'control')} | "
            f"{_role_cell(item, 'diagnostic')} | "
            f"{_role_cell(item, 'sensor')} | "
            f"{_role_cell(item, 'config')} | "
            f"{_role_cell(item, 'event')} | "
            f"{_int_value(item.get('actual_total'))}/{_int_value(item.get('expected_total'))} | "
            f"{_md(_conclusion_status(item))} | {_md(_device_note(item))} |"
        )
    return lines


def _topology_lines(items: Sequence[Mapping[str, Any]]) -> list[str]:
    if not items:
        return ["- None"]
    lines = [
        "| # | Source | Actual/Expected | Roles | Platforms | Status |",
        "|---:|---|---:|---|---|---|",
    ]
    for index, item in enumerate(items, start=1):
        lines.append(
            "| "
            f"{index} | {_md(_text(item.get('source') or item.get('name')))} | "
            f"{_int_value(item.get('actual_total'))}/{_int_value(item.get('expected_total'))} | "
            f"{_md(_inline_mapping(_mapping(item.get('actual_roles'))))} | "
            f"{_md(_inline_mapping(_mapping(item.get('actual_platforms'))))} | "
            f"{_md(_conclusion_status(item))} |"
        )
    return lines


def _role_cell(item: Mapping[str, Any], role: str) -> str:
    view = _mapping(_mapping(item.get("coverage_view")).get(role))
    expected = _int_value(view.get("expected"))
    actual = _int_value(view.get("actual"))
    missing = _int_value(view.get("missing"))
    status = _text(view.get("status"))
    suffix = "" if missing <= 0 else f" missing {missing}"
    if not status:
        status = "unknown"
    return f"{actual}/{expected} {status}{suffix}"


def _device_note(item: Mapping[str, Any]) -> str:
    status = _conclusion_status(item)
    if status == "source_data_limited":
        return "source data limited; do not synthesize controls without product-model evidence"
    if _control_expected(item) <= 0:
        return _not_expected_note(item)
    platforms = _control_platforms(item)
    if platforms:
        return f"control platforms: {platforms}"
    return _text(_mapping(item.get("coverage_view")).get("summary")) or "covered"


def _not_expected_note(item: Mapping[str, Any]) -> str:
    category = _text(item.get("category"))
    if category == "scene_panel":
        return "event-input device; button actions are event entities, not switch controls"
    if category == "gateway":
        return "gateway/topology context; no primary control projected"
    if category == "other":
        return "config-only writable properties; no HA primary control role expected"
    return _text(_mapping(item.get("coverage_view")).get("summary")) or "no primary control expected"


def _control_status(item: Mapping[str, Any]) -> str:
    return _text(_mapping(_mapping(item.get("coverage_view")).get("control")).get("status"))


def _control_expected(item: Mapping[str, Any]) -> int:
    return _int_value(_mapping(_mapping(item.get("coverage_view")).get("control")).get("expected"))


def _control_actual(item: Mapping[str, Any]) -> int:
    return _int_value(_mapping(_mapping(item.get("coverage_view")).get("control")).get("actual"))


def _control_missing(item: Mapping[str, Any]) -> int:
    return _int_value(_mapping(_mapping(item.get("coverage_view")).get("control")).get("missing"))


def _control_platforms(item: Mapping[str, Any]) -> str:
    platforms = _mapping(item.get("actual_platforms"))
    return _inline_mapping({
        name: platforms[name]
        for name in CONTROL_PLATFORMS
        if _int_value(platforms.get(name)) > 0
    })


def _source_evidence_text(item: Mapping[str, Any]) -> str:
    evidence = _mapping(item.get("source_evidence"))
    keys = _sequence(evidence.get("raw_property_keys")) or _sequence(item.get("param_keys"))
    parts = [
        f"params={_int_value(item.get('params_count'))}",
        "keys=" + ",".join(str(key) for key in keys),
        f"model={_bool_text(item.get('product_model'))}",
        f"schema={_bool_text(item.get('product_schema'))}",
    ]
    return _md(";".join(parts))


def _conclusion_status(item: Mapping[str, Any]) -> str:
    return _text(_mapping(item.get("conclusion")).get("status"))


def _inline_mapping(value: Mapping[str, Any] | Counter[str]) -> str:
    """Return stable key=value text for a mapping."""
    if not value:
        return ""
    return ";".join(f"{key}={value[key]}" for key in sorted(value))


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> Sequence[Any]:
    return value if isinstance(value, Sequence) and not isinstance(value, str) else ()


def _int_value(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _text(value: Any) -> str:
    return str(value) if value not in (None, "") else ""


def _pid_text(value: Any) -> str:
    return str(value) if isinstance(value, int) and not isinstance(value, bool) else ""


def _bool_text(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    return ""


def _md(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        value = json.load(file)
    if not isinstance(value, dict):
        raise ValueError("classification report must be a JSON object")
    return value


def _classified_report(value: Mapping[str, Any]) -> dict[str, Any]:
    devices = _sequence(value.get("devices"))
    if devices and all(
        isinstance(item, Mapping) and isinstance(item.get("conclusion"), Mapping)
        for item in devices
    ):
        return dict(value)
    return classify_report(value)


if __name__ == "__main__":
    raise SystemExit(main())
