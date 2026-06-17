"""Yeelight Pro analytics client and coordinator tests."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.yeelight_pro.core.analytics_coordinator import (
    AnalyticsSnapshot,
    YeelightProAnalyticsCoordinator,
)
from custom_components.yeelight_pro.core.client import YeelightProClient
from custom_components.yeelight_pro.core.exceptions import (
    AuthenticationError,
    CommandError,
    ConnectionError,
)


def _client() -> YeelightProClient:
    """构造 analytics 测试 client。"""
    return YeelightProClient(
        domain="https://api.yeelight.com/apis/iot",
        access_token="test-token",
        session=MagicMock(),
    )


@pytest.mark.asyncio
async def test_client_analytics_methods_use_post_query_contracts() -> None:
    """数据分析接口应使用文档定义的 POST + query 参数。"""
    client = _client()

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        await client.get_alarm_analysis(12345, date_code="2024-08", area_id=301)
        await client.get_alarm_top(12345, date_code="2024-08")
        await client.get_alarm_trend(
            12345,
            start_date="2024-08-01",
            end_date="2024-08-07",
            area_id="area_1",
        )
        await client.get_energy_analysis(12345, date_code="2024-08")
        await client.get_energy_trend(
            12345,
            start_date="2024-08-01",
            end_date="2024-08-07",
        )
        await client.get_daily_user_actions(12345, date_code="2024-08-01")
        await client.get_monthly_user_actions(12345, date_code="2024-08")
        await client.get_yearly_user_actions(12345, date_code="2024")

    assert [call.args for call in mock_request.await_args_list] == [
        ("POST", "/v1/open/data/house/12345/alarm/analyse?dateCode=2024-08&areaId=301"),
        ("POST", "/v1/open/data/house/12345/alarm/top?dateCode=2024-08"),
        (
            "POST",
            "/v1/open/data/house/12345/alarm/trend?startDate=2024-08-01&endDate=2024-08-07&areaId=area_1",
        ),
        ("POST", "/v1/open/data/house/12345/energy/analyse?dateCode=2024-08"),
        (
            "POST",
            "/v1/open/data/house/12345/energy/trend?startDate=2024-08-01&endDate=2024-08-07",
        ),
        ("POST", "/v1/open/data/house/12345/action/r/day?dateCode=2024-08-01"),
        ("POST", "/v1/open/data/house/12345/action/r/month?dateCode=2024-08"),
        ("POST", "/v1/open/data/house/12345/action/r/year?dateCode=2024"),
    ]
    assert all(call.kwargs == {} for call in mock_request.await_args_list)


@pytest.mark.asyncio
async def test_analytics_coordinator_collects_snapshot(hass) -> None:
    """analytics coordinator 应聚合报警、能耗和用户行为快照。"""
    client = AsyncMock(spec=YeelightProClient)
    client.get_alarm_analysis.return_value = {
        "data": {"statInfo": {"alarmNum": "3"}, "deviceInfo": {"alarmDeviceNum": "2"}}
    }
    client.get_alarm_top.return_value = {"data": [{"deviceId": "1", "alarmNum": "3"}]}
    client.get_alarm_trend.return_value = {"data": [{"dateStr": "2024-08-01", "alarmNum": "3"}]}
    client.get_energy_analysis.return_value = {"data": {"used": {"usedCnt": 12.5}}}
    client.get_energy_trend.return_value = {"data": [{"dateStr": "2024-08-01", "usedCnt": 12.5}]}
    client.get_daily_user_actions.return_value = {
        "data": {"summary": {"pOnNum": 2, "pOffNum": 1}, "details": []}
    }
    client.get_monthly_user_actions.return_value = {
        "data": {"summary": {"pOnNum": 20}, "details": [{"dateStr": "8/01", "pOnNum": 2}]}
    }
    client.get_yearly_user_actions.return_value = {
        "data": {"summary": {"pOnNum": 200}, "details": [{"dateStr": "8月", "pOnNum": 20}]}
    }
    coordinator = YeelightProAnalyticsCoordinator(hass, client, 12345)

    with patch(
        "custom_components.yeelight_pro.core.analytics_coordinator.dt_util.now",
        return_value=datetime(2024, 8, 9, 12, 0, 0),
    ):
        await coordinator.async_config_entry_first_refresh()

    assert coordinator.data is not None
    assert coordinator.data.date_code == "2024-08"
    assert coordinator.data.day_code == "2024-08-08"
    assert coordinator.data.alarm_analysis["statInfo"]["alarmNum"] == "3"
    assert coordinator.data.alarm_top == [{"deviceId": "1", "alarmNum": "3"}]
    assert coordinator.data.energy_analysis["used"]["usedCnt"] == 12.5
    assert coordinator.data.user_actions["summary"]["pOnNum"] == 2
    assert coordinator.data.monthly_user_actions["summary"]["pOnNum"] == 20
    assert coordinator.data.yearly_user_actions["summary"]["pOnNum"] == 200


@pytest.mark.asyncio
async def test_analytics_coordinator_accepts_wrapped_and_direct_data(hass) -> None:
    """analytics 可兼容 data、result.data 和直接 data object/list 形态."""
    client = AsyncMock(spec=YeelightProClient)
    client.get_alarm_analysis.return_value = {
        "result": {"data": {"statInfo": {"alarmNum": "5"}}}
    }
    client.get_alarm_top.return_value = {
        "result": {"data": [{"deviceId": "1", "alarmNum": "2"}]}
    }
    client.get_alarm_trend.return_value = [
        {"dateStr": "2024-08-08", "alarmNum": "1"}
    ]
    client.get_energy_analysis.return_value = {"used": {"usedCnt": "12.5"}}
    client.get_energy_trend.return_value = {
        "result": {"data": [{"dateStr": "2024-08-08", "usedCnt": "12.5"}]}
    }
    client.get_daily_user_actions.return_value = {
        "summary": {"pOnNum": 2, "pOffNum": 1},
        "details": [],
    }
    client.get_monthly_user_actions.return_value = {"data": {"summary": {"pOnNum": 20}}}
    client.get_yearly_user_actions.return_value = {
        "result": {"data": {"summary": {"pOnNum": 200}}}
    }
    coordinator = YeelightProAnalyticsCoordinator(hass, client, 12345)

    with patch(
        "custom_components.yeelight_pro.core.analytics_coordinator.dt_util.now",
        return_value=datetime(2024, 8, 9, 12, 0, 0),
    ):
        await coordinator.async_config_entry_first_refresh()

    assert coordinator.data is not None
    assert coordinator.data.endpoint_errors == {}
    assert coordinator.data.alarm_analysis["statInfo"]["alarmNum"] == "5"
    assert coordinator.data.alarm_top == [{"deviceId": "1", "alarmNum": "2"}]
    assert coordinator.data.alarm_trend == [
        {"dateStr": "2024-08-08", "alarmNum": "1"}
    ]
    assert coordinator.data.energy_analysis["used"]["usedCnt"] == "12.5"
    assert coordinator.data.energy_trend == [
        {"dateStr": "2024-08-08", "usedCnt": "12.5"}
    ]
    assert coordinator.data.user_actions["summary"]["pOnNum"] == 2
    assert coordinator.data.monthly_user_actions["summary"]["pOnNum"] == 20
    assert coordinator.data.yearly_user_actions["summary"]["pOnNum"] == 200


@pytest.mark.asyncio
async def test_analytics_coordinator_first_refresh_reports_unavailable(hass) -> None:
    """初次 analytics API 全失败时应保留诊断快照而不伪造统计值。"""
    client = AsyncMock(spec=YeelightProClient)
    client.get_alarm_analysis.side_effect = ConnectionError("HTTP 404 request failed")
    coordinator = YeelightProAnalyticsCoordinator(hass, client, 12345)

    await coordinator.async_config_entry_first_refresh()

    assert coordinator.data is not None
    assert coordinator.data.has_values is False
    assert coordinator.data.endpoint_count == 8
    assert coordinator.data.successful_endpoint_count == 0
    assert set(coordinator.data.endpoint_errors) == {
        "alarm_analysis",
        "alarm_top",
        "alarm_trend",
        "energy_analysis",
        "energy_trend",
        "monthly_user_actions",
        "user_actions",
        "yearly_user_actions",
    }


@pytest.mark.asyncio
async def test_analytics_coordinator_keeps_partial_snapshot_when_endpoint_fails(
    hass,
) -> None:
    """单个可选 analytics endpoint 失败时，不应拖垮其它已成功的统计。"""
    client = AsyncMock(spec=YeelightProClient)
    client.get_alarm_analysis.return_value = {
        "data": {"statInfo": {"alarmNum": "3"}}
    }
    client.get_alarm_top.side_effect = ConnectionError("optional endpoint unavailable")
    client.get_alarm_trend.return_value = {"data": []}
    client.get_energy_analysis.return_value = {"data": {"used": {"usedCnt": 12.5}}}
    client.get_energy_trend.return_value = {"data": []}
    client.get_daily_user_actions.return_value = {"data": {"summary": {"pOnNum": 1}}}
    client.get_monthly_user_actions.return_value = {"data": {}}
    client.get_yearly_user_actions.return_value = {"data": {}}
    coordinator = YeelightProAnalyticsCoordinator(hass, client, 12345)

    await coordinator.async_config_entry_first_refresh()

    assert coordinator.data is not None
    assert coordinator.data.alarm_analysis["statInfo"]["alarmNum"] == "3"
    assert coordinator.data.energy_analysis["used"]["usedCnt"] == 12.5
    assert coordinator.data.alarm_top == []
    assert coordinator.data.endpoint_errors == {"alarm_top": "ConnectionError"}
    assert coordinator.data.endpoint_count == 8
    assert coordinator.data.successful_endpoint_count == 7


@pytest.mark.asyncio
async def test_analytics_endpoint_auth_errors_are_endpoint_diagnostics(hass) -> None:
    """统计端点权限失败应软降级，避免私有部署整组诊断实体不可用。"""
    client = AsyncMock(spec=YeelightProClient)
    client.get_alarm_analysis.side_effect = AuthenticationError("HTTP 403")
    coordinator = YeelightProAnalyticsCoordinator(hass, client, 12345)

    await coordinator.async_config_entry_first_refresh()

    assert coordinator.data is not None
    assert coordinator.data.has_values is False
    assert coordinator.data.endpoint_count == 8
    assert coordinator.data.successful_endpoint_count == 0
    assert coordinator.data.endpoint_errors["alarm_analysis"] == (
        "AuthenticationError code 403"
    )


@pytest.mark.asyncio
async def test_analytics_endpoint_errors_preserve_safe_error_code(hass) -> None:
    """analytics endpoint 失败诊断应保留安全错误码但不泄露原始消息."""
    client = AsyncMock(spec=YeelightProClient)
    client.get_alarm_analysis.side_effect = CommandError(
        "Open API request failed: code 400 token-secret"
    )
    coordinator = YeelightProAnalyticsCoordinator(hass, client, 12345)

    await coordinator.async_config_entry_first_refresh()

    assert coordinator.data is not None
    assert coordinator.data.endpoint_errors["alarm_analysis"] == (
        "CommandError code 400"
    )
    assert "token-secret" not in str(coordinator.data.endpoint_errors)


@pytest.mark.asyncio
async def test_analytics_soft_initial_refresh_does_not_raise(hass, caplog) -> None:
    """Setup 阶段 analytics 可选端点不可用时应软降级而不是抛错。"""
    client = AsyncMock(spec=YeelightProClient)
    client.get_alarm_analysis.side_effect = ConnectionError("HTTP 404 request failed")
    coordinator = YeelightProAnalyticsCoordinator(hass, client, 12345)
    main_coordinator = MagicMock()
    main_coordinator.analytics_data = object()
    main_coordinator.entry_data = {}
    main_coordinator.houses = []
    coordinator.bind_runtime_coordinator(main_coordinator)

    with caplog.at_level("WARNING"):
        refreshed = await coordinator.async_soft_initial_refresh()

    assert refreshed is False
    assert coordinator.data is not None
    assert coordinator.data.has_values is False
    assert main_coordinator.analytics_data is coordinator.data
    assert coordinator.last_update_success is True
    assert "HTTP 404" not in caplog.text


@pytest.mark.asyncio
async def test_analytics_coordinator_keeps_last_snapshot_on_soft_failure(hass) -> None:
    """后续刷新失败时保留上次成功 snapshot，避免诊断实体抖动为 unavailable。"""
    client = AsyncMock(spec=YeelightProClient)
    client.get_alarm_analysis.return_value = {"data": {"statInfo": {"alarmNum": "3"}}}
    client.get_alarm_top.return_value = {"data": []}
    client.get_alarm_trend.return_value = {"data": []}
    client.get_energy_analysis.return_value = {"data": {"used": {"usedCnt": 12.5}}}
    client.get_energy_trend.return_value = {"data": []}
    client.get_daily_user_actions.return_value = {"data": {"summary": {"pOnNum": 1}}}
    client.get_monthly_user_actions.return_value = {"data": {}}
    client.get_yearly_user_actions.return_value = {"data": {}}
    coordinator = YeelightProAnalyticsCoordinator(hass, client, 12345)

    await coordinator.async_config_entry_first_refresh()
    first_snapshot = coordinator.data
    for method_name in (
        "get_alarm_analysis",
        "get_alarm_top",
        "get_alarm_trend",
        "get_energy_analysis",
        "get_energy_trend",
        "get_daily_user_actions",
        "get_monthly_user_actions",
        "get_yearly_user_actions",
    ):
        getattr(client, method_name).side_effect = ConnectionError("temporary")

    await coordinator.async_refresh()

    assert coordinator.data is first_snapshot


@pytest.mark.asyncio
async def test_analytics_coordinator_binding_syncs_main_coordinator_snapshot(hass) -> None:
    """analytics coordinator 应通过显式绑定同步主 coordinator 诊断缓存。"""
    client = AsyncMock(spec=YeelightProClient)
    coordinator = YeelightProAnalyticsCoordinator(hass, client, 12345)
    main_coordinator = MagicMock()
    main_coordinator.analytics_data = None
    main_coordinator.entry_data = {"house_name": "星河暖居"}
    main_coordinator.houses = [{"id": 12345, "name": "星河暖居"}]
    entry = MagicMock()
    entry.async_on_unload = MagicMock()

    coordinator.bind_runtime_coordinator(main_coordinator, entry=entry)
    snapshot = AnalyticsSnapshot(
        date_code="2024-08",
        day_code="2024-08-08",
        trend_start_date="2024-08-02",
        trend_end_date="2024-08-08",
    )
    coordinator.async_set_updated_data(snapshot)

    assert coordinator.entry_data == {"house_name": "星河暖居"}
    assert coordinator.houses == [{"id": 12345, "name": "星河暖居"}]
    assert main_coordinator.analytics_data is snapshot
    await coordinator.async_shutdown()
