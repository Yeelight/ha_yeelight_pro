"""Opt-in Yeelight Pro analytics runtime aggregation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math
from typing import Any

from .analytics_contract import (
    ANALYTICS_ACTION_DAY,
    ANALYTICS_ACTION_MONTH,
    ANALYTICS_ACTION_YEAR,
    ANALYTICS_ALARM_ANALYSE,
    ANALYTICS_ALARM_TOP,
    ANALYTICS_ALARM_TREND,
    ANALYTICS_ENERGY_ANALYSE,
    ANALYTICS_ENERGY_TREND,
)

Number = int | float

ANALYTICS_METRIC_KEYS = (
    "alarm_total",
    "alarm_device_count",
    "energy_used_kwh",
    "energy_saved_kwh",
    "action_total",
)
_ACTION_SUMMARY_KEYS = ("cNum", "ctNum", "lNum", "sceneNum", "pOnNum", "pOffNum")


@dataclass(frozen=True, slots=True)
class AnalyticsSnapshot:
    """Redacted aggregate analytics sample retained in memory."""

    endpoint_key: str
    refreshed_at: str
    sample_count: int
    alarm_total: Number | None = None
    alarm_device_count: Number | None = None
    energy_used_kwh: Number | None = None
    energy_saved_kwh: Number | None = None
    action_total: Number | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return a safe, aggregate-only representation."""
        return {
            "endpoint_key": self.endpoint_key,
            "refreshed_at": self.refreshed_at,
            "sample_count": self.sample_count,
            **{
                key: value
                for key, value in {
                    "alarm_total": self.alarm_total,
                    "alarm_device_count": self.alarm_device_count,
                    "energy_used_kwh": self.energy_used_kwh,
                    "energy_saved_kwh": self.energy_saved_kwh,
                    "action_total": self.action_total,
                }.items()
                if value is not None
            },
        }


class AnalyticsRuntimeState:
    """In-memory retention for opt-in aggregate analytics."""

    __slots__ = ("_history", "_retention_days")

    def __init__(self, *, retention_days: int) -> None:
        self._retention_days = retention_days
        self._history: list[AnalyticsSnapshot] = []

    @property
    def retention_days(self) -> int:
        """Return the current in-memory retention window."""
        return self._retention_days

    def apply_retention_days(self, retention_days: int) -> None:
        """Update retention and prune old aggregate samples."""
        self._retention_days = retention_days
        self._prune(_utcnow())

    def record_response(
        self,
        endpoint_key: str,
        payload: Mapping[str, Any],
        *,
        now: datetime | None = None,
    ) -> AnalyticsSnapshot:
        """Summarize a raw API response without retaining raw payload details."""
        current = now or _utcnow()
        snapshot = _aggregate_payload(endpoint_key, payload, current)
        self._history.append(snapshot)
        self._prune(current)
        return snapshot

    def latest_summary(self) -> dict[str, Any]:
        """Return latest aggregate metrics for sensors and diagnostics."""
        latest = self._history[-1] if self._history else None
        return {
            "retention_days": self._retention_days,
            "history_size": len(self._history),
            "last_endpoint": latest.endpoint_key if latest else None,
            "last_refreshed_at": latest.refreshed_at if latest else None,
            **{key: self._latest_metric(key) for key in ANALYTICS_METRIC_KEYS},
        }

    def _latest_metric(self, key: str) -> Number | None:
        """Return the newest retained non-empty metric value."""
        for snapshot in reversed(self._history):
            value = getattr(snapshot, key)
            if value is not None:
                return value
        return None

    def _prune(self, now: datetime) -> None:
        """Prune samples older than the configured retention window."""
        threshold = now - timedelta(days=self._retention_days)
        self._history = [
            snapshot
            for snapshot in self._history
            if _parse_refreshed_at(snapshot.refreshed_at) >= threshold
        ]


