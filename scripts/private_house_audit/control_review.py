"""Shared control-review rules for private-house coverage classification."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


PRIMARY_CONTROL_ROLE = "primary_control_or_state"
_EVENT_INPUT_CATEGORIES = frozenset({"knob_switch", "scene_panel"})
_TOPOLOGY_CONTEXT_CATEGORIES = frozenset({"gateway"})
_CONFIG_ONLY_CATEGORIES = frozenset({"other"})
_CONFIG_ONLY_ROLES = frozenset({"config", "diagnostic"})


def needs_missing_primary_control_review(
    *,
    category: Any,
    expected_roles: Mapping[str, Any],
    actual_roles: Mapping[str, Any],
    model_writable_properties_count: int,
) -> bool:
    """Return whether writable model properties need a missing-control review."""
    if model_writable_properties_count <= 0:
        return False
    if _role_count(expected_roles, PRIMARY_CONTROL_ROLE) > 0:
        return False
    if _role_count(actual_roles, PRIMARY_CONTROL_ROLE) > 0:
        return False

    category_key = str(category or "").strip()
    if category_key in _EVENT_INPUT_CATEGORIES | _TOPOLOGY_CONTEXT_CATEGORIES:
        return False
    if category_key in _CONFIG_ONLY_CATEGORIES and _roles_covered(
        expected_roles,
        actual_roles,
        allowed_roles=_CONFIG_ONLY_ROLES,
    ):
        return False
    return True


def _roles_covered(
    expected_roles: Mapping[str, Any],
    actual_roles: Mapping[str, Any],
    *,
    allowed_roles: frozenset[str],
) -> bool:
    """Return true when all expected non-primary roles are already covered."""
    expected = {
        str(role): _int_value(count)
        for role, count in expected_roles.items()
        if _int_value(count) > 0
    }
    if not expected:
        return False
    if any(role not in allowed_roles for role in expected):
        return False
    return all(_role_count(actual_roles, role) >= count for role, count in expected.items())


def _role_count(roles: Mapping[str, Any], role: str) -> int:
    """Return one integer role count from diagnostics data."""
    return _int_value(roles.get(role))


def _int_value(value: Any) -> int:
    """Return an int diagnostics value without treating bools as integers."""
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


__all__ = ["PRIMARY_CONTROL_ROLE", "needs_missing_primary_control_review"]
