"""Low-frequency analytics coordinator for Yeelight Pro house diagnostics."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import timedelta
import logging
from typing import Any

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

    async def _async_update_data(self) -> AnalyticsSnapshot:
        """Fetch one low-frequency analytics snapshot."""
        period = _analytics_period()

        try:
            alarm_analysis = await self.client.get_alarm_analysis(
                self.house_id,
                date_code=period.month_code,
            )
            alarm_top = await self.client.get_alarm_top(
                self.house_id,
                date_code=period.month_code,
            )
            alarm_trend = await self.client.get_alarm_trend(
                self.house_id,
                start_date=period.trend_start_date,
                end_date=period.day_code,
            )
            energy_analysis = await self.client.get_energy_analysis(
                self.house_id,
                date_code=period.month_code,
            )
            energy_trend = await self.client.get_energy_trend(
                self.house_id,
                start_date=period.trend_start_date,
                end_date=period.day_code,
            )
            user_actions = await self.client.get_daily_user_actions(
                self.house_id,
                date_code=period.day_code,
            )
            monthly_user_actions = await self.client.get_monthly_user_actions(
                self.house_id,
                date_code=period.month_code,
            )
            yearly_user_actions = await self.client.get_yearly_user_actions(
                self.house_id,
                date_code=period.year_code,
            )
        except AuthenticationError:
            raise
        except Exception as err:
            if self.data is not None:
                _LOGGER.warning(
                    "Failed to refresh Yeelight Pro analytics, keeping last snapshot: %s",
                    safe_error_summary(err),
                )
                return self.data
            raise UpdateFailed(
                f"Failed to refresh Yeelight Pro analytics: {safe_error_summary(err)}"
            ) from None

        return AnalyticsSnapshot(
            date_code=period.month_code,
            day_code=period.day_code,
            trend_start_date=period.trend_start_date,
            trend_end_date=period.day_code,
            alarm_analysis=_response_dict(alarm_analysis),
            alarm_top=_response_list(alarm_top),
            alarm_trend=_response_list(alarm_trend),
            energy_analysis=_response_dict(energy_analysis),
            energy_trend=_response_list(energy_trend),
            user_actions=_response_dict(user_actions),
            monthly_user_actions=_response_dict(monthly_user_actions),
            yearly_user_actions=_response_dict(yearly_user_actions),
        )


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


def _response_dict(response: Any) -> dict[str, Any]:
    """Return response.data when it is an object."""
    if not isinstance(response, dict):
        return {}
    data = response.get("data")
    return _safe_mapping(data) if isinstance(data, Mapping) else {}


def _response_list(response: Any) -> list[dict[str, Any]]:
    """Return response.data when it is a list of objects."""
    if not isinstance(response, dict):
        return []
    data = response.get("data")
    if not isinstance(data, list):
        return []
    return [_safe_mapping(item) for item in data if isinstance(item, Mapping)]


def _safe_mapping(value: Mapping[Any, Any]) -> dict[str, Any]:
    """Return only string-keyed values from an Open API mapping."""
    return {str(key): item for key, item in value.items() if isinstance(key, str)}
