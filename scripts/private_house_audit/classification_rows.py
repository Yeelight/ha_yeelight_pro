"""Per-device row shaping for private-house coverage classifications."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from scripts.private_house_audit.control_coverage import (
    control_absence_reason,
    strict_control_counts,
)
from scripts.private_house_audit.control_review import (
    needs_missing_primary_control_review,
)


def classified_device_row(
    device: Mapping[str, Any],
    conclusion: Mapping[str, Any],
) -> dict[str, Any]:
    """Return JSON-safe device facts plus an actionable conclusion."""
    expected_roles = _sorted_mapping(device.get("expected_roles"))
    actual_roles = _sorted_mapping(device.get("actual_roles"))
    missing_roles = _sorted_mapping(device.get("missing_roles"))
    expected_platforms = _sorted_mapping(device.get("expected_platforms"))
    actual_platforms = _sorted_mapping(device.get("actual_platforms"))
    missing_platforms = _sorted_mapping(device.get("missing_platforms"))
    strict_controls = strict_control_counts(
        expected_platforms=expected_platforms,
        actual_platforms=actual_platforms,
        missing_platforms=missing_platforms,
    )
    expected_total = _int_value(device.get("expected_total"))
    actual_total = _int_value(device.get("actual_total"))
    missing_total = _int_value(device.get("missing_total"))
    extra_total = _int_value(device.get("extra_total"))
    category = str(device.get("category") or "")
    low_coverage_reasons = list(_sequence_value(device.get("low_coverage_reasons")))
    params_count = _int_value(device.get("params_count"))
    model_components_count = _int_value(device.get("model_components_count"))
    model_properties_count = _int_value(device.get("model_properties_count"))
    model_writable_properties_count = _int_value(device.get("model_writable_properties_count"))
    model_events_count = _int_value(device.get("model_events_count"))
    instance_state_keys_count = _int_value(device.get("instance_state_keys_count"))
    return {
        "name": str(device.get("name") or ""),
        "category": category,
        "type": str(device.get("type") or ""),
        "pid": device.get("pid") if isinstance(device.get("pid"), int) else None,
        "online": device.get("online") if isinstance(device.get("online"), bool) else None,
        "product_schema": bool(device.get("product_schema")),
        "product_model": bool(device.get("product_model")),
        "device_instance": bool(device.get("device_instance")),
        "actual_total": actual_total,
        "expected_total": expected_total,
        "missing_total": missing_total,
        "extra_total": extra_total,
        "missing_platforms": missing_platforms,
        "missing_roles": missing_roles,
        "expected_roles": expected_roles,
        "actual_roles": actual_roles,
        "expected_platforms": expected_platforms,
        "actual_platforms": actual_platforms,
        "coverage_view": _coverage_view(
            conclusion,
            expected_roles=expected_roles,
            actual_roles=actual_roles,
            missing_roles=missing_roles,
            expected_platforms=expected_platforms,
            actual_platforms=actual_platforms,
            missing_platforms=missing_platforms,
            strict_controls=strict_controls,
            source_evidence=_mapping_value(device.get("source_evidence")),
            unprojected_writable_properties=device.get("unprojected_writable_properties"),
            category=category,
            expected_total=expected_total,
            actual_total=actual_total,
            missing_total=missing_total,
            extra_total=extra_total,
            params_count=params_count,
            model_components_count=model_components_count,
            model_properties_count=model_properties_count,
            model_writable_properties_count=model_writable_properties_count,
            model_events_count=model_events_count,
            instance_state_keys_count=instance_state_keys_count,
            low_coverage_reasons=low_coverage_reasons,
        ),
        "source_evidence": _mapping_value(device.get("source_evidence")),
        "params_count": params_count,
        "model_components_count": model_components_count,
        "model_properties_count": model_properties_count,
        "model_readable_properties_count": _int_value(
            device.get("model_readable_properties_count")
        ),
        "model_writable_properties_count": model_writable_properties_count,
        "model_events_count": model_events_count,
        "model_actions_count": _int_value(device.get("model_actions_count")),
        "instance_components_count": _int_value(device.get("instance_components_count")),
        "instance_state_keys_count": instance_state_keys_count,
        "projected_component_count": _int_value(device.get("projected_component_count")),
        "projected_component_ids": list(_sequence_value(device.get("projected_component_ids"))),
        "unprojected_writable_properties": [
            dict(sample)
            for sample in _sequence_value(device.get("unprojected_writable_properties"))
            if isinstance(sample, Mapping)
        ],
        "strict_control": {
            **strict_controls,
            "absence_reason": control_absence_reason(device),
        },
        "expected_samples": [
            dict(sample)
            for sample in _sequence_value(device.get("expected_samples"))
            if isinstance(sample, Mapping)
        ],
        "schema_gap_reason": str(device.get("schema_gap_reason") or ""),
        "param_keys": list(_sequence_value(device.get("param_keys"))),
        "low_coverage_reasons": low_coverage_reasons,
        "missing_samples": [
            dict(sample)
            for sample in _sequence_value(device.get("missing_samples"))
            if isinstance(sample, Mapping)
        ],
        "stale_samples": [
            dict(sample)
            for sample in _sequence_value(device.get("stale_samples"))
            if isinstance(sample, Mapping)
        ],
        "conclusion": dict(conclusion),
    }


def _coverage_view(
    conclusion: Mapping[str, Any],
    *,
    expected_roles: Mapping[str, Any],
    actual_roles: Mapping[str, Any],
    missing_roles: Mapping[str, Any],
    expected_platforms: Mapping[str, Any],
    actual_platforms: Mapping[str, Any],
    missing_platforms: Mapping[str, Any],
    strict_controls: Mapping[str, int],
    source_evidence: Mapping[str, Any],
    unprojected_writable_properties: Any,
    category: str,
    expected_total: int,
    actual_total: int,
    missing_total: int,
    extra_total: int,
    params_count: int,
    model_components_count: int,
    model_properties_count: int,
    model_writable_properties_count: int,
    model_events_count: int,
    instance_state_keys_count: int,
    low_coverage_reasons: Sequence[Any],
) -> dict[str, Any]:
    """Return user-facing coverage buckets for device-by-device acceptance."""
    source_limited = str(conclusion.get("status") or "") == "source_data_limited"
    control_attention = _control_attention(
        category=category,
        expected_roles=expected_roles,
        actual_roles=actual_roles,
        expected_platforms=expected_platforms,
        actual_platforms=actual_platforms,
        source_evidence=source_evidence,
        unprojected_writable_properties=unprojected_writable_properties,
        model_writable_properties_count=model_writable_properties_count,
        source_limited=source_limited,
    )
    return {
        "control": _bucket_state(
            expected=_int_value(strict_controls.get("expected")),
            actual=_int_value(strict_controls.get("actual")),
            missing=_int_value(strict_controls.get("missing")),
            source_limited=source_limited,
            attention=control_attention,
        ),
        "sensor": _bucket_state(
            expected=_platform_count(expected_platforms, "binary_sensor")
            + _platform_count(expected_platforms, "sensor"),
            actual=_platform_count(actual_platforms, "binary_sensor")
            + _platform_count(actual_platforms, "sensor"),
            missing=_platform_count(missing_platforms, "binary_sensor")
            + _platform_count(missing_platforms, "sensor"),
            source_limited=source_limited,
        ),
        "diagnostic": _bucket_state(
            expected=_role_count(expected_roles, "diagnostic"),
            actual=_role_count(actual_roles, "diagnostic"),
            missing=_role_count(missing_roles, "diagnostic"),
            source_limited=source_limited,
        ),
        "config": _bucket_state(
            expected=_role_count(expected_roles, "config"),
            actual=_role_count(actual_roles, "config"),
            missing=_role_count(missing_roles, "config"),
            source_limited=source_limited,
        ),
        "event": _bucket_state(
            expected=_role_count(expected_roles, "event"),
            actual=_role_count(actual_roles, "event"),
            missing=_role_count(missing_roles, "event"),
            source_limited=source_limited,
        ),
        "state_evidence": _state_evidence(
            params_count=params_count,
            model_components_count=model_components_count,
            model_properties_count=model_properties_count,
            model_events_count=model_events_count,
            instance_state_keys_count=instance_state_keys_count,
            source_limited=source_limited,
        ),
        "summary": _coverage_summary(
            conclusion,
            expected_total=expected_total,
            actual_total=actual_total,
            missing_total=missing_total,
            extra_total=extra_total,
            low_coverage_reasons=low_coverage_reasons,
        ),
    }


def _bucket_state(
    *,
    expected: int,
    actual: int,
    missing: int,
    source_limited: bool,
    attention: str = "",
) -> dict[str, Any]:
    """Return one coverage bucket verdict."""
    if attention:
        status = "needs_review"
    elif expected <= 0:
        status = "not_expected"
    elif missing > 0:
        status = "missing_from_registry"
    elif actual >= expected:
        status = "covered"
    elif source_limited:
        status = "source_limited"
    else:
        status = "partial"
    result = {
        "expected": expected,
        "actual": actual,
        "missing": missing,
        "status": status,
    }
    if attention:
        result["attention"] = attention
    return result


def _control_attention(
    *,
    category: str,
    expected_roles: Mapping[str, Any],
    actual_roles: Mapping[str, Any],
    expected_platforms: Mapping[str, Any],
    actual_platforms: Mapping[str, Any],
    source_evidence: Mapping[str, Any],
    unprojected_writable_properties: Any,
    model_writable_properties_count: int,
    source_limited: bool,
) -> str:
    """Return why a control bucket deserves manual review."""
    if not source_limited:
        return ""
    if not needs_missing_primary_control_review(
        category=category,
        expected_roles=expected_roles,
        actual_roles=actual_roles,
        expected_platforms=expected_platforms,
        actual_platforms=actual_platforms,
        source_evidence=source_evidence,
        unprojected_writable_properties=unprojected_writable_properties,
        model_writable_properties_count=model_writable_properties_count,
    ):
        return ""
    return "model_has_writable_properties_but_no_strict_control"


def _state_evidence(
    *,
    params_count: int,
    model_components_count: int,
    model_properties_count: int,
    model_events_count: int,
    instance_state_keys_count: int,
    source_limited: bool,
) -> dict[str, Any]:
    """Return whether source data had enough state/model evidence."""
    if source_limited:
        status = "source_limited"
    elif model_properties_count or model_events_count or instance_state_keys_count:
        status = "covered"
    elif model_components_count:
        status = "component_only"
    else:
        status = "online_only"
    return {
        "params_count": params_count,
        "model_components_count": model_components_count,
        "model_properties_count": model_properties_count,
        "model_events_count": model_events_count,
        "instance_state_keys_count": instance_state_keys_count,
        "status": status,
    }


def _coverage_summary(
    conclusion: Mapping[str, Any],
    *,
    expected_total: int,
    actual_total: int,
    missing_total: int,
    extra_total: int,
    low_coverage_reasons: Sequence[Any],
) -> str:
    """Return one concise acceptance-oriented summary."""
    status = str(conclusion.get("status") or "")
    reason = str(conclusion.get("reason") or "")
    if status == "ok":
        return f"covered: {actual_total}/{expected_total} expected entities present"
    if status == "registry_stale":
        return (
            f"registry stale: {missing_total} missing and {extra_total} stale/extra; "
            f"{reason}"
        )
    if status == "source_data_limited":
        details = ",".join(str(item) for item in low_coverage_reasons)
        return f"source data limited: {details}"
    if status == "projection_gap":
        return f"projection gap: {reason}"
    return reason


def _role_count(roles: Mapping[str, Any], role: str) -> int:
    """Return one integer role count."""
    return _int_value(roles.get(role))


def _platform_count(platforms: Mapping[str, Any], platform: str) -> int:
    """Return one integer platform count."""
    return _int_value(platforms.get(platform))


def _sorted_mapping(value: Any) -> dict[str, Any]:
    """Return a sorted mapping diagnostics object."""
    if not isinstance(value, Mapping):
        return {}
    return dict(sorted(value.items()))


def _mapping_value(value: Any) -> dict[str, Any]:
    """Return a JSON-safe shallow mapping value."""
    if not isinstance(value, Mapping):
        return {}
    return dict(value)


def _sequence_value(value: Any) -> Sequence[Any]:
    """Return sequence diagnostics or an empty tuple, excluding strings."""
    return value if isinstance(value, Sequence) and not isinstance(value, str) else ()


def _int_value(value: Any) -> int:
    """Return an int diagnostics value without treating bools as integers."""
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


__all__ = ["classified_device_row"]
