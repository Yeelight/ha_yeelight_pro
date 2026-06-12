"""Diagnostics-safe property hydration aggregate counters."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PropertyHydrationDiagnostics:
    """Aggregate read-side hydration counters without resource ids or values."""

    request_groups: int = 0
    requested_devices: int = 0
    requested_property_sets: int = 0
    requested_node_properties: int = 0
    response_devices: int = 0
    response_values: int = 0
    merged_devices: int = 0
    merged_values: int = 0
    empty_response_groups: int = 0
    failed_groups: int = 0

    def record_requests(self, requests: dict[tuple[str, ...], list[int | str]]) -> None:
        """Record aggregate request shape without storing property names."""
        self.request_groups = len(requests)
        self.requested_devices = sum(len(resource_ids) for resource_ids in requests.values())
        self.requested_property_sets = sum(len(properties) for properties in requests)
        self.requested_node_properties = sum(
            len(properties) * len(resource_ids)
            for properties, resource_ids in requests.items()
        )

    def record_response(self, values_by_device: dict[str, dict[str, object]]) -> None:
        """Record one response group's parsed values."""
        if not values_by_device:
            self.empty_response_groups += 1
            return
        self.response_devices += len(values_by_device)
        self.response_values += sum(len(values) for values in values_by_device.values())

    def record_failure(self) -> None:
        """Record one non-auth hydration group failure."""
        self.failed_groups += 1

    def record_merge(self, values_by_device: dict[str, dict[str, object]]) -> None:
        """Record final merged values after all response groups."""
        self.merged_devices = len(values_by_device)
        self.merged_values = sum(len(values) for values in values_by_device.values())

    def as_dict(self) -> dict[str, int]:
        """Return JSON-safe aggregate diagnostics."""
        return {
            "request_groups": self.request_groups,
            "requested_devices": self.requested_devices,
            "requested_property_sets": self.requested_property_sets,
            "requested_node_properties": self.requested_node_properties,
            "response_devices": self.response_devices,
            "response_values": self.response_values,
            "merged_devices": self.merged_devices,
            "merged_values": self.merged_values,
            "empty_response_groups": self.empty_response_groups,
            "failed_groups": self.failed_groups,
        }


__all__ = ["PropertyHydrationDiagnostics"]
