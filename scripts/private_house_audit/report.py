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
from custom_components.yeelight_pro.utils import to_int
from scripts.private_house_audit.coverage_model import registry_reload_required
from scripts.private_house_audit.report_device import _device_coverage
from scripts.private_house_audit.report_topology import _topology_coverage
from scripts.private_house_audit.projection import (
    stable_digest,
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
    for topology_item in topology_reports:
        topology_missing_platforms.update(topology_item.missing_platforms)
        topology_missing_roles.update(topology_item.missing_roles)
        topology_expected_platforms.update(topology_item.expected_platforms)
        topology_actual_platforms.update(topology_item.actual_platforms)
    runtime_status = dict(install_runtime or {})
    return {
        "entry": {
            "entry_id_hash": stable_digest(entry.get("entry_id")),
            "connection_mode": entry_data.get(CONF_CONNECTION_MODE),
            "cloud_region": entry_data.get(CONF_CLOUD_REGION),
            "private_endpoint_configured": bool(entry_data.get(CONF_PRIVATE_DOMAIN)),
            "private_push_endpoint_configured": bool(
                entry_data.get(CONF_PRIVATE_PUSH_DOMAIN)
            ),
            "effective_push_base_url_hash": stable_digest(_effective_push_base_url(entry_data)),
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

__all__ = ["build_report"]
