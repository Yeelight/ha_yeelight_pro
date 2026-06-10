"""Home Assistant Repairs issues for Yeelight Pro."""
from __future__ import annotations

from hashlib import sha256
from typing import Any, Mapping

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN
from .core.topology_diff import TOPOLOGY_COLLECTIONS, empty_topology_diff

TOPOLOGY_CHANGED_ISSUE = "device_topology_changed_{entry_id}_{generation}"
_TOPOLOGY_DIFF_COLLECTION_KEYS = frozenset(
    {"added", "removed", "metadata_changed"}
)
_TOPOLOGY_DIFF_COUNT_KEYS = frozenset(
    {
        "previous_generation",
        "current_generation",
        "total_added",
        "total_removed",
        "total_metadata_changed",
        "total_changes",
    }
)
_TOPOLOGY_DIFF_CATEGORIES = frozenset(TOPOLOGY_COLLECTIONS)


def async_create_topology_changed_issue(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: Any,
    *,
    previous_generation: int,
) -> None:
    """Create a Repairs issue when the Yeelight device topology changes."""
    counts = _topology_counts(coordinator)
    current_generation = int(getattr(coordinator, "topology_generation", 0) or 0)
    diff_summary = _topology_diff_summary(
        coordinator,
        previous_generation=previous_generation,
        current_generation=current_generation,
    )
    current_issue_id = _topology_issue_id(entry.entry_id, current_generation)
    for issue_id in _stale_topology_issue_ids(
        hass,
        entry_id=entry.entry_id,
        previous_generation=previous_generation,
        current_issue_id=current_issue_id,
    ):
        ir.async_delete_issue(hass, DOMAIN, issue_id)
    ir.async_create_issue(
        hass,
        DOMAIN,
        current_issue_id,
        data={
            "previous_generation": previous_generation,
            "current_generation": current_generation,
            "diff_summary": diff_summary,
            **counts,
        },
        is_fixable=False,
        is_persistent=True,
        severity=ir.IssueSeverity.WARNING,
        translation_key="device_topology_changed",
        translation_placeholders={
            key: str(value)
            for key, value in {
                "devices": counts["devices"],
                "gateways": counts["gateways"],
                "areas": counts["areas"],
                "rooms": counts["rooms"],
                "groups": counts["groups"],
                "scenes": counts["scenes"],
                "automations": counts["automations"],
                "added": diff_summary["total_added"],
                "removed": diff_summary["total_removed"],
                "metadata_changed": diff_summary["total_metadata_changed"],
            }.items()
        },
    )


def async_delete_topology_changed_issues(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Delete all topology Repairs issues for a config entry."""
    for issue_id in _topology_issue_ids_for_entry(hass, entry_id=entry.entry_id):
        ir.async_delete_issue(hass, DOMAIN, issue_id)


def _topology_issue_id(entry_id: str, generation: int) -> str:
    """Return the stable Repairs issue id without exposing the raw entry id."""
    return TOPOLOGY_CHANGED_ISSUE.format(
        entry_id=_topology_issue_entry_scope(entry_id),
        generation=generation,
    )


def _legacy_topology_issue_id(entry_id: str, generation: int) -> str:
    """Return the pre-redaction Repairs issue id used by older builds."""
    return TOPOLOGY_CHANGED_ISSUE.format(entry_id=entry_id, generation=generation)


def _topology_issue_entry_scope(entry_id: str) -> str:
    """Return a non-reversible scope for entry-scoped Repairs issue ids."""
    return sha256(str(entry_id).encode()).hexdigest()[:16]


def _stale_topology_issue_ids(
    hass: HomeAssistant,
    *,
    entry_id: str,
    previous_generation: int,
    current_issue_id: str,
) -> list[str]:
    """Return old topology issue ids for the same config entry."""
    stale_issue_ids = {
        _legacy_topology_issue_id(entry_id, previous_generation),
        _topology_issue_id(entry_id, previous_generation),
    } - {current_issue_id}

    try:
        issue_registry = ir.async_get(hass)
    except KeyError:
        return sorted(stale_issue_ids)
    for issue_id in _topology_issue_ids_for_entry(
        hass,
        entry_id=entry_id,
        issue_registry=issue_registry,
    ):
        if issue_id == current_issue_id:
            continue
        stale_issue_ids.add(issue_id)

    return sorted(stale_issue_ids)


def _topology_issue_ids_for_entry(
    hass: HomeAssistant,
    *,
    entry_id: str,
    issue_registry: Any | None = None,
) -> list[str]:
    """Return topology issue ids that belong to one config entry."""
    issue_prefixes = (
        TOPOLOGY_CHANGED_ISSUE.format(
            entry_id=_topology_issue_entry_scope(entry_id),
            generation="",
        ),
        TOPOLOGY_CHANGED_ISSUE.format(entry_id=entry_id, generation=""),
    )
    if issue_registry is None:
        try:
            issue_registry = ir.async_get(hass)
        except KeyError:
            return []

    issue_ids: list[str] = []
    for domain, issue_id in tuple(issue_registry.issues):
        if domain != DOMAIN:
            continue
        for issue_prefix in issue_prefixes:
            if issue_id.startswith(issue_prefix) and issue_id.removeprefix(
                issue_prefix
            ).isdecimal():
                issue_ids.append(issue_id)
                break
    return sorted(issue_ids)


def _topology_counts(coordinator: Any) -> dict[str, int]:
    """Return non-sensitive topology counts for Repairs placeholders."""
    return {
        "devices": _safe_len(getattr(coordinator, "devices", {})),
        "gateways": _safe_len(getattr(coordinator, "gateways", {})),
        "areas": _safe_len(getattr(coordinator, "areas", [])),
        "rooms": _safe_len(getattr(coordinator, "rooms", [])),
        "groups": _safe_len(getattr(coordinator, "groups", [])),
        "scenes": _safe_len(getattr(coordinator, "scenes", [])),
        "automations": _safe_len(getattr(coordinator, "automations", [])),
    }


def _safe_len(value: Any) -> int:
    """Return a collection length or zero for invalid test doubles."""
    try:
        return len(value)
    except TypeError:
        return 0


def _topology_diff_summary(
    coordinator: Any,
    *,
    previous_generation: int,
    current_generation: int,
) -> dict[str, Any]:
    """Return a sanitized topology diff summary for Repairs issue data."""
    summary = getattr(coordinator, "topology_diff_summary", None)
    as_dict = getattr(summary, "as_dict", None)
    if callable(as_dict):
        value = as_dict()
        if isinstance(value, Mapping):
            sanitized = _sanitize_topology_diff_mapping(value)
            if sanitized is not None:
                return sanitized
    return empty_topology_diff(
        previous_generation=previous_generation,
        current_generation=current_generation,
    ).as_dict()


def _sanitize_topology_diff_mapping(value: Mapping[str, Any]) -> dict[str, Any] | None:
    """Whitelist aggregate topology diff fields for Repairs issue data."""
    sanitized: dict[str, Any] = {}
    for key in _TOPOLOGY_DIFF_COUNT_KEYS:
        if isinstance(value.get(key), int):
            sanitized[key] = value[key]
    for key in _TOPOLOGY_DIFF_COLLECTION_KEYS:
        counts = value.get(key)
        if isinstance(counts, Mapping):
            sanitized[key] = {
                str(name): count
                for name, count in counts.items()
                if name in _TOPOLOGY_DIFF_CATEGORIES and isinstance(count, int)
            }
    return sanitized or None
