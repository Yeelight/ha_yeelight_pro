"""Aggregate and topology rows for private-house classification reports."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from scripts.private_house_audit.classification_constants import (
    ACTION_NO_CODE_CHANGE,
    ACTION_REGISTRY_REFRESH,
    STATUS_OK,
    STATUS_REGISTRY_STALE,
)
from scripts.private_house_audit.classification_values import (
    int_value,
    mapping_value,
    sequence_value,
)


def classified_topology_row(item: Mapping[str, Any]) -> dict[str, Any]:
    """Return JSON-safe topology coverage facts plus an actionable conclusion."""
    missing_total = int_value(item.get("missing_total"))
    missing_platforms = dict(sorted(mapping_value(item.get("missing_platforms")).items()))
    if missing_total > 0 and missing_platforms:
        conclusion = {
            "status": STATUS_REGISTRY_STALE,
            "action": ACTION_REGISTRY_REFRESH,
            "reason": "topology_entities_missing_from_registry",
        }
    else:
        conclusion = {
            "status": STATUS_OK,
            "action": ACTION_NO_CODE_CHANGE,
            "reason": "topology_entities_match_current_registry",
        }
    source = str(item.get("source") or "")
    expected_roles = dict(sorted(mapping_value(item.get("expected_roles")).items()))
    actual_roles = dict(sorted(mapping_value(item.get("actual_roles")).items()))
    missing_roles = dict(sorted(mapping_value(item.get("missing_roles")).items()))
    expected_platforms = dict(
        sorted(mapping_value(item.get("expected_platforms")).items())
    )
    actual_platforms = dict(sorted(mapping_value(item.get("actual_platforms")).items()))
    return {
        "name": f"topology:{source}" if source else "topology",
        "category": "topology",
        "source": source,
        "actual_total": int_value(item.get("actual_total")),
        "expected_total": int_value(item.get("expected_total")),
        "missing_total": missing_total,
        "extra_total": 0,
        "expected_roles": expected_roles,
        "actual_roles": actual_roles,
        "missing_roles": missing_roles,
        "expected_platforms": expected_platforms,
        "actual_platforms": actual_platforms,
        "missing_platforms": missing_platforms,
        "expected_samples": [
            dict(sample)
            for sample in sequence_value(item.get("expected_samples"))
            if isinstance(sample, Mapping)
        ],
        "missing_samples": [
            dict(sample)
            for sample in sequence_value(item.get("missing_samples"))
            if isinstance(sample, Mapping)
        ],
        "conclusion": conclusion,
    }


def install_runtime_summary(status: Mapping[str, Any]) -> dict[str, Any]:
    """Return source/install runtime drift facts needed for acceptance."""
    if not status:
        return {}
    return {
        "matched_source": bool(status.get("matched_source", True)),
        "missing_files": int_value(status.get("missing_files")),
        "extra_files": int_value(status.get("extra_files")),
        "changed_files": int_value(status.get("changed_files")),
        "missing_samples": [
            str(item) for item in sequence_value(status.get("missing_samples"))
        ],
        "extra_samples": [
            str(item) for item in sequence_value(status.get("extra_samples"))
        ],
        "changed_samples": [
            str(item) for item in sequence_value(status.get("changed_samples"))
        ],
    }


def audit_summary(summary: Mapping[str, Any]) -> dict[str, Any]:
    """Return report-level facts needed to audit classifier conclusions."""
    if not summary:
        return {}
    return {
        "actual_device_entities": int_value(summary.get("actual_device_entities")),
        "actual_topology_entities": int_value(summary.get("actual_topology_entities")),
        "devices_with_unprojected_events": int_value(
            summary.get("devices_with_unprojected_events")
        ),
        "devices_with_unprojected_readable_properties": int_value(
            summary.get("devices_with_unprojected_readable_properties")
        ),
        "devices_with_unprojected_writable_properties": int_value(
            summary.get("devices_with_unprojected_writable_properties")
        ),
        "endpoint_errors": dict(
            sorted(mapping_value(summary.get("endpoint_errors")).items())
        ),
        "expected_entities": int_value(summary.get("expected_entities")),
        "expected_topology_entities": int_value(
            summary.get("expected_topology_entities")
        ),
        "extra_device_entities": int_value(summary.get("extra_device_entities")),
        "hydration": dict(sorted(mapping_value(summary.get("hydration")).items())),
        "missing_entities": int_value(summary.get("missing_entities")),
        "missing_topology_entities": int_value(
            summary.get("missing_topology_entities")
        ),
        "missing_platforms": dict(
            sorted(mapping_value(summary.get("missing_platforms")).items())
        ),
        "topology_actual_platforms": dict(
            sorted(mapping_value(summary.get("topology_actual_platforms")).items())
        ),
        "topology_expected_platforms": dict(
            sorted(mapping_value(summary.get("topology_expected_platforms")).items())
        ),
        "topology_missing_platforms": dict(
            sorted(mapping_value(summary.get("topology_missing_platforms")).items())
        ),
        "topology_missing_roles": dict(
            sorted(mapping_value(summary.get("topology_missing_roles")).items())
        ),
        "schema_gaps": dict(sorted(mapping_value(summary.get("schema_gaps")).items())),
        "install_runtime": install_runtime_summary(
            mapping_value(summary.get("install_runtime"))
        ),
    }