def _aggregate_payload(
    endpoint_key: str,
    payload: Mapping[str, Any],
    now: datetime,
) -> AnalyticsSnapshot:
    """Build a snapshot for one documented analytics endpoint."""
    data = payload.get("data") if isinstance(payload, Mapping) else None
    if endpoint_key == ANALYTICS_ALARM_ANALYSE and isinstance(data, Mapping):
        return AnalyticsSnapshot(
            endpoint_key=endpoint_key,
            refreshed_at=_isoformat(now),
            sample_count=1,
            alarm_total=_number_at(data, ("statInfo", "alarmNum")),
            alarm_device_count=_number_at(data, ("deviceInfo", "alarmDeviceNum")),
        )
    if endpoint_key in {ANALYTICS_ALARM_TOP, ANALYTICS_ALARM_TREND}:
        rows = _rows(data)
        return AnalyticsSnapshot(
            endpoint_key=endpoint_key,
            refreshed_at=_isoformat(now),
            sample_count=len(rows),
            alarm_total=_sum_rows(rows, "alarmNum"),
        )
    if endpoint_key == ANALYTICS_ENERGY_ANALYSE and isinstance(data, Mapping):
        return AnalyticsSnapshot(
            endpoint_key=endpoint_key,
            refreshed_at=_isoformat(now),
            sample_count=1,
            energy_used_kwh=_number_at(data, ("used", "usedCnt")),
            energy_saved_kwh=_number_at(data, ("saved", "savedCnt")),
        )
    if endpoint_key == ANALYTICS_ENERGY_TREND:
        rows = _rows(data)
        return AnalyticsSnapshot(
            endpoint_key=endpoint_key,
            refreshed_at=_isoformat(now),
            sample_count=len(rows),
            energy_used_kwh=_sum_rows(rows, "usedCnt"),
            energy_saved_kwh=_sum_rows(rows, "savedCnt"),
        )
    if endpoint_key in {
        ANALYTICS_ACTION_DAY,
        ANALYTICS_ACTION_MONTH,
        ANALYTICS_ACTION_YEAR,
    } and isinstance(data, Mapping):
        details = _rows(data.get("details"))
        return AnalyticsSnapshot(
            endpoint_key=endpoint_key,
            refreshed_at=_isoformat(now),
            sample_count=len(details),
            action_total=_sum_action_summary(data.get("summary")),
        )
    return AnalyticsSnapshot(
        endpoint_key=endpoint_key,
        refreshed_at=_isoformat(now),
        sample_count=0,
    )


def _rows(value: Any) -> list[Mapping[str, Any]]:
    """Return object rows only, dropping raw non-object values."""
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _number_at(value: Mapping[str, Any], path: tuple[str, ...]) -> Number | None:
    """Read one numeric value from a nested mapping."""
    current: Any = value
    for part in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(part)
    return _number(current)


def _sum_rows(rows: Sequence[Mapping[str, Any]], key: str) -> Number | None:
    """Sum numeric values from aggregate rows."""
    values = [_number(row.get(key)) for row in rows]
    numbers = [value for value in values if value is not None]
    if not numbers:
        return None
    return _normalize_number(sum(numbers))


def _sum_action_summary(value: Any) -> Number | None:
    """Sum documented action summary counters."""
    if not isinstance(value, Mapping):
        return None
    numbers = [_number(value.get(key)) for key in _ACTION_SUMMARY_KEYS]
    clean = [number for number in numbers if number is not None]
    if not clean:
        return None
    return _normalize_number(sum(clean))


def _number(value: Any) -> Number | None:
    """Coerce documented numeric strings/numbers while rejecting booleans."""
    if isinstance(value, bool) or value in (None, ""):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return _normalize_number(value)
    if isinstance(value, str):
        try:
            return _normalize_number(float(value.strip()))
        except ValueError:
            return None
    return None


def _normalize_number(value: float) -> Number | None:
    """Prefer ints for whole-number counters."""
    if not math.isfinite(value):
        return None
    return int(value) if float(value).is_integer() else value


def _utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


def _isoformat(value: datetime) -> str:
    """Serialize timestamps in a stable UTC form."""
    return value.astimezone(timezone.utc).isoformat()


def _parse_refreshed_at(value: str) -> datetime:
    """Parse timestamps produced by this module."""
    return datetime.fromisoformat(value).astimezone(timezone.utc)
