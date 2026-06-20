"""Report builders for the private-house projection coverage audit."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from custom_components.yeelight_pro.const import (
    CLOUD_REGION_PUSH_BASE_URLS,
    CONF_CLOUD_REGION,
    CONF_CONNECTION_MODE,
    CONF_HOUSE_ID,
    CONF_LIVE_UPDATES,
    CONF_PRIVATE_DOMAIN,
    CONF_PRIVATE_PUSH_DOMAIN,
    CONNECTION_MODE_CLOUD,
    CONNECTION_MODE_PRIVATE,
    DEFAULT_CLOUD_REGION,
    DEFAULT_LIVE_UPDATES,
)
from custom_components.yeelight_pro.deployment_urls import (
    deployment_private_push_base_url,
)
from custom_components.yeelight_pro.entity_candidate_topology import (
    iter_topology_entity_candidates,
)
from custom_components.yeelight_pro.entity_candidates import (
    iter_device_entity_candidates,
)
from custom_components.yeelight_pro.utils import to_int, to_str
from scripts.private_house_audit.coverage_model import (
    DeviceCoverage,
    TopologyCoverage,
    registry_reload_required,
)
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


def build_report(
    *,
    entry: Mapping[str, Any],
    entry_data: Mapping[str, Any],
    runtime_data: Mapping[int, Mapping[str, Any]],
    registry_entries: Mapping[str, Mapping[str, Any]],
    hydration: Mapping[str, int],
    endpoint_errors: Mapping[str, str],
    install_runtime: Mapping[str, Any] | None = None,
    areas: Sequence[Mapping[str, Any]] | None = None,
    rooms: Sequence[Mapping[str, Any]] | None = None,
    groups: Sequence[Mapping[str, Any]] | None = None,
    houses: Sequence[Mapping[str, Any]] | None = None,
    scenes: Sequence[Mapping[str, Any]] | None = None,
    analytics_enabled: bool = False,
) -> dict[str, Any]:
    """Build full device-by-device coverage report."""
    device_reports = []
    summary_platforms_expected: Counter[str] = Counter()
    summary_platforms_actual: Counter[str] = Counter()
    summary_roles_expected: Counter[str] = Counter()
    summary_roles_actual: Counter[str] = Counter()
    summary_roles_missing: Counter[str] = Counter()
    summary_platforms_missing: Counter[str] = Counter()
    summary_categories: Counter[str] = Counter()
    missing_by_category: Counter[str] = Counter()
    unprojected_readable_by_category: Counter[str] = Counter()
    unprojected_writable_by_category: Counter[str] = Counter()
    unprojected_events_by_category: Counter[str] = Counter()
    for device_id, payload in sorted(runtime_data.items(), key=lambda item: item[0]):
        coverage = _device_coverage(device_id, payload, registry_entries)
        device_reports.append(coverage)
        summary_categories[coverage.category] += 1
        summary_platforms_expected.update(coverage.expected_platforms)
        summary_platforms_actual.update(coverage.actual_platforms)
        summary_roles_expected.update(coverage.expected_roles)
        summary_roles_actual.update(coverage.actual_roles)
        summary_roles_missing.update(coverage.missing_roles)
        summary_platforms_missing.update(coverage.missing_platforms)
        if coverage.missing_total:
            missing_by_category[coverage.category] += 1
        if coverage.unprojected_readable_properties:
            unprojected_readable_by_category[coverage.category] += 1
        if coverage.unprojected_writable_properties:
            unprojected_writable_by_category[coverage.category] += 1
        if coverage.unprojected_events:
            unprojected_events_by_category[coverage.category] += 1
    missing_devices = [item for item in device_reports if item.missing_total]
    online_only = [
        item
        for item in device_reports
        if item.actual_total <= 1 and item.expected_total > item.actual_total
    ]
    low_coverage = [item for item in device_reports if item.low_coverage_reasons]
    low_coverage_by_reason: Counter[str] = Counter()
    schema_gaps: Counter[str] = Counter()
    for item in low_coverage:
        low_coverage_by_reason.update(item.low_coverage_reasons)
    for item in device_reports:
        if item.schema_gap_reason:
            schema_gaps[item.schema_gap_reason] += 1
    topology_reports = _topology_coverage(
        entry_data=entry_data,
        house_id=to_int(entry_data.get(CONF_HOUSE_ID)),
        registry_entries=registry_entries,
        areas=areas or (),
        rooms=rooms or (),
        groups=groups or (),
        houses=houses or (),
        scenes=scenes or (),
        analytics_enabled=analytics_enabled,
    )
    topology_missing_platforms: Counter[str] = Counter()
    topology_missing_roles: Counter[str] = Counter()
    topology_expected_platforms: Counter[str] = Counter()
    topology_actual_platforms: Counter[str] = Counter()
    for item in topology_reports:
        topology_missing_platforms.update(item.missing_platforms)
        topology_missing_roles.update(item.missing_roles)
        topology_expected_platforms.update(item.expected_platforms)
        topology_actual_platforms.update(item.actual_platforms)
    runtime_status = dict(install_runtime or {})
    return {
        "entry": {
            "entry_id": entry.get("entry_id"),
            "title": entry.get("title"),
            "connection_mode": entry_data.get(CONF_CONNECTION_MODE),
            "cloud_region": entry_data.get(CONF_CLOUD_REGION),
            "private_domain": entry_data.get(CONF_PRIVATE_DOMAIN),
            "private_push_domain": entry_data.get(CONF_PRIVATE_PUSH_DOMAIN),
            "effective_push_base_url": _effective_push_base_url(entry_data),
            "live_updates": _live_updates(entry, entry_data),
            "house_id_hash": stable_digest(entry_data.get(CONF_HOUSE_ID)),
        },
        "install_runtime": runtime_status,
        "summary": {
            "device_count": len(device_reports),
            "devices_with_missing_entities": len(missing_devices),
            "devices_actual_online_only_but_expected_more": len(online_only),
            "expected_entities": sum(item.expected_total for item in device_reports),
            "actual_device_entities": sum(item.actual_total for item in device_reports),
            "expected_topology_entities": sum(
                item.expected_total for item in topology_reports
            ),
            "actual_topology_entities": sum(
                item.actual_total for item in topology_reports
            ),
            "missing_topology_entities": sum(
                item.missing_total for item in topology_reports
            ),
            "missing_entities": sum(item.missing_total for item in device_reports),
            "extra_device_entities": sum(item.extra_total for item in device_reports),
            "categories": dict(sorted(summary_categories.items())),
            "expected_platforms": dict(sorted(summary_platforms_expected.items())),
            "actual_platforms": dict(sorted(summary_platforms_actual.items())),
            "expected_roles": dict(sorted(summary_roles_expected.items())),
            "actual_roles": dict(sorted(summary_roles_actual.items())),
            "missing_roles": dict(sorted(summary_roles_missing.items())),
            "missing_platforms": dict(sorted(summary_platforms_missing.items())),
            "topology_expected_platforms": dict(sorted(topology_expected_platforms.items())),
            "topology_actual_platforms": dict(sorted(topology_actual_platforms.items())),
            "topology_missing_platforms": dict(sorted(topology_missing_platforms.items())),
            "topology_missing_roles": dict(sorted(topology_missing_roles.items())),
            "missing_devices_by_category": dict(sorted(missing_by_category.items())),
            "registry_reload_required": registry_reload_required(device_reports),
            "low_coverage_devices": len(low_coverage),
            "low_coverage_by_reason": dict(sorted(low_coverage_by_reason.items())),
            "schema_gaps": dict(sorted(schema_gaps.items())),
            "devices_with_unprojected_readable_properties": sum(
                1 for item in device_reports if item.unprojected_readable_properties
            ),
            "devices_with_unprojected_writable_properties": sum(
                1 for item in device_reports if item.unprojected_writable_properties
            ),
            "devices_with_unprojected_events": sum(
                1 for item in device_reports if item.unprojected_events
            ),
            "unprojected_readable_by_category": dict(
                sorted(unprojected_readable_by_category.items())
            ),
            "unprojected_writable_by_category": dict(
                sorted(unprojected_writable_by_category.items())
            ),
            "unprojected_events_by_category": dict(
                sorted(unprojected_events_by_category.items())
            ),
            "hydration": dict(hydration),
            "endpoint_errors": dict(sorted(endpoint_errors.items())),
            "install_runtime": runtime_status,
        },
        "devices": [item.as_dict() for item in device_reports],
        "topology_entities": [item.as_dict() for item in topology_reports],
    }


def _effective_push_base_url(data: Mapping[str, Any]) -> str | None:
    """Return the WebSocket base URL the live runtime would use."""
    mode = data.get(CONF_CONNECTION_MODE)
    if mode == CONNECTION_MODE_CLOUD:
        region = str(data.get(CONF_CLOUD_REGION) or DEFAULT_CLOUD_REGION)
        return CLOUD_REGION_PUSH_BASE_URLS.get(
            region,
            CLOUD_REGION_PUSH_BASE_URLS[DEFAULT_CLOUD_REGION],
        )
    if mode != CONNECTION_MODE_PRIVATE:
        return None
    private_domain = data.get(CONF_PRIVATE_DOMAIN)
    if not isinstance(private_domain, str) or not private_domain.strip():
        return None
    return deployment_private_push_base_url(
        private_domain,
        data.get(CONF_PRIVATE_PUSH_DOMAIN),
    )


def _live_updates(
    entry: Mapping[str, Any],
    entry_data: Mapping[str, Any],
) -> bool | None:
    """Return normalized live-update intent for report context."""
    mode = entry_data.get(CONF_CONNECTION_MODE)
    if mode not in {CONNECTION_MODE_CLOUD, CONNECTION_MODE_PRIVATE}:
        return False
    options = entry.get("options")
    if not isinstance(options, Mapping):
        return DEFAULT_LIVE_UPDATES
    return bool(options.get(CONF_LIVE_UPDATES, DEFAULT_LIVE_UPDATES))


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


def _topology_coverage(
    *,
    entry_data: Mapping[str, Any],
    house_id: int | None,
    registry_entries: Mapping[str, Mapping[str, Any]],
    areas: Sequence[Mapping[str, Any]],
    rooms: Sequence[Mapping[str, Any]],
    groups: Sequence[Mapping[str, Any]],
    houses: Sequence[Mapping[str, Any]],
    scenes: Sequence[Mapping[str, Any]],
    analytics_enabled: bool,
) -> list[TopologyCoverage]:
    """Return coverage rows for room/area/group/scene/house helper entities."""
    coordinator = _TopologyCandidateCoordinator(
        entry_data=entry_data,
        house_id=house_id,
        areas=areas,
        rooms=rooms,
        groups=groups,
        houses=houses,
        scenes=scenes,
    )
    candidates = list(
        iter_topology_entity_candidates(
            coordinator,
            analytics_enabled=analytics_enabled,
        )
    )
    by_source: dict[str, list[Any]] = {}
    for candidate in candidates:
        by_source.setdefault(candidate.source, []).append(candidate)

    rows: list[TopologyCoverage] = []
    for source, source_candidates in sorted(by_source.items()):
        expected_ids = {item.unique_id: item for item in source_candidates}
        actual_rows = {
            unique_id: registry_entries[unique_id]
            for unique_id in expected_ids
            if unique_id in registry_entries
        }
        missing = [
            expected_ids[unique_id]
            for unique_id in expected_ids
            if unique_id not in actual_rows
        ]
        rows.append(
            TopologyCoverage(
                source=source,
                expected_total=len(expected_ids),
                actual_total=len(actual_rows),
                missing_total=len(missing),
                expected_platforms=dict(sorted(Counter(
                    item.platform for item in source_candidates
                ).items())),
                actual_platforms=dict(sorted(Counter(
                    domain
                    for row in actual_rows.values()
                    if (domain := entity_domain(row))
                ).items())),
                missing_platforms=dict(sorted(Counter(
                    item.platform for item in missing
                ).items())),
                expected_roles=dict(sorted(Counter(
                    candidate_role(item) for item in source_candidates
                ).items())),
                actual_roles=dict(sorted(Counter(
                    actual_row_role(row) for row in actual_rows.values()
                ).items())),
                missing_roles=dict(sorted(Counter(
                    candidate_role(item) for item in missing
                ).items())),
                expected_samples=candidate_samples(source_candidates),
                missing_samples=candidate_samples(missing),
            )
        )
    return rows


class _TopologyCandidateCoordinator:
    """Minimal coordinator shape for topology candidate projection."""

    def __init__(
        self,
        *,
        entry_data: Mapping[str, Any],
        house_id: int | None,
        areas: Sequence[Mapping[str, Any]],
        rooms: Sequence[Mapping[str, Any]],
        groups: Sequence[Mapping[str, Any]],
        houses: Sequence[Mapping[str, Any]],
        scenes: Sequence[Mapping[str, Any]],
    ) -> None:
        self.entry_data = dict(entry_data)
        self.house_id = house_id
        self.areas = [dict(item) for item in areas if isinstance(item, Mapping)]
        self.rooms = [dict(item) for item in rooms if isinstance(item, Mapping)]
        self.groups = [dict(item) for item in groups if isinstance(item, Mapping)]
        self.houses = [dict(item) for item in houses if isinstance(item, Mapping)]
        self.scenes = [dict(item) for item in scenes if isinstance(item, Mapping)]


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



__all__ = ["DeviceCoverage", "build_report"]
