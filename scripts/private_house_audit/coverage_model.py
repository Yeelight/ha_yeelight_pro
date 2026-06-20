"""Coverage models for private-house audit reports."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class DeviceCoverage:
    """Projection coverage facts for one source device."""

    device_hash: str
    name: str
    category: str
    type_value: str
    pid: int | None
    online: bool | None
    params_count: int
    source_evidence: dict[str, Any]
    product_schema: bool
    product_model: bool
    device_instance: bool
    expected_total: int
    actual_total: int
    missing_total: int
    extra_total: int
    expected_platforms: dict[str, int]
    actual_platforms: dict[str, int]
    expected_categories: dict[str, int]
    expected_roles: dict[str, int]
    actual_roles: dict[str, int]
    missing_platforms: dict[str, int]
    missing_roles: dict[str, int]
    model_components_count: int
    model_properties_count: int
    model_readable_properties_count: int
    model_writable_properties_count: int
    model_events_count: int
    model_actions_count: int
    instance_components_count: int
    instance_state_keys_count: int
    projected_component_count: int
    projected_component_ids: list[str]
    expected_samples: list[dict[str, Any]]
    unprojected_readable_properties: list[dict[str, Any]]
    unprojected_writable_properties: list[dict[str, Any]]
    unprojected_events: list[dict[str, Any]]
    schema_gap_reason: str | None = None
    low_coverage_reasons: list[str] = field(default_factory=list)
    param_keys: list[str] = field(default_factory=list)
    missing_samples: list[dict[str, Any]] = field(default_factory=list)
    stale_samples: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        """Return JSON-safe audit data."""
        return {
            "device_hash": self.device_hash,
            "name": self.name,
            "category": self.category,
            "type": self.type_value,
            "pid": self.pid,
            "online": self.online,
            "params_count": self.params_count,
            "source_evidence": self.source_evidence,
            "product_schema": self.product_schema,
            "product_model": self.product_model,
            "device_instance": self.device_instance,
            "expected_total": self.expected_total,
            "actual_total": self.actual_total,
            "missing_total": self.missing_total,
            "extra_total": self.extra_total,
            "expected_platforms": self.expected_platforms,
            "actual_platforms": self.actual_platforms,
            "expected_categories": self.expected_categories,
            "expected_roles": self.expected_roles,
            "actual_roles": self.actual_roles,
            "missing_platforms": self.missing_platforms,
            "missing_roles": self.missing_roles,
            "model_components_count": self.model_components_count,
            "model_properties_count": self.model_properties_count,
            "model_readable_properties_count": self.model_readable_properties_count,
            "model_writable_properties_count": self.model_writable_properties_count,
            "model_events_count": self.model_events_count,
            "model_actions_count": self.model_actions_count,
            "instance_components_count": self.instance_components_count,
            "instance_state_keys_count": self.instance_state_keys_count,
            "projected_component_count": self.projected_component_count,
            "projected_component_ids": self.projected_component_ids,
            "expected_samples": self.expected_samples,
            "unprojected_readable_properties": self.unprojected_readable_properties,
            "unprojected_writable_properties": self.unprojected_writable_properties,
            "unprojected_events": self.unprojected_events,
            "schema_gap_reason": self.schema_gap_reason,
            "low_coverage_reasons": self.low_coverage_reasons,
            "param_keys": self.param_keys,
            "missing_samples": self.missing_samples,
            "stale_samples": self.stale_samples,
        }


@dataclass(slots=True)
class TopologyCoverage:
    """Projection coverage facts for non-device topology entities."""

    source: str
    expected_total: int
    actual_total: int
    missing_total: int
    expected_platforms: dict[str, int]
    actual_platforms: dict[str, int]
    missing_platforms: dict[str, int]
    expected_roles: dict[str, int]
    actual_roles: dict[str, int]
    missing_roles: dict[str, int]
    expected_samples: list[dict[str, Any]]
    missing_samples: list[dict[str, Any]]

    def as_dict(self) -> dict[str, Any]:
        """Return JSON-safe audit data."""
        return {
            "source": self.source,
            "expected_total": self.expected_total,
            "actual_total": self.actual_total,
            "missing_total": self.missing_total,
            "expected_platforms": self.expected_platforms,
            "actual_platforms": self.actual_platforms,
            "missing_platforms": self.missing_platforms,
            "expected_roles": self.expected_roles,
            "actual_roles": self.actual_roles,
            "missing_roles": self.missing_roles,
            "expected_samples": self.expected_samples,
            "missing_samples": self.missing_samples,
        }


def registry_reload_required(device_reports: Sequence[DeviceCoverage]) -> dict[str, Any]:
    """Return whether current HA registry is behind current projection output."""
    missing_platforms: Counter[str] = Counter()
    missing_roles: Counter[str] = Counter()
    missing_categories: Counter[str] = Counter()
    missing_devices = 0
    missing_entities = 0
    for item in device_reports:
        if not item.missing_total:
            continue
        missing_devices += 1
        missing_entities += item.missing_total
        missing_platforms.update(item.missing_platforms)
        missing_roles.update(item.missing_roles)
        missing_categories[item.category] += 1
    return {
        "required": missing_entities > 0,
        "missing_devices": missing_devices,
        "missing_entities": missing_entities,
        "missing_platforms": dict(sorted(missing_platforms.items())),
        "missing_roles": dict(sorted(missing_roles.items())),
        "missing_devices_by_category": dict(sorted(missing_categories.items())),
    }


__all__ = ["DeviceCoverage", "TopologyCoverage", "registry_reload_required"]
