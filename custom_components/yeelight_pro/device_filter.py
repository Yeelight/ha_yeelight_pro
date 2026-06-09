"""Non-destructive Yeelight Pro device import filter helpers."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from .device_filter_rules import (
    FILTER_DIMENSIONS,
    distinct_value_counts,
    matches_rules,
    mode,
    normalize_bool,
    rules_with_ignored,
    stored_rules,
)


@dataclass(frozen=True, slots=True)
class DeviceImportFilterPreview:
    """Aggregate-only preview of local device import filtering."""

    enabled: bool
    rules_count: int
    visible_devices: int
    excluded_devices: int
    matched_devices: int
    total_devices: int
    mode: str
    rules_by_dimension: dict[str, int]
    ignored_rule_count: int
    distinct_value_counts_by_dimension: dict[str, int]

    def as_dict(self) -> dict[str, Any]:
        """Return a diagnostics-safe dictionary."""
        return {
            "enabled": self.enabled,
            "rules_count": self.rules_count,
            "visible_devices": self.visible_devices,
            "excluded_devices": self.excluded_devices,
            "matched_devices": self.matched_devices,
            "total_devices": self.total_devices,
            "mode": self.mode,
            "rules_by_dimension": self.rules_by_dimension,
            "ignored_rule_count": self.ignored_rule_count,
            "distinct_value_counts_by_dimension": (
                self.distinct_value_counts_by_dimension
            ),
        }


@dataclass(frozen=True, slots=True)
class NormalizedDeviceImportFilter:
    """Normalized non-destructive device import filter config."""

    enabled: bool
    include: dict[str, set[str]]
    exclude: dict[str, set[str]]
    mode: str
    rules_by_dimension: dict[str, int]
    ignored_rule_count: int

    @property
    def rules_count(self) -> int:
        """Return the number of normalized rule values."""
        return sum(self.rules_by_dimension.values())


def matches_device_import_filter(
    device: Mapping[str, Any],
    filter_config: Mapping[str, Any] | None,
) -> bool:
    """Return whether one device would stay visible after local import filtering."""
    normalized = normalize_device_import_filter(filter_config)
    if not normalized.enabled:
        return True

    if normalized.include and not matches_rules(
        device,
        normalized.include,
        mode=normalized.mode,
    ):
        return False
    return not matches_rules(device, normalized.exclude, mode=normalized.mode)


def preview_device_import_filter(
    devices: Iterable[Mapping[str, Any]],
    filter_config: Mapping[str, Any] | None,
) -> DeviceImportFilterPreview:
    """Return an aggregate preview without filtering runtime devices."""
    device_list = list(devices)
    normalized = normalize_device_import_filter(filter_config)
    value_counts = distinct_value_counts(device_list)

    if not normalized.enabled:
        return DeviceImportFilterPreview(
            enabled=False,
            rules_count=normalized.rules_count,
            visible_devices=len(device_list),
            excluded_devices=0,
            matched_devices=0,
            total_devices=len(device_list),
            mode=normalized.mode,
            rules_by_dimension=normalized.rules_by_dimension,
            ignored_rule_count=normalized.ignored_rule_count,
            distinct_value_counts_by_dimension=value_counts,
        )

    visible = 0
    matched = 0
    for device in device_list:
        include_matched = matches_rules(
            device,
            normalized.include,
            mode=normalized.mode,
        )
        exclude_matched = matches_rules(
            device,
            normalized.exclude,
            mode=normalized.mode,
        )
        if include_matched or exclude_matched:
            matched += 1
        if matches_device_import_filter(device, filter_config):
            visible += 1

    return DeviceImportFilterPreview(
        enabled=True,
        rules_count=normalized.rules_count,
        visible_devices=visible,
        excluded_devices=len(device_list) - visible,
        matched_devices=matched,
        total_devices=len(device_list),
        mode=normalized.mode,
        rules_by_dimension=normalized.rules_by_dimension,
        ignored_rule_count=normalized.ignored_rule_count,
        distinct_value_counts_by_dimension=value_counts,
    )


def normalize_device_import_filter(
    filter_config: Mapping[str, Any] | None,
) -> NormalizedDeviceImportFilter:
    """Normalize filter config into diagnostics-safe rule counts and sets."""
    config = filter_config if isinstance(filter_config, Mapping) else {}
    include_rules, include_ignored = rules_with_ignored(config.get("include"))
    exclude_rules, exclude_ignored = rules_with_ignored(config.get("exclude"))
    rules_by_dimension = {
        dimension: len(include_rules.get(dimension, set()))
        + len(exclude_rules.get(dimension, set()))
        for dimension in FILTER_DIMENSIONS
    }
    rules_by_dimension = {
        dimension: count for dimension, count in rules_by_dimension.items() if count
    }
    rules_count = sum(rules_by_dimension.values())
    return NormalizedDeviceImportFilter(
        enabled=bool(normalize_bool(config.get("enabled", False)) and rules_count),
        include=include_rules,
        exclude=exclude_rules,
        mode=mode(config.get("mode")),
        rules_by_dimension=rules_by_dimension,
        ignored_rule_count=include_ignored + exclude_ignored,
    )


def canonical_device_import_filter(
    filter_config: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Return the canonical config-entry storage shape for import filters."""
    normalized = normalize_device_import_filter(filter_config)
    return {
        "enabled": normalized.enabled,
        "mode": normalized.mode,
        "include": stored_rules(normalized.include),
        "exclude": stored_rules(normalized.exclude),
    }
