#!/usr/bin/env python3
"""Export private-house coverage classification JSON as a CSV matrix."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from collections.abc import Mapping
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.private_house_audit.classification import classify_report  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(
        description="Export Yeelight Pro private-house classification JSON to CSV."
    )
    parser.add_argument("classification", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    args = build_parser().parse_args(argv)
    classified = _classified_report(_load_json(args.classification))
    rows = [_device_row(item) for item in _sequence(classified.get("devices"))]
    rows.extend(
        _device_row(item)
        for item in _sequence(classified.get("topology_entities"))
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {args.output}")
    return 0


_FIELDNAMES = [
    "device",
    "category",
    "type",
    "pid",
    "online",
    "status",
    "action",
    "reason",
    "product_schema",
    "product_model",
    "device_instance",
    "actual_total",
    "expected_total",
    "missing_total",
    "extra_total",
    "coverage_percent",
    "control_status",
    "control_attention",
    "control_expected",
    "control_actual",
    "control_missing",
    "sensor_status",
    "sensor_expected",
    "sensor_actual",
    "sensor_missing",
    "diagnostic_status",
    "config_status",
    "event_status",
    "state_evidence_status",
    "acceptance_summary",
    "primary_expected",
    "primary_actual",
    "primary_missing",
    "diagnostic_expected",
    "diagnostic_actual",
    "diagnostic_missing",
    "config_expected",
    "config_actual",
    "config_missing",
    "event_expected",
    "event_actual",
    "event_missing",
    "control_platforms",
    "sensor_platforms",
    "diagnostic_platforms",
    "action_required_summary",
    "expected_roles",
    "actual_roles",
    "missing_roles",
    "expected_platforms",
    "actual_platforms",
    "missing_platforms",
    "source_raw_property_count",
    "source_raw_property_keys",
    "source_subdevice_count",
    "source_subdevice_property_count",
    "source_subdevice_property_keys",
    "source_product_schema_available",
    "source_product_model_available",
    "source_device_instance_available",
    "params_count",
    "model_components_count",
    "model_properties_count",
    "model_readable_properties_count",
    "model_writable_properties_count",
    "model_events_count",
    "model_actions_count",
    "instance_components_count",
    "instance_state_keys_count",
    "projected_component_count",
    "schema_gap_reason",
    "low_coverage_reasons",
    "param_keys",
    "projected_component_ids",
    "expected_samples",
    "missing_samples",
    "stale_samples",
]


def _device_row(item: Any) -> dict[str, Any]:
    """Return one CSV row from a classified device item."""
    if not isinstance(item, dict):
        return {key: "" for key in _FIELDNAMES}
    conclusion = item.get("conclusion") if isinstance(item.get("conclusion"), dict) else {}
    expected_roles = _mapping(item.get("expected_roles"))
    actual_roles = _mapping(item.get("actual_roles"))
    missing_roles = _mapping(item.get("missing_roles"))
    expected_platforms = _mapping(item.get("expected_platforms"))
    actual_platforms = _mapping(item.get("actual_platforms"))
    missing_platforms = _mapping(item.get("missing_platforms"))
    coverage_view = _mapping(item.get("coverage_view"))
    control_view = _mapping(coverage_view.get("control"))
    sensor_view = _mapping(coverage_view.get("sensor"))
    diagnostic_view = _mapping(coverage_view.get("diagnostic"))
    config_view = _mapping(coverage_view.get("config"))
    event_view = _mapping(coverage_view.get("event"))
    state_view = _mapping(coverage_view.get("state_evidence"))
    source_evidence = _mapping(item.get("source_evidence"))
    expected_total = _int_value(item.get("expected_total"))
    actual_total = _int_value(item.get("actual_total"))
    missing_total = _int_value(item.get("missing_total"))
    extra_total = _int_value(item.get("extra_total"))
    return {
        "device": str(item.get("name") or ""),
        "category": str(item.get("category") or ""),
        "type": str(item.get("type") or ""),
        "pid": _optional_int_text(item.get("pid")),
        "online": _optional_bool_text(item.get("online")),
        "status": str(conclusion.get("status") or ""),
        "action": str(conclusion.get("action") or ""),
        "reason": str(conclusion.get("reason") or ""),
        "product_schema": _bool_text(item.get("product_schema")),
        "product_model": _bool_text(item.get("product_model")),
        "device_instance": _bool_text(item.get("device_instance")),
        "actual_total": actual_total,
        "expected_total": expected_total,
        "missing_total": missing_total,
        "extra_total": extra_total,
        "coverage_percent": _coverage_percent(actual_total, expected_total, missing_total),
        "control_status": str(control_view.get("status") or ""),
        "control_attention": str(control_view.get("attention") or ""),
        "control_expected": _int_value(control_view.get("expected")),
        "control_actual": _int_value(control_view.get("actual")),
        "control_missing": _int_value(control_view.get("missing")),
        "sensor_status": str(sensor_view.get("status") or ""),
        "sensor_expected": _int_value(sensor_view.get("expected")),
        "sensor_actual": _int_value(sensor_view.get("actual")),
        "sensor_missing": _int_value(sensor_view.get("missing")),
        "diagnostic_status": str(diagnostic_view.get("status") or ""),
        "config_status": str(config_view.get("status") or ""),
        "event_status": str(event_view.get("status") or ""),
        "state_evidence_status": str(state_view.get("status") or ""),
        "acceptance_summary": str(coverage_view.get("summary") or ""),
        "primary_expected": _role_count(expected_roles, "primary_control_or_state"),
        "primary_actual": _role_count(actual_roles, "primary_control_or_state"),
        "primary_missing": _role_count(missing_roles, "primary_control_or_state"),
        "diagnostic_expected": _role_count(expected_roles, "diagnostic"),
        "diagnostic_actual": _role_count(actual_roles, "diagnostic"),
        "diagnostic_missing": _role_count(missing_roles, "diagnostic"),
        "config_expected": _role_count(expected_roles, "config"),
        "config_actual": _role_count(actual_roles, "config"),
        "config_missing": _role_count(missing_roles, "config"),
        "event_expected": _role_count(expected_roles, "event"),
        "event_actual": _role_count(actual_roles, "event"),
        "event_missing": _role_count(missing_roles, "event"),
        "control_platforms": _platform_family(actual_platforms, ("climate", "cover", "fan", "light", "switch")),
        "sensor_platforms": _platform_family(actual_platforms, ("binary_sensor", "sensor")),
        "diagnostic_platforms": _diagnostic_platforms(actual_platforms, actual_roles),
        "action_required_summary": _action_required_summary(
            conclusion,
            missing_total=missing_total,
            missing_platforms=missing_platforms,
        ),
        "expected_roles": _inline_mapping(expected_roles),
        "actual_roles": _inline_mapping(actual_roles),
        "missing_roles": _inline_mapping(missing_roles),
        "expected_platforms": _inline_mapping(expected_platforms),
        "actual_platforms": _inline_mapping(actual_platforms),
        "missing_platforms": _inline_mapping(missing_platforms),
        "source_raw_property_count": _int_value(source_evidence.get("raw_property_count")),
        "source_raw_property_keys": "|".join(
            str(value) for value in _sequence(source_evidence.get("raw_property_keys"))
        ),
        "source_subdevice_count": _int_value(source_evidence.get("subdevice_count")),
        "source_subdevice_property_count": _int_value(
            source_evidence.get("subdevice_property_count")
        ),
        "source_subdevice_property_keys": "|".join(
            str(value)
            for value in _sequence(source_evidence.get("subdevice_property_keys"))
        ),
        "source_product_schema_available": _bool_text(
            source_evidence.get("product_schema_available")
        ),
        "source_product_model_available": _bool_text(
            source_evidence.get("product_model_available")
        ),
        "source_device_instance_available": _bool_text(
            source_evidence.get("device_instance_available")
        ),
        "params_count": _int_value(item.get("params_count")),
        "model_components_count": _int_value(item.get("model_components_count")),
        "model_properties_count": _int_value(item.get("model_properties_count")),
        "model_readable_properties_count": _int_value(
            item.get("model_readable_properties_count")
        ),
        "model_writable_properties_count": _int_value(
            item.get("model_writable_properties_count")
        ),
        "model_events_count": _int_value(item.get("model_events_count")),
        "model_actions_count": _int_value(item.get("model_actions_count")),
        "instance_components_count": _int_value(item.get("instance_components_count")),
        "instance_state_keys_count": _int_value(item.get("instance_state_keys_count")),
        "projected_component_count": _int_value(item.get("projected_component_count")),
        "schema_gap_reason": str(item.get("schema_gap_reason") or ""),
        "low_coverage_reasons": "|".join(str(value) for value in _sequence(item.get("low_coverage_reasons"))),
        "param_keys": "|".join(str(value) for value in _sequence(item.get("param_keys"))),
        "projected_component_ids": "|".join(
            str(value) for value in _sequence(item.get("projected_component_ids"))
        ),
        "expected_samples": _entity_samples_text(item.get("expected_samples")),
        "missing_samples": _missing_samples_text(item.get("missing_samples")),
        "stale_samples": _entity_samples_text(item.get("stale_samples")),
    }


def _missing_samples_text(value: Any) -> str:
    """Return compact missing entity sample text."""
    return _entity_samples_text(value)


def _entity_samples_text(value: Any) -> str:
    """Return compact entity sample text."""
    parts: list[str] = []
    for sample in _sequence(value):
        if not isinstance(sample, dict):
            continue
        parts.append(
            "/".join(
                str(sample.get(key) or "")
                for key in ("platform", "name", "component_id", "entity_category", "role")
            )
        )
    return " | ".join(parts)


def _inline_mapping(value: Any) -> str:
    """Return stable key=value text for a mapping."""
    if not isinstance(value, dict) or not value:
        return ""
    return ";".join(f"{key}={value[key]}" for key in sorted(value))


def _mapping(value: Any) -> dict[str, Any]:
    """Return a mapping value for derived CSV fields."""
    return value if isinstance(value, dict) else {}


def _sequence(value: Any) -> list[Any]:
    """Return a list value while excluding strings."""
    return value if isinstance(value, list) else []


def _coverage_percent(actual_total: int, expected_total: int, missing_total: int) -> str:
    """Return actual/expected coverage percent as text."""
    if expected_total <= 0:
        return ""
    covered = max(0, expected_total - missing_total)
    return f"{covered / expected_total * 100:.1f}"


def _role_count(roles: Mapping[str, Any], role: str) -> int:
    """Return a count for one role bucket."""
    return _int_value(roles.get(role))


def _platform_family(platforms: Mapping[str, Any], names: tuple[str, ...]) -> str:
    """Return compact counts for one platform family."""
    return _inline_mapping(
        {name: platforms[name] for name in names if _int_value(platforms.get(name))}
    )


def _diagnostic_platforms(
    platforms: Mapping[str, Any],
    actual_roles: Mapping[str, Any],
) -> str:
    """Return diagnostic coverage in a readable way."""
    diagnostic_total = _role_count(actual_roles, "diagnostic")
    if not diagnostic_total:
        return ""
    return f"diagnostic={diagnostic_total};platforms={_platform_family(platforms, ('binary_sensor', 'sensor'))}"


def _action_required_summary(
    conclusion: Mapping[str, Any],
    *,
    missing_total: int,
    missing_platforms: Mapping[str, Any],
) -> str:
    """Return one concise human-facing action summary."""
    status = str(conclusion.get("status") or "")
    if status == "ok":
        return "OK"
    if status == "registry_stale":
        return (
            f"Reload HA entry to create {missing_total} missing entities"
            f" ({_inline_mapping(missing_platforms)})"
        )
    if status == "runtime_drift":
        return "Sync installed HA runtime from source, then reload the entry"
    if status == "source_data_limited":
        return "Only online/source evidence is available; do not synthesize entities"
    if status == "projection_gap":
        return "Fix projector coverage"
    return str(conclusion.get("action") or "")


def _int_value(value: Any) -> int:
    """Return an integer without treating bools as ints."""
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _optional_int_text(value: Any) -> str:
    """Return an optional integer as text."""
    return str(value) if isinstance(value, int) and not isinstance(value, bool) else ""


def _bool_text(value: Any) -> str:
    """Return a bool diagnostics value as lowercase text."""
    return "true" if value is True else "false"


def _optional_bool_text(value: Any) -> str:
    """Return an optional bool diagnostics value as lowercase text."""
    if value is True:
        return "true"
    if value is False:
        return "false"
    return ""


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        value = json.load(file)
    if not isinstance(value, dict):
        raise ValueError("classification report must be a JSON object")
    return value


def _classified_report(value: Mapping[str, Any]) -> dict[str, Any]:
    """Return a classified report, accepting raw audit JSON as input."""
    devices = _sequence(value.get("devices"))
    if devices and all(
        isinstance(item, Mapping) and isinstance(item.get("conclusion"), Mapping)
        for item in devices
    ):
        return dict(value)
    return classify_report(value)


if __name__ == "__main__":
    raise SystemExit(main())
