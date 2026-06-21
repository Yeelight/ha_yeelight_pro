"""Device coverage helpers for private-house audit reports."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from custom_components.yeelight_pro.entity_candidates import iter_device_entity_candidates
from custom_components.yeelight_pro.utils import to_int, to_str
from scripts.private_house_audit.coverage_model import DeviceCoverage
from scripts.private_house_audit.inventory import property_inventory
from scripts.private_house_audit.projection import (
    device_category,
    device_name,
    online,
    projected_component_ids,
    projected_property_keys,
    runtime_property_keys,
    safe_param_keys,
    schema_gap_reason,
    stable_digest,
    unprojected_event_samples,
    unprojected_property_samples,
)
from scripts.private_house_audit.report_samples import (
    actual_row_role,
    candidate_role,
    candidate_samples,
    entity_domain,
    source_evidence,
    registry_samples,
)



def _device_coverage(
    device_id: int,
    payload: Mapping[str, Any],
    registry_entries: Mapping[str, Mapping[str, Any]],
) -> DeviceCoverage:
    """Return expected vs actual coverage for one source device."""
    expected = list(iter_device_entity_candidates(payload, hide_unknown_entities=True))
    expected_ids = {item.unique_id: item for item in expected}
    actual_rows = {
        unique_id: row
        for unique_id, row in registry_entries.items()
        if unique_id in expected_ids or _unique_id_belongs_to_device(unique_id, device_id)
    }
    missing_ids = [unique_id for unique_id in expected_ids if unique_id not in actual_rows]
    extra_ids = [unique_id for unique_id in actual_rows if unique_id not in expected_ids]
    missing_candidates = [expected_ids[unique_id] for unique_id in missing_ids]
    expected_platforms = Counter(item.platform for item in expected)
    actual_platforms = Counter(
        domain for row in actual_rows.values() if (domain := entity_domain(row))
    )
    expected_categories = Counter(item.entity_category or "primary" for item in expected)
    missing_platforms = Counter(item.platform for item in missing_candidates)
    expected_roles = Counter(candidate_role(item) for item in expected)
    actual_roles = Counter(actual_row_role(row) for row in actual_rows.values())
    missing_roles = Counter(candidate_role(item) for item in missing_candidates)
    inventory = property_inventory(payload)
    projected_ids = projected_component_ids(expected)
    projected_keys = projected_property_keys(payload, expected)
    runtime_keys = runtime_property_keys(payload)
    unprojected_readable = unprojected_property_samples(
        inventory["readable_properties"],
        projected_keys,
        runtime_keys=runtime_keys,
    )
    unprojected_writable = unprojected_property_samples(
        inventory["writable_properties"],
        projected_keys,
        runtime_keys=runtime_keys,
    )
    unprojected_events = unprojected_event_samples(
        inventory["events"],
        projected_ids,
    )
    return DeviceCoverage(
        device_hash=stable_digest(device_id),
        name=device_name(payload),
        category=device_category(payload),
        type_value=to_str(payload.get("type")) or "",
        pid=to_int(payload.get("pid")),
        online=online(payload),
        params_count=len(payload.get("params") or {})
        if isinstance(payload.get("params"), Mapping)
        else 0,
        source_evidence=source_evidence(payload, inventory),
        product_schema=isinstance(payload.get("product_schema"), Mapping),
        product_model=isinstance(payload.get("ha_product_model"), Mapping),
        device_instance=isinstance(payload.get("ha_device_instance"), Mapping),
        expected_total=len(expected_ids),
        actual_total=len(actual_rows),
        missing_total=len(missing_ids),
        extra_total=len(extra_ids),
        expected_platforms=dict(sorted(expected_platforms.items())),
        actual_platforms=dict(sorted((k, v) for k, v in actual_platforms.items() if k)),
        expected_categories=dict(sorted(expected_categories.items())),
        expected_roles=dict(sorted(expected_roles.items())),
        actual_roles=dict(sorted(actual_roles.items())),
        missing_platforms=dict(sorted(missing_platforms.items())),
        missing_roles=dict(sorted(missing_roles.items())),
        model_components_count=inventory["model_components_count"],
        model_properties_count=inventory["model_properties_count"],
        model_readable_properties_count=len(inventory["readable_properties"]),
        model_writable_properties_count=len(inventory["writable_properties"]),
        model_events_count=len(inventory["events"]),
        model_actions_count=inventory["model_actions_count"],
        instance_components_count=inventory["instance_components_count"],
        instance_state_keys_count=inventory["instance_state_keys_count"],
        projected_component_count=len(projected_ids),
        projected_component_ids=projected_ids[:24],
        expected_samples=candidate_samples(expected),
        unprojected_readable_properties=unprojected_readable,
        unprojected_writable_properties=unprojected_writable,
        unprojected_events=unprojected_events,
        schema_gap_reason=schema_gap_reason(payload),
        low_coverage_reasons=_low_coverage_reasons(
            payload,
            expected,
            actual_rows,
            property_inventory=inventory,
            unprojected_readable=unprojected_readable,
            unprojected_writable=unprojected_writable,
            unprojected_events=unprojected_events,
        ),
        param_keys=safe_param_keys(payload),
        missing_samples=candidate_samples(missing_candidates),
        stale_samples=registry_samples(
            (actual_rows[unique_id] for unique_id in extra_ids),
        ),
    )


def _unique_id_belongs_to_device(unique_id: str, device_id: int) -> bool:
    """Best-effort device unique-id membership for stale/extra rows."""
    marker = f"_device_{device_id}_"
    return marker in unique_id or unique_id.endswith(f"_device_{device_id}")


def _low_coverage_reasons(
    payload: Mapping[str, Any],
    expected: Sequence[Any],
    actual_rows: Mapping[str, Mapping[str, Any]],
    *,
    property_inventory: Mapping[str, Any],
    unprojected_readable: Sequence[Mapping[str, Any]],
    unprojected_writable: Sequence[Mapping[str, Any]],
    unprojected_events: Sequence[Mapping[str, Any]],
) -> list[str]:
    """Classify devices that need manual capability review."""
    reasons: list[str] = []
    expected_total = len({item.unique_id for item in expected})
    actual_total = len(actual_rows)
    category = device_category(payload)
    params = payload.get("params")
    params_count = len(params) if isinstance(params, Mapping) else 0
    has_product_model = isinstance(payload.get("ha_product_model"), Mapping)

    if expected_total == 0:
        reasons.append("no_expected_entities")
    if expected_total <= 1 and actual_total <= 1:
        reasons.append("single_or_no_entity")
    if category == "unknown":
        reasons.append("unknown_category")
    if not has_product_model:
        reasons.append("missing_product_model")
    if params_count <= 1 and expected_total <= 2:
        reasons.append("low_runtime_property_evidence")
    if property_inventory.get("model_properties_count", 0) and unprojected_readable:
        reasons.append("has_unprojected_readable_properties")
    if property_inventory.get("model_properties_count", 0) and unprojected_writable:
        reasons.append("has_unprojected_writable_properties")
    if property_inventory.get("events") and unprojected_events:
        reasons.append("has_unprojected_events")
    return reasons

__all__ = ["_device_coverage"]
