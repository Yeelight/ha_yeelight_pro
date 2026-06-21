"""Per-device conclusions for private-house coverage audit reports."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from typing import Any

from scripts.private_house_audit.classification_constants import (
    ACTION_FIX_PROJECTION,
    ACTION_INVESTIGATE_SOURCE_DATA,
    ACTION_NO_CODE_CHANGE,
    ACTION_REGISTRY_REFRESH,
    ACTION_SYNC_RUNTIME,
    STATUS_OK,
    STATUS_PROJECTION_GAP,
    STATUS_REGISTRY_STALE,
    STATUS_RUNTIME_DRIFT,
    STATUS_SOURCE_DATA_LIMITED,
)
from scripts.private_house_audit.classification_markdown import markdown_report
from scripts.private_house_audit.classification_rows import classified_device_row
from scripts.private_house_audit.classification_summary import (
    audit_summary,
    classified_topology_row,
    install_runtime_summary,
)
from scripts.private_house_audit.classification_values import (
    has_int_value,
    int_value,
    mapping_value,
    sequence_value,
)
from scripts.private_house_audit.control_review import (
    needs_missing_primary_control_review,
)


def classify_device(
    device: Mapping[str, Any],
    *,
    install_runtime_matches_source: bool = True,
) -> dict[str, Any]:
    """Return a stable, actionable conclusion for one audit device row."""
    missing_total = int_value(device.get("missing_total"))
    extra_total = int_value(device.get("extra_total"))
    unprojected_readable = sequence_value(device.get("unprojected_readable_properties"))
    unprojected_writable = sequence_value(device.get("unprojected_writable_properties"))
    unprojected_events = sequence_value(device.get("unprojected_events"))
    reasons = set(sequence_value(device.get("low_coverage_reasons")))
    missing_platforms = mapping_value(device.get("missing_platforms"))
    expected_platforms = mapping_value(device.get("expected_platforms"))
    actual_platforms = mapping_value(device.get("actual_platforms"))
    params_count = int_value(device.get("params_count"))
    model_components = int_value(device.get("model_components_count"))
    model_writable_properties = int_value(device.get("model_writable_properties_count"))
    expected_total = int_value(device.get("expected_total"))
    actual_total = int_value(device.get("actual_total"))
    has_evidence_counts = has_int_value(device, "params_count") and has_int_value(
        device, "model_components_count"
    )

    if unprojected_readable or unprojected_writable or unprojected_events:
        return {
            "status": STATUS_PROJECTION_GAP,
            "action": ACTION_FIX_PROJECTION,
            "reason": "product_model_capability_not_projected",
        }

    if _registry_differs_from_projection(missing_total, extra_total, missing_platforms):
        if not install_runtime_matches_source:
            return {
                "status": STATUS_RUNTIME_DRIFT,
                "action": ACTION_SYNC_RUNTIME,
                "reason": "installed_runtime_differs_from_source",
            }
        return {
            "status": STATUS_REGISTRY_STALE,
            "action": ACTION_REGISTRY_REFRESH,
            "reason": _registry_stale_reason(device),
        }

    if _limited_source_data(
        reasons=reasons,
        params_count=params_count,
        model_components=model_components,
        category=device.get("category"),
        model_writable_properties=model_writable_properties,
        expected_roles=mapping_value(device.get("expected_roles")),
        actual_roles=mapping_value(device.get("actual_roles")),
        expected_platforms=expected_platforms,
        actual_platforms=actual_platforms,
        source_evidence=mapping_value(device.get("source_evidence")),
        unprojected_writable_properties=device.get("unprojected_writable_properties"),
        expected_total=expected_total,
        actual_total=actual_total,
        has_evidence_counts=has_evidence_counts,
    ):
        return {
            "status": STATUS_SOURCE_DATA_LIMITED,
            "action": ACTION_INVESTIGATE_SOURCE_DATA,
            "reason": _source_limited_reason(device),
        }

    return {
        "status": STATUS_OK,
        "action": ACTION_NO_CODE_CHANGE,
        "reason": "projected_entities_match_current_registry_and_known_capabilities",
    }


def classify_report(report: Mapping[str, Any]) -> dict[str, Any]:
    """Return aggregate and per-device conclusions for a full audit report."""
    source_audit_summary = mapping_value(report.get("summary"))
    install_runtime = mapping_value(report.get("install_runtime"))
    if not install_runtime:
        install_runtime = mapping_value(source_audit_summary.get("install_runtime"))
    install_runtime_matches_source = bool(
        install_runtime.get("matched_source", True)
    )
    devices = [
        classified_device_row(
            device,
            classify_device(
                device,
                install_runtime_matches_source=install_runtime_matches_source,
            ),
        )
        for device in sequence_value(report.get("devices"))
        if isinstance(device, Mapping)
    ]
    topology_entities = [
        classified_topology_row(item)
        for item in sequence_value(report.get("topology_entities"))
        if isinstance(item, Mapping)
    ]
    statuses = Counter(item["conclusion"]["status"] for item in devices)
    actions = Counter(item["conclusion"]["action"] for item in devices)
    topology_statuses = Counter(
        item["conclusion"]["status"] for item in topology_entities
    )
    topology_actions = Counter(
        item["conclusion"]["action"] for item in topology_entities
    )
    return {
        "summary": {
            "device_count": len(devices),
            "statuses": dict(sorted(statuses.items())),
            "actions": dict(sorted(actions.items())),
            "topology_count": len(topology_entities),
            "topology_statuses": dict(sorted(topology_statuses.items())),
            "topology_actions": dict(sorted(topology_actions.items())),
            "audit": audit_summary(source_audit_summary),
            "install_runtime": install_runtime_summary(install_runtime),
        },
        "devices": devices,
        "topology_entities": topology_entities,
    }


def _registry_differs_from_projection(
    missing_total: int,
    extra_total: int,
    missing_platforms: Mapping[str, Any],
) -> bool:
    """Return whether current projection and HA registry do not match."""
    return (missing_total > 0 and bool(missing_platforms)) or extra_total > 0


def _registry_stale_reason(device: Mapping[str, Any]) -> str:
    """Return a precise stale-registry reason for one device."""
    if _has_platform_changed_sample_pair(device):
        return "entity_platform_changed"
    return "current_projection_differs_from_ha_registry"


def _has_platform_changed_sample_pair(device: Mapping[str, Any]) -> bool:
    """Return true when stale/missing samples show the same logical entity changed domain."""
    missing = [
        sample
        for sample in sequence_value(device.get("missing_samples"))
        if isinstance(sample, Mapping)
    ]
    stale = [
        sample
        for sample in sequence_value(device.get("stale_samples"))
        if isinstance(sample, Mapping)
    ]
    if not missing or not stale:
        return False
    stale_pairs = {
        (_logical_component_key(sample), str(sample.get("platform") or ""))
        for sample in stale
    }
    return any(
        stale_key == _logical_component_key(sample)
        and stale_platform != str(sample.get("platform") or "")
        for sample in missing
        for stale_key, stale_platform in stale_pairs
    )


def _logical_component_key(sample: Mapping[str, Any]) -> str:
    """Return component identity without the final HA platform suffix."""
    component_id = str(sample.get("component_id") or "")
    platform = str(sample.get("platform") or "")
    suffix = f"_{platform}"
    if platform and component_id.endswith(suffix):
        return component_id[: -len(suffix)]
    return component_id


def _limited_source_data(
    *,
    reasons: set[Any],
    params_count: int,
    model_components: int,
    category: Any,
    model_writable_properties: int,
    expected_roles: Mapping[str, Any],
    actual_roles: Mapping[str, Any],
    expected_platforms: Mapping[str, Any],
    actual_platforms: Mapping[str, Any],
    source_evidence: Mapping[str, Any],
    unprojected_writable_properties: Any,
    expected_total: int,
    actual_total: int,
    has_evidence_counts: bool,
) -> bool:
    """Return true when low coverage is caused by limited source evidence."""
    if needs_missing_primary_control_review(
        category=category,
        expected_roles=expected_roles,
        actual_roles=actual_roles,
        expected_platforms=expected_platforms,
        actual_platforms=actual_platforms,
        source_evidence=source_evidence,
        unprojected_writable_properties=unprojected_writable_properties,
        model_writable_properties_count=model_writable_properties,
    ):
        return True
    if "unknown_category" in reasons or "missing_product_model" in reasons:
        return True
    if (
        "low_runtime_property_evidence" in reasons
        and model_components <= 1
        and actual_total <= 1
        and expected_total <= 1
    ):
        return True
    return (
        has_evidence_counts
        and params_count <= 1
        and model_components <= 1
        and expected_total <= 1
        and actual_total <= 1
    )


def _source_limited_reason(device: Mapping[str, Any]) -> str:
    """Return a precise source-data reason without exposing raw values."""
    evidence = mapping_value(device.get("source_evidence"))
    raw_property_count = int_value(evidence.get("raw_property_count"))
    raw_property_value_count = int_value(evidence.get("raw_property_value_count"))
    raw_property_keys = set(sequence_value(evidence.get("raw_property_keys")))
    product_model_available = bool(evidence.get("product_model_available"))
    product_schema_available = bool(evidence.get("product_schema_available"))
    model_writable_properties = int_value(device.get("model_writable_properties_count"))
    expected_roles = mapping_value(device.get("expected_roles"))
    actual_roles = mapping_value(device.get("actual_roles"))
    expected_platforms = mapping_value(device.get("expected_platforms"))
    actual_platforms = mapping_value(device.get("actual_platforms"))
    documented_online_keys = {"o"}
    if needs_missing_primary_control_review(
        category=device.get("category"),
        expected_roles=expected_roles,
        actual_roles=actual_roles,
        expected_platforms=expected_platforms,
        actual_platforms=actual_platforms,
        source_evidence=evidence,
        unprojected_writable_properties=device.get("unprojected_writable_properties"),
        model_writable_properties_count=model_writable_properties,
    ):
        return "writable_model_properties_without_strict_control_projection"
    if (
        raw_property_count > 1
        and raw_property_keys - documented_online_keys
        and not product_model_available
        and not product_schema_available
    ):
        if raw_property_value_count <= 1:
            return (
                "open_api_payload_lists_undocumented_property_ids_without_values_or_supported_model"
            )
        return "open_api_payload_has_undocumented_raw_properties_without_supported_model"
    return "open_api_payload_has_only_online_or_unknown_capability_evidence"


__all__ = [
    "ACTION_FIX_PROJECTION",
    "ACTION_INVESTIGATE_SOURCE_DATA",
    "ACTION_NO_CODE_CHANGE",
    "ACTION_REGISTRY_REFRESH",
    "ACTION_SYNC_RUNTIME",
    "STATUS_OK",
    "STATUS_PROJECTION_GAP",
    "STATUS_REGISTRY_STALE",
    "STATUS_RUNTIME_DRIFT",
    "STATUS_SOURCE_DATA_LIMITED",
    "classify_device",
    "classify_report",
    "markdown_report",
]
