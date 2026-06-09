"""No-network helpers for Yeelight Pro data-analysis API contracts."""

from __future__ import annotations

from dataclasses import dataclass
import re
from urllib.parse import urlencode

from .core.exceptions import CommandError

_YEAR_RE = re.compile(r"^\d{4}$")
_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")
_DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

ANALYTICS_ALARM_ANALYSE = "alarm_analyse"
ANALYTICS_ALARM_TOP = "alarm_top"
ANALYTICS_ALARM_TREND = "alarm_trend"
ANALYTICS_ENERGY_ANALYSE = "energy_analyse"
ANALYTICS_ENERGY_TREND = "energy_trend"
ANALYTICS_ACTION_DAY = "action_day"
ANALYTICS_ACTION_MONTH = "action_month"
ANALYTICS_ACTION_YEAR = "action_year"
ANALYTICS_METHOD_POST = "POST"


@dataclass(frozen=True, slots=True)
class AnalyticsEndpoint:
    """Documented Yeelight data-analysis endpoint metadata."""

    key: str
    path_suffix: str
    query_shape: str
    method: str = ANALYTICS_METHOD_POST
    area_supported: bool = False


ANALYTICS_ENDPOINTS: dict[str, AnalyticsEndpoint] = {
    ANALYTICS_ALARM_ANALYSE: AnalyticsEndpoint(
        key=ANALYTICS_ALARM_ANALYSE,
        path_suffix="alarm/analyse",
        query_shape="month",
        area_supported=True,
    ),
    ANALYTICS_ALARM_TOP: AnalyticsEndpoint(
        key=ANALYTICS_ALARM_TOP,
        path_suffix="alarm/top",
        query_shape="month",
        area_supported=True,
    ),
    ANALYTICS_ALARM_TREND: AnalyticsEndpoint(
        key=ANALYTICS_ALARM_TREND,
        path_suffix="alarm/trend",
        query_shape="range",
        area_supported=True,
    ),
    ANALYTICS_ENERGY_ANALYSE: AnalyticsEndpoint(
        key=ANALYTICS_ENERGY_ANALYSE,
        path_suffix="energy/analyse",
        query_shape="month",
        area_supported=True,
    ),
    ANALYTICS_ENERGY_TREND: AnalyticsEndpoint(
        key=ANALYTICS_ENERGY_TREND,
        path_suffix="energy/trend",
        query_shape="range",
        area_supported=True,
    ),
    ANALYTICS_ACTION_DAY: AnalyticsEndpoint(
        key=ANALYTICS_ACTION_DAY,
        path_suffix="action/r/day",
        query_shape="day",
    ),
    ANALYTICS_ACTION_MONTH: AnalyticsEndpoint(
        key=ANALYTICS_ACTION_MONTH,
        path_suffix="action/r/month",
        query_shape="month",
    ),
    ANALYTICS_ACTION_YEAR: AnalyticsEndpoint(
        key=ANALYTICS_ACTION_YEAR,
        path_suffix="action/r/year",
        query_shape="year",
    ),
}


def analytics_path(house_id: int, endpoint_key: str) -> str:
    """Build a documented data-analysis path without query parameters."""
    return f"/v1/open/data/house/{house_id}/{_endpoint(endpoint_key).path_suffix}"


def analytics_method(endpoint_key: str) -> str:
    """Return the documented HTTP method for a data-analysis endpoint."""
    return _endpoint(endpoint_key).method


def analytics_query(
    endpoint_key: str,
    *,
    date_code: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    area_id: int | str | None = None,
) -> str:
    """Build a documented data-analysis query string."""
    endpoint = _endpoint(endpoint_key)
    params: dict[str, int | str] = {}
    if endpoint.query_shape == "range":
        if not start_date or not end_date:
            raise CommandError(f"{endpoint.key} requires start_date and end_date")
        _validate_date("start_date", start_date, "day")
        _validate_date("end_date", end_date, "day")
        params["startDate"] = start_date
        params["endDate"] = end_date
    else:
        if date_code is None:
            raise CommandError(f"{endpoint.key} requires date_code")
        _validate_date("date_code", date_code, endpoint.query_shape)
        params["dateCode"] = date_code

    if area_id is not None:
        if not endpoint.area_supported:
            raise CommandError(f"{endpoint.key} does not support area_id")
        params["areaId"] = area_id
    return urlencode(params)


def analytics_request_path(
    house_id: int,
    endpoint_key: str,
    *,
    date_code: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    area_id: int | str | None = None,
) -> str:
    """Build the complete documented data-analysis request path."""
    query = analytics_query(
        endpoint_key,
        date_code=date_code,
        start_date=start_date,
        end_date=end_date,
        area_id=area_id,
    )
    return f"{analytics_path(house_id, endpoint_key)}?{query}"


def _endpoint(endpoint_key: str) -> AnalyticsEndpoint:
    """Return endpoint metadata or fail with a redacted error."""
    try:
        return ANALYTICS_ENDPOINTS[endpoint_key]
    except KeyError as err:
        raise CommandError(f"Unsupported analytics endpoint: {endpoint_key}") from err


def _validate_date(name: str, value: str, shape: str) -> None:
    """Validate the documented date shape without parsing timezone semantics."""
    pattern = {
        "year": _YEAR_RE,
        "month": _MONTH_RE,
        "day": _DAY_RE,
    }[shape]
    if pattern.fullmatch(value) is None:
        raise CommandError(f"{name} must use {shape} date format")
