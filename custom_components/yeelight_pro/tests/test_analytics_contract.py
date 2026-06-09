"""Yeelight Pro data-analysis API contract tests."""

from __future__ import annotations

from typing import Any

import pytest

from custom_components.yeelight_pro.analytics_contract import (
    ANALYTICS_ACTION_DAY,
    ANALYTICS_ACTION_MONTH,
    ANALYTICS_ACTION_YEAR,
    ANALYTICS_ALARM_ANALYSE,
    ANALYTICS_ALARM_TOP,
    ANALYTICS_ALARM_TREND,
    ANALYTICS_ENERGY_ANALYSE,
    ANALYTICS_ENERGY_TREND,
    ANALYTICS_METHOD_POST,
    analytics_method,
    analytics_path,
    analytics_query,
    analytics_request_path,
)
from custom_components.yeelight_pro.core.exceptions import CommandError


@pytest.mark.parametrize(
    ("endpoint", "expected"),
    [
        (ANALYTICS_ALARM_ANALYSE, "/v1/open/data/house/12345/alarm/analyse"),
        (ANALYTICS_ALARM_TOP, "/v1/open/data/house/12345/alarm/top"),
        (ANALYTICS_ALARM_TREND, "/v1/open/data/house/12345/alarm/trend"),
        (ANALYTICS_ENERGY_ANALYSE, "/v1/open/data/house/12345/energy/analyse"),
        (ANALYTICS_ENERGY_TREND, "/v1/open/data/house/12345/energy/trend"),
        (ANALYTICS_ACTION_DAY, "/v1/open/data/house/12345/action/r/day"),
        (ANALYTICS_ACTION_MONTH, "/v1/open/data/house/12345/action/r/month"),
        (ANALYTICS_ACTION_YEAR, "/v1/open/data/house/12345/action/r/year"),
    ],
)
def test_analytics_paths_match_documented_endpoints(
    endpoint: str,
    expected: str,
) -> None:
    """3.4 数据分析接口路径保持文档化合同."""
    assert analytics_path(12345, endpoint) == expected


@pytest.mark.parametrize(
    "endpoint",
    [
        ANALYTICS_ALARM_ANALYSE,
        ANALYTICS_ALARM_TOP,
        ANALYTICS_ALARM_TREND,
        ANALYTICS_ENERGY_ANALYSE,
        ANALYTICS_ENERGY_TREND,
        ANALYTICS_ACTION_DAY,
        ANALYTICS_ACTION_MONTH,
        ANALYTICS_ACTION_YEAR,
    ],
)
def test_analytics_methods_match_documented_post_contract(endpoint: str) -> None:
    """3.4 数据分析接口均为 POST，避免后续 runtime 误用 GET."""
    assert analytics_method(endpoint) == ANALYTICS_METHOD_POST


def test_month_analytics_query_supports_optional_area() -> None:
    """报警和能源月统计接口使用 dateCode，可带 areaId."""
    assert analytics_query(
        ANALYTICS_ALARM_ANALYSE,
        date_code="2024-08",
        area_id=678,
    ) == "dateCode=2024-08&areaId=678"
    assert analytics_request_path(
        12345,
        ANALYTICS_ENERGY_ANALYSE,
        date_code="2024-08",
    ) == "/v1/open/data/house/12345/energy/analyse?dateCode=2024-08"


def test_trend_analytics_query_uses_date_range() -> None:
    """趋势接口使用 startDate/endDate，可带 areaId."""
    assert analytics_request_path(
        12345,
        ANALYTICS_ENERGY_TREND,
        start_date="2024-08-01",
        end_date="2024-08-07",
        area_id="area_1",
    ) == (
        "/v1/open/data/house/12345/energy/trend"
        "?startDate=2024-08-01&endDate=2024-08-07&areaId=area_1"
    )


@pytest.mark.parametrize(
    ("endpoint", "date_code", "expected"),
    [
        (ANALYTICS_ACTION_DAY, "2024-08-01", "dateCode=2024-08-01"),
        (ANALYTICS_ACTION_MONTH, "2024-08", "dateCode=2024-08"),
        (ANALYTICS_ACTION_YEAR, "2024", "dateCode=2024"),
    ],
)
def test_action_analytics_query_uses_documented_date_shape(
    endpoint: str,
    date_code: str,
    expected: str,
) -> None:
    """用户行为统计接口按日/月/年使用不同 dateCode 格式."""
    assert analytics_query(endpoint, date_code=date_code) == expected


@pytest.mark.parametrize(
    ("endpoint", "kwargs", "match"),
    [
        (ANALYTICS_ALARM_ANALYSE, {"date_code": "2024-8"}, "date_code"),
        (ANALYTICS_ALARM_TREND, {"start_date": "2024-08", "end_date": "2024-08-07"}, "start_date"),
        (ANALYTICS_ACTION_DAY, {"date_code": "2024-08"}, "date_code"),
        (ANALYTICS_ACTION_YEAR, {"date_code": "2024-08"}, "date_code"),
        (ANALYTICS_ACTION_MONTH, {"date_code": "2024-08", "area_id": 1}, "area_id"),
    ],
)
def test_analytics_query_rejects_wrong_shape_or_unsupported_area(
    endpoint: str,
    kwargs: dict[str, Any],
    match: str,
) -> None:
    """错误日期粒度或未文档化 areaId 会失败，避免拼出伪接口."""
    with pytest.raises(CommandError, match=match):
        analytics_query(endpoint, **kwargs)


def test_analytics_query_rejects_unknown_endpoint() -> None:
    """未知统计类型不能静默拼 URL."""
    with pytest.raises(CommandError, match="Unsupported analytics endpoint"):
        analytics_request_path(12345, "unknown", date_code="2024-08")
