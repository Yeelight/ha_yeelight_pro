"""Markdown rendering for private-house coverage classification reports."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

STATUS_PROJECTION_GAP = "projection_gap"
STATUS_REGISTRY_STALE = "registry_stale"
STATUS_RUNTIME_DRIFT = "runtime_drift"
STATUS_SOURCE_DATA_LIMITED = "source_data_limited"


def markdown_report(classified: Mapping[str, Any]) -> str:
    """Render classification output as a compact Markdown report."""
    summary = _mapping_value(classified.get("summary"))
    devices = _sequence_value(classified.get("devices"))
    audit = _mapping_value(summary.get("audit"))
    install_runtime = _mapping_value(summary.get("install_runtime"))
    lines = [
        "# Yeelight Pro Private House Coverage Classification",
        "",
        "## Summary",
        "",
        f"- Devices: {_int_value(summary.get('device_count'))}",
        f"- Statuses: {_inline_mapping(_mapping_value(summary.get('statuses')))}",
        f"- Actions: {_inline_mapping(_mapping_value(summary.get('actions')))}",
        f"- Expected/Actual entities: {_int_value(audit.get('expected_entities'))}/"
        f"{_int_value(audit.get('actual_device_entities'))}",
        f"- Missing entities: {_int_value(audit.get('missing_entities'))}"
        f" ({_inline_mapping(_mapping_value(audit.get('missing_platforms')))})",
        f"- Topology expected/actual/missing: "
        f"{_int_value(audit.get('expected_topology_entities'))}/"
        f"{_int_value(audit.get('actual_topology_entities'))}/"
        f"{_int_value(audit.get('missing_topology_entities'))}"
        f" ({_inline_mapping(_mapping_value(audit.get('topology_missing_platforms')))})",
        f"- Extra device entities: {_int_value(audit.get('extra_device_entities'))}",
        f"- Schema gaps: {_inline_mapping(_mapping_value(audit.get('schema_gaps')))}",
        "- Unprojected readable/writable/events: "
        f"{_int_value(audit.get('devices_with_unprojected_readable_properties'))}/"
        f"{_int_value(audit.get('devices_with_unprojected_writable_properties'))}/"
        f"{_int_value(audit.get('devices_with_unprojected_events'))}",
        f"- Endpoint errors: {_inline_mapping(_mapping_value(audit.get('endpoint_errors')))}",
        f"- Installed runtime matches source: "
        f"{_bool_text(install_runtime.get('matched_source'))}"
        f" ({_inline_mapping(_runtime_drift_counts(install_runtime))})",
        f"- Hydration: {_inline_mapping(_mapping_value(audit.get('hydration')))}",
        "",
        "## Action Buckets",
        "",
        *_action_bucket_lines(devices),
        "",
        "## Device Conclusions",
        "",
        "| # | Device | Category | Actual/Expected | Missing/Extra | Roles | Platforms | Status | Action | Reason |",
        "|---:|---|---|---:|---:|---|---|---|---|---|",
    ]
    for index, item in enumerate(devices, start=1):
        if not isinstance(item, Mapping):
            continue
        conclusion = _mapping_value(item.get("conclusion"))
        lines.append(
            "| "
            f"{index} | "
            f"{_escape_table(str(item.get('name') or ''))} | "
            f"{_escape_table(str(item.get('category') or ''))} | "
            f"{_int_value(item.get('actual_total'))}/{_int_value(item.get('expected_total'))} | "
            f"{_int_value(item.get('missing_total'))}/{_int_value(item.get('extra_total'))} | "
            f"{_escape_table(_role_matrix(item))} | "
            f"{_escape_table(_platform_matrix(item))} | "
            f"{_escape_table(str(conclusion.get('status') or ''))} | "
            f"{_escape_table(str(conclusion.get('action') or ''))} | "
            f"{_escape_table(str(conclusion.get('reason') or ''))} |"
        )
    lines.append("")
    return "\n".join(lines)


def _action_bucket_lines(devices: Sequence[Any]) -> list[str]:
    """Return grouped action lines for non-OK device conclusions."""
    lines: list[str] = []
    for status, title in (
        (STATUS_PROJECTION_GAP, "Projection Gaps"),
        (STATUS_RUNTIME_DRIFT, "Installed Runtime Drift"),
        (STATUS_REGISTRY_STALE, "Registry Refresh Required"),
        (STATUS_SOURCE_DATA_LIMITED, "Source Data Limited"),
    ):
        items = [
            item
            for item in devices
            if isinstance(item, Mapping)
            and _mapping_value(item.get("conclusion")).get("status") == status
        ]
        lines.append(f"### {title} ({len(items)})")
        lines.append("")
        if not items:
            lines.append("- None")
            lines.append("")
            continue
        for item in items:
            lines.append(
                "- "
                f"{_escape_table(str(item.get('name') or ''))} "
                f"[{_escape_table(str(item.get('category') or ''))}] "
                f"actual/expected={_int_value(item.get('actual_total'))}/"
                f"{_int_value(item.get('expected_total'))}, "
                f"missing={_int_value(item.get('missing_total'))}"
                f"{_bucket_detail(item)}"
            )
            lines.extend(_missing_sample_lines(item))
        lines.append("")
    return lines


def _bucket_detail(item: Mapping[str, Any]) -> str:
    """Return compact detail for an action-bucket row."""
    missing_platforms = _mapping_value(item.get("missing_platforms"))
    reasons = _sequence_value(item.get("low_coverage_reasons"))
    param_keys = _sequence_value(item.get("param_keys"))
    parts: list[str] = []
    if missing_platforms:
        parts.append(f"missing_platforms={_inline_mapping(missing_platforms)}")
    if reasons:
        parts.append("reasons=" + ",".join(str(reason) for reason in reasons))
    if param_keys:
        parts.append("params=" + ",".join(str(key) for key in param_keys))
    return "" if not parts else " (" + "; ".join(parts) + ")"


def _missing_sample_lines(item: Mapping[str, Any]) -> list[str]:
    """Return missing entity sample lines for registry-refresh buckets."""
    samples = [
        sample
        for sample in _sequence_value(item.get("missing_samples"))
        if isinstance(sample, Mapping)
    ]
    if not samples:
        return []
    lines = ["  - Missing entity samples:"]
    for sample in samples:
        lines.append(
            "    - "
            f"platform={_markdown_value(sample.get('platform'))}, "
            f"name={_markdown_value(sample.get('name'))}, "
            f"component_id={_markdown_value(sample.get('component_id'))}, "
            f"entity_category={_markdown_value(sample.get('entity_category'))}, "
            f"role={_markdown_value(sample.get('role'))}"
        )
    return lines


def _int_value(value: Any) -> int:
    """Return an int diagnostics value without treating bools as integers."""
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _mapping_value(value: Any) -> Mapping[str, Any]:
    """Return mapping diagnostics or an empty mapping."""
    return value if isinstance(value, Mapping) else {}


def _sequence_value(value: Any) -> Sequence[Any]:
    """Return sequence diagnostics or an empty tuple, excluding strings."""
    return value if isinstance(value, Sequence) and not isinstance(value, str) else ()


def _inline_mapping(value: Mapping[str, Any]) -> str:
    """Return a stable inline summary for a small mapping."""
    if not value:
        return "{}"
    return ", ".join(f"{key}={value[key]}" for key in sorted(value))


def _runtime_drift_counts(value: Mapping[str, Any]) -> dict[str, int]:
    """Return compact install-runtime drift counts."""
    return {
        key: _int_value(value.get(key))
        for key in ("changed_files", "extra_files", "missing_files")
        if _int_value(value.get(key))
    }


def _bool_text(value: Any) -> str:
    """Return a compact optional bool value."""
    if value is True:
        return "true"
    if value is False:
        return "false"
    return "unknown"


def _role_matrix(item: Mapping[str, Any]) -> str:
    """Return expected/actual/missing role coverage for one device."""
    return (
        "exp{"
        + _inline_mapping(_mapping_value(item.get("expected_roles")))
        + "} act{"
        + _inline_mapping(_mapping_value(item.get("actual_roles")))
        + "} miss{"
        + _inline_mapping(_mapping_value(item.get("missing_roles")))
        + "}"
    )


def _platform_matrix(item: Mapping[str, Any]) -> str:
    """Return expected/actual/missing platform coverage for one device."""
    return (
        "exp{"
        + _inline_mapping(_mapping_value(item.get("expected_platforms")))
        + "} act{"
        + _inline_mapping(_mapping_value(item.get("actual_platforms")))
        + "} miss{"
        + _inline_mapping(_mapping_value(item.get("missing_platforms")))
        + "}"
    )


def _escape_table(value: str) -> str:
    """Escape Markdown table separators."""
    return value.replace("|", "\\|").replace("\n", " ")


def _markdown_value(value: Any) -> str:
    """Return a one-line Markdown-safe diagnostics value."""
    return str(value or "").replace("\n", " ").replace("|", "\\|")
