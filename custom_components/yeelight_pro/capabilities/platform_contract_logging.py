"""DEBUG logging helpers for Yeelight platform candidate projection."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import logging
from typing import Any

from ..utils import to_str

_LOGGER = logging.getLogger(__name__)
_SENSITIVE_KEY_PARTS = frozenset({
    "access",
    "authorization",
    "bearer",
    "did",
    "ip",
    "mac",
    "password",
    "secret",
    "token",
})


@dataclass(frozen=True, slots=True)
class PlatformCandidateTrace:
    """One non-sensitive reason that contributed to HA platform candidates."""

    platform: str
    prop: str | None
    reason: str


@dataclass(frozen=True, slots=True)
class PlatformIgnoredTrace:
    """One non-sensitive reason a property did not create a HA platform."""

    prop: str
    reason: str


def platform_trace(
    platform: str,
    *,
    prop: str | None,
    reason: str,
) -> PlatformCandidateTrace:
    """Build a typed platform candidate trace row."""
    return PlatformCandidateTrace(platform=platform, prop=prop, reason=reason)


def ignored_trace(prop: str, *, reason: str) -> PlatformIgnoredTrace:
    """Build a typed ignored-property trace row."""
    return PlatformIgnoredTrace(prop=prop, reason=reason)


def log_platform_candidates(
    payload: Mapping[str, Any],
    *,
    category: str,
    props: set[str],
    has_events: bool,
    has_indexed_switch: bool,
    capability_category: str | None,
    candidates: tuple[str, ...],
    traces: tuple[PlatformCandidateTrace, ...],
    ignored: tuple[PlatformIgnoredTrace, ...] = (),
) -> None:
    """Log platform candidate evidence without exposing raw payload or names."""
    if not _LOGGER.isEnabledFor(logging.DEBUG):
        return
    reason = "matched_capability_evidence" if candidates else "missing_capability_evidence"
    _LOGGER.debug(
        "Resolved platform candidates: device_id=%s category=%s type=%s "
        "capability_category=%s prop_ids=%s has_events=%s has_indexed_switch=%s "
        "candidates=%s traces=%s ignored=%s reason=%s",
        _payload_id(payload),
        category,
        payload.get("type"),
        capability_category,
        _safe_props(props),
        has_events,
        has_indexed_switch,
        candidates,
        _trace_log_rows(traces),
        _ignored_log_rows(ignored),
        reason,
    )


def _payload_id(payload: Mapping[str, Any]) -> str | None:
    return to_str(payload.get("device_id") or payload.get("id")) or None


def _trace_log_rows(traces: tuple[PlatformCandidateTrace, ...]) -> tuple[dict[str, str], ...]:
    return tuple(
        {
            "platform": trace.platform,
            "prop": trace.prop or "",
            "reason": trace.reason,
        }
        for trace in traces
        if _safe_key(trace.prop)
    )


def _ignored_log_rows(ignored: tuple[PlatformIgnoredTrace, ...]) -> tuple[dict[str, str], ...]:
    return tuple(
        {
            "prop": trace.prop,
            "reason": trace.reason,
        }
        for trace in ignored
        if _safe_key(trace.prop)
    )


def _safe_props(props: set[str]) -> list[str]:
    return sorted(prop for prop in props if _safe_key(prop))


def _safe_key(value: str | None) -> bool:
    if not value:
        return True
    lowered = value.lower()
    return not any(part in lowered for part in _SENSITIVE_KEY_PARTS)


__all__ = [
    "PlatformCandidateTrace",
    "PlatformIgnoredTrace",
    "ignored_trace",
    "log_platform_candidates",
    "platform_trace",
]
