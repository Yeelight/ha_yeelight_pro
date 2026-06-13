"""Yeelight Pro Open API house analytics operations."""

from __future__ import annotations

from typing import Any

from .client_node_base import YeelightProNodeRequestMixin
from .client_paths import (
    alarm_analysis_path,
    alarm_top_path,
    alarm_trend_path,
    daily_user_actions_path,
    energy_analysis_path,
    energy_trend_path,
    monthly_user_actions_path,
    yearly_user_actions_path,
)


class YeelightProDataAnalyticsMixin(YeelightProNodeRequestMixin):
    """开放平台房屋数据分析接口。"""

    async def get_alarm_analysis(
        self,
        house_id: int,
        *,
        date_code: str,
        area_id: int | str | None = None,
    ) -> dict[str, Any]:
        """获取报警统计信息。"""
        return await self._request(
            "POST",
            alarm_analysis_path(house_id, date_code=date_code, area_id=area_id),
        )

    async def get_alarm_top(
        self,
        house_id: int,
        *,
        date_code: str,
        area_id: int | str | None = None,
    ) -> dict[str, Any]:
        """获取高危设备列表。"""
        return await self._request(
            "POST",
            alarm_top_path(house_id, date_code=date_code, area_id=area_id),
        )

    async def get_alarm_trend(
        self,
        house_id: int,
        *,
        start_date: str,
        end_date: str,
        area_id: int | str | None = None,
    ) -> dict[str, Any]:
        """获取报警趋势。"""
        return await self._request(
            "POST",
            alarm_trend_path(
                house_id,
                start_date=start_date,
                end_date=end_date,
                area_id=area_id,
            ),
        )

    async def get_energy_analysis(
        self,
        house_id: int,
        *,
        date_code: str,
        area_id: int | str | None = None,
    ) -> dict[str, Any]:
        """获取能源统计信息。"""
        return await self._request(
            "POST",
            energy_analysis_path(house_id, date_code=date_code, area_id=area_id),
        )

    async def get_energy_trend(
        self,
        house_id: int,
        *,
        start_date: str,
        end_date: str,
        area_id: int | str | None = None,
    ) -> dict[str, Any]:
        """获取能耗趋势。"""
        return await self._request(
            "POST",
            energy_trend_path(
                house_id,
                start_date=start_date,
                end_date=end_date,
                area_id=area_id,
            ),
        )

    async def get_daily_user_actions(
        self,
        house_id: int,
        *,
        date_code: str,
    ) -> dict[str, Any]:
        """获取日度用户行为统计。"""
        return await self._request(
            "POST",
            daily_user_actions_path(house_id, date_code=date_code),
        )

    async def get_monthly_user_actions(
        self,
        house_id: int,
        *,
        date_code: str,
    ) -> dict[str, Any]:
        """获取月度用户行为统计。"""
        return await self._request(
            "POST",
            monthly_user_actions_path(house_id, date_code=date_code),
        )

    async def get_yearly_user_actions(
        self,
        house_id: int,
        *,
        date_code: str,
    ) -> dict[str, Any]:
        """获取年度用户行为统计。"""
        return await self._request(
            "POST",
            yearly_user_actions_path(house_id, date_code=date_code),
        )
