"""Low-frequency analytics coordinator for Yeelight Pro house diagnostics."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import timedelta
import logging
from typing import Any, Callable, Awaitable

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from ..const import DOMAIN
from .client import YeelightProClient
from .exceptions import AuthenticationError, safe_error_summary

_LOGGER = logging.getLogger(__name__)
ANALYTICS_UPDATE_INTERVAL = timedelta(minutes=60)


@dataclass(slots=True)
class AnalyticsSnapshot:
    """House analytics snapshot exposed by diagnostic sensors."""

    date_code: str
    day_code: str
    trend_start_date: str
    trend_end_date: str
    alarm_analysis: dict[str, Any] = field(default_factory=dict)
    alarm_top: list[dict[str, Any]] = field(default_factory=list)
    alarm_trend: list[dict[str, Any]] = field(default_factory=list)
    energy_analysis: dict[str, Any] = field(default_factory=dict)
    energy_trend: list[dict[str, Any]] = field(default_factory=list)
    user_actions: dict[str, Any] = field(default_factory=dict)
    monthly_user_actions: dict[str, Any] = field(default_factory=dict)
    yearly_user_actions: dict[str, Any] = field(default_factory=dict)
    endpoint_errors: dict[str, str] = field(default_factory=dict)
    endpoint_count: int = 0
    successful_endpoint_count: int = 0

    @property
    def has_values(self) -> bool:
        """Return whether at least one analytics endpoint returned usable data."""
        return self.successful_endpoint_count > 0


class YeelightProAnalyticsCoordinator(DataUpdateCoordinator[AnalyticsSnapshot]):
    """低频拉取房屋级报警、能耗和用户行为统计。"""

    def __init__(
        self,
        hass: HomeAssistant,
        client: YeelightProClient,
        house_id: int,
        entry_data: Mapping[str, Any] | None = None,
    ) -> None:
        """初始化 analytics coordinator。"""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_analytics",
            update_interval=ANALYTICS_UPDATE_INTERVAL,
        )
        self.client = client
        self.house_id = house_id
        self.entry_data = dict(entry_data or {})
        self.houses: list[dict[str, Any]] = []
        self._runtime_coordinator: Any | None = None

    def bind_runtime_coordinator(
        self,
        coordinator: Any,
        *,
        entry: Any | None = None,
    ) -> None:
        """显式绑定主 coordinator，用于同步 analytics 快照和房屋 metadata。"""
        del entry
        self._runtime_coordinator = coordinator
        self.sync_runtime_metadata(coordinator)
        self._sync_runtime_snapshot(coordinator)

    def async_set_updated_data(self, data: AnalyticsSnapshot) -> None:
        """Set externally pushed analytics data and sync the runtime cache."""
        super().async_set_updated_data(data)
        self._sync_bound_runtime_snapshot(data)

    async def async_soft_initial_refresh(self) -> bool:
        """Fetch the first snapshot without logging HA coordinator setup errors.

        Some private deployments do not expose the optional analytics endpoints.
        The main integration should still load; analytics sensors remain registered
        but unavailable until a later refresh succeeds.
        """
        try:
            snapshot = await self._async_update_data()
        except AuthenticationError:
            raise
        except Exception as err:
            self.last_update_success = False
            self.last_exception = (
                err if isinstance(err, UpdateFailed) else UpdateFailed(
                    f"Failed to refresh Yeelight Pro analytics: {safe_error_summary(err)}"
                )
            )
            _LOGGER.warning(
                "Yeelight Pro analytics unavailable; diagnostic sensors will stay "
                "unavailable until the endpoint succeeds: %s",
                type(err).__name__,
            )
            self._sync_bound_runtime_snapshot(None)
            return False
        self.async_set_updated_data(snapshot)
        return snapshot.has_values

    def sync_runtime_metadata(self, coordinator: Any) -> None:
        """从主 coordinator 同步 analytics sensor 需要的稳定 metadata。"""
        entry_data = getattr(coordinator, "entry_data", None)
        if isinstance(entry_data, Mapping):
            self.entry_data = dict(entry_data)

        houses = getattr(coordinator, "houses", None)
        if isinstance(houses, list):
            self.houses = houses

    def _sync_runtime_snapshot(self, coordinator: Any) -> None:
        """把最新 analytics snapshot 写回主 coordinator 的诊断缓存。"""
        if hasattr(coordinator, "analytics_data"):
            coordinator.analytics_data = self.data

    def _sync_bound_runtime_snapshot(self, snapshot: AnalyticsSnapshot | None) -> None:
        """同步已绑定主 coordinator 的 analytics snapshot。"""
        if self._runtime_coordinator is not None and hasattr(
            self._runtime_coordinator,
            "analytics_data",
        ):
            self._runtime_coordinator.analytics_data = snapshot

    async def _async_update_data(self) -> AnalyticsSnapshot:
        """Fetch one low-frequency analytics snapshot."""
        period = _analytics_period()
        responses, endpoint_errors = await self._fetch_endpoint_responses(period)
        if not responses:
            if self.data is not None:
                _LOGGER.warning(
                    "Failed to refresh all Yeelight Pro analytics endpoints, "
                    "keeping last snapshot: %s",
                    sorted(endpoint_errors),
                )
                self._sync_bound_runtime_snapshot(self.data)
                return self.data
            snapshot = _empty_snapshot(period, endpoint_errors)
            self._sync_bound_runtime_snapshot(snapshot)
            return snapshot

        snapshot = AnalyticsSnapshot(
            date_code=period.month_code,
            day_code=period.day_code,
            trend_start_date=period.trend_start_date,
            trend_end_date=period.day_code,
            alarm_analysis=_response_dict(responses.get("alarm_analysis")),
            alarm_top=_response_list(responses.get("alarm_top")),
            alarm_trend=_response_list(responses.get("alarm_trend")),
            energy_analysis=_response_dict(responses.get("energy_analysis")),
            energy_trend=_response_list(responses.get("energy_trend")),
            user_actions=_response_dict(responses.get("user_actions")),
            monthly_user_actions=_response_dict(
                responses.get("monthly_user_actions")
            ),
            yearly_user_actions=_response_dict(responses.get("yearly_user_actions")),
            endpoint_errors=endpoint_errors,
            endpoint_count=len(responses) + len(endpoint_errors),
            successful_endpoint_count=len(responses),
        )
        self._sync_bound_runtime_snapshot(snapshot)
        return snapshot

    async def _fetch_endpoint_responses(
        self,
        period: _AnalyticsPeriod,
    ) -> tuple[dict[str, Any], dict[str, str]]:
        """Fetch analytics endpoints independently so optional failures stay local."""
        calls: dict[str, Callable[[], Awaitable[Any]]] = {
            "alarm_analysis": lambda: self.client.get_alarm_analysis(
                self.house_id,
                date_code=period.month_code,
            ),
            "alarm_top": lambda: self.client.get_alarm_top(
                self.house_id,
                date_code=period.month_code,
            ),
            "alarm_trend": lambda: self.client.get_alarm_trend(
                self.house_id,
                start_date=period.trend_start_date,
                end_date=period.day_code,
            ),
            "energy_analysis": lambda: self.client.get_energy_analysis(
                self.house_id,
                date_code=period.month_code,
            ),
            "energy_trend": lambda: self.client.get_energy_trend(
                self.house_id,
                start_date=period.trend_start_date,
                end_date=period.day_code,
            ),
            "user_actions": lambda: self.client.get_daily_user_actions(
                self.house_id,
                date_code=period.day_code,
            ),
            "monthly_user_actions": lambda: self.client.get_monthly_user_actions(
                self.house_id,
                date_code=period.month_code,
            ),
            "yearly_user_actions": lambda: self.client.get_yearly_user_actions(
                self.house_id,
                date_code=period.year_code,
            ),
        }
        responses: dict[str, Any] = {}
        endpoint_errors: dict[str, str] = {}
        for name, call in calls.items():
            try:
                response = await call()
                if _is_analytics_response(response):
                    responses[name] = response
                else:
                    endpoint_errors[name] = "InvalidResponse"
            except Exception as err:
                endpoint_errors[name] = safe_error_summary(err)
                _LOGGER.debug(
                    "Skipping unavailable Yeelight Pro analytics endpoint: "
                    "endpoint=%s error_type=%s summary=%s",
                    name,
                    type(err).__name__,
                    safe_error_summary(err),
                )
        return responses, endpoint_errors


@dataclass(frozen=True, slots=True)
class _AnalyticsPeriod:
    """Date window used by low-frequency analytics calls."""

    month_code: str
    year_code: str
    day_code: str
    trend_start_date: str


def _analytics_period() -> _AnalyticsPeriod:
    """Return the previous-day analytics window."""
    last_day = dt_util.now().date() - timedelta(days=1)
    trend_start = last_day - timedelta(days=6)
    return _AnalyticsPeriod(
        month_code=last_day.strftime("%Y-%m"),
        year_code=last_day.strftime("%Y"),
        day_code=last_day.isoformat(),
        trend_start_date=trend_start.isoformat(),
    )


def _empty_snapshot(
    period: _AnalyticsPeriod,
    endpoint_errors: Mapping[str, str],
) -> AnalyticsSnapshot:
    """Build a diagnostic-only snapshot when optional analytics endpoints fail."""
    return AnalyticsSnapshot(
        date_code=period.month_code,
        day_code=period.day_code,
        trend_start_date=period.trend_start_date,
        trend_end_date=period.day_code,
        endpoint_errors={
            key: value
            for key, value in endpoint_errors.items()
            if isinstance(key, str) and isinstance(value, str)
        },
        endpoint_count=len(endpoint_errors),
        successful_endpoint_count=0,
    )


def _response_dict(response: Any) -> dict[str, Any]:
    """Return response.data when it is an object."""
    data = _response_data(response)
    return _safe_mapping(data) if isinstance(data, Mapping) else {}


def _response_list(response: Any) -> list[dict[str, Any]]:
    """Return response.data when it is a list of objects."""
    data = _response_data(response)
    if not isinstance(data, list):
        return []
    return [_safe_mapping(item) for item in data if isinstance(item, Mapping)]


def _response_data(response: Any) -> Any:
    """Return analytics payload data from documented and proxy response wrappers."""
    if not isinstance(response, dict):
        return response
    if "data" in response:
        return response.get("data")
    result = response.get("result")
    if isinstance(result, Mapping) and "data" in result:
        return result.get("data")
    if any(key in response for key in ("code", "msg", "message", "success")):
        return {}
    return response


def _response_has_data(response: Any) -> bool:
    """Return whether a response carries a usable analytics payload."""
    if isinstance(response, list):
        return True
    if not isinstance(response, dict):
        return False
    if "data" in response:
        return True
    result = response.get("result")
    if isinstance(result, Mapping) and "data" in result:
        return True
    return not any(key in response for key in ("code", "msg", "message", "success"))


def _is_analytics_response(response: Any) -> bool:
    """Return true for documented analytics response shapes."""
    if not isinstance(response, dict | list):
        return False
    return _response_has_data(response)


def _safe_mapping(value: Mapping[Any, Any]) -> dict[str, Any]:
    """Return only string-keyed values from an Open API mapping."""
    return {str(key): item for key, item in value.items() if isinstance(key, str)}
