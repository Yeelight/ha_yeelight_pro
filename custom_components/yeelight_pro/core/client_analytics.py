"""Yeelight Pro Open API analytics requests."""

from __future__ import annotations

from typing import Any

from ..analytics_contract import analytics_method, analytics_request_path
from .client_node_base import YeelightProNodeRequestMixin


class YeelightProAnalyticsMixin(YeelightProNodeRequestMixin):
    """开放平台数据分析接口入口。"""

    async def request_analytics(
        self,
        *,
        house_id: int,
        endpoint_key: str,
        date_code: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        area_id: int | str | None = None,
    ) -> dict[str, Any]:
        """请求一个已文档化的数据分析接口。"""
        return await self._request(
            analytics_method(endpoint_key),
            analytics_request_path(
                house_id,
                endpoint_key,
                date_code=date_code,
                start_date=start_date,
                end_date=end_date,
                area_id=area_id,
            ),
        )
