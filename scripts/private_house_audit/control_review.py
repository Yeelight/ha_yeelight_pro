"""Backward-compatible control-review facade for private-house classification."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from scripts.private_house_audit.control_coverage import (
    PRIMARY_CONTROL_ROLE,
    needs_missing_strict_control_review,
)


def needs_missing_primary_control_review(
    *,
    category: Any,
    expected_roles: Mapping[str, Any],
    actual_roles: Mapping[str, Any],
    expected_platforms: Mapping[str, Any] | None = None,
    actual_platforms: Mapping[str, Any] | None = None,
    source_evidence: Mapping[str, Any] | None = None,
    unprojected_writable_properties: Sequence[Any] | None = None,
    model_writable_properties_count: int,
) -> bool:
    """Return whether writable model properties need missing-control review."""
    return needs_missing_strict_control_review(
        category=category,
        expected_roles=expected_roles,
        actual_roles=actual_roles,
        expected_platforms=expected_platforms or {},
        actual_platforms=actual_platforms or {},
        source_evidence=source_evidence,
        unprojected_writable_properties=unprojected_writable_properties,
        model_writable_properties_count=model_writable_properties_count,
    )


__all__ = ["PRIMARY_CONTROL_ROLE", "needs_missing_primary_control_review"]
