"""Yeelight Pro analytics diagnostic sensor tests."""

from __future__ import annotations

from types import SimpleNamespace

from homeassistant.const import EntityCategory, UnitOfEnergy

from custom_components.yeelight_pro.analytics_sensor import (
    ANALYTICS_SENSOR_DESCRIPTIONS,
    YeelightProAnalyticsSensor,
)
from custom_components.yeelight_pro.core.analytics_coordinator import AnalyticsSnapshot
from custom_components.yeelight_pro.identity import entry_identity_scope, scoped_entity_unique_id


def test_analytics_sensors_expose_house_level_diagnostics() -> None:
    """analytics sensor 应暴露聚合值，并把趋势/明细放 attributes。"""
    snapshot = AnalyticsSnapshot(
        date_code="2024-08",
        day_code="2024-08-08",
        trend_start_date="2024-08-02",
        trend_end_date="2024-08-08",
        alarm_analysis={
            "statInfo": {"alarmNum": "4274"},
            "deviceInfo": {"alarmDeviceNum": "222"},
        },
        alarm_top=[{"deviceId": "13", "alarmNum": "40"}],
        alarm_trend=[{"dateStr": "2024-08-08", "alarmNum": "9"}],
        energy_analysis={
            "used": {"usedCnt": 961.53},
            "saved": {"savedCnt": 217.25},
        },
        energy_trend=[{"dateStr": "2024-08-08", "usedCnt": 4.75}],
        user_actions={
            "summary": {"pOnNum": 337, "pOffNum": 363, "lNum": 2, "sceneNum": 3},
            "details": [{"dateStr": "11:00", "deviceId": "secret-device", "pOnNum": 98}],
        },
        monthly_user_actions={
            "summary": {"pOnNum": 2872, "pOffNum": 3562},
            "details": [{"dateStr": "8/01", "deviceId": "secret-device", "pOnNum": 70}],
        },
        yearly_user_actions={
            "summary": {"pOnNum": 20908, "pOffNum": 34081},
            "details": [{"dateStr": "8月", "deviceId": "secret-device", "pOnNum": 2872}],
        },
    )
    coordinator = SimpleNamespace(
        data=snapshot,
        house_id=12345,
        entry_data={"house_name": "星河暖居"},
        houses=[],
    )
    sensors = {
        description.key: YeelightProAnalyticsSensor(coordinator, description)
        for description in ANALYTICS_SENSOR_DESCRIPTIONS
    }

    expected_uid = scoped_entity_unique_id(
        entry_identity_scope({"house_name": "星河暖居"}, 12345),
        "analytics",
        "alarm_total",
    )
    assert sensors["alarm_total"].unique_id == expected_uid
    assert sensors["alarm_total"].suggested_object_id == "星河暖居 报警总数"
    assert sensors["endpoint_success_count"].native_value == 0
    assert sensors["endpoint_success_count"].extra_state_attributes["endpoint_count"] == 0
    assert sensors["alarm_total"].native_value == 4274
    assert sensors["alarm_total"].entity_category == EntityCategory.DIAGNOSTIC
    assert sensors["alarm_total"].available is True
    assert sensors["alarm_total"].extra_state_attributes["trend"] == [
        {"dateStr": "2024-08-08", "alarmNum": "9"}
    ]
    assert sensors["alarm_high_risk_count"].native_value == 1
    assert sensors["alarm_high_risk_count"].extra_state_attributes["top_devices"] == [
        {"alarmNum": "40"}
    ]
    assert "deviceId" not in str(sensors["alarm_high_risk_count"].extra_state_attributes)
    assert sensors["energy_total"].native_value == 961.53
    assert sensors["energy_total"].native_unit_of_measurement == UnitOfEnergy.KILO_WATT_HOUR
    assert sensors["user_action_count"].native_value == 705
    assert sensors["user_action_count"].extra_state_attributes["details"] == [
        {"dateStr": "11:00", "pOnNum": 98}
    ]
    assert sensors["user_action_count"].extra_state_attributes["monthly"]["summary"] == {
        "pOnNum": 2872,
        "pOffNum": 3562,
    }
    assert sensors["user_action_count"].extra_state_attributes["monthly"]["details"] == [
        {"dateStr": "8/01", "pOnNum": 70}
    ]
    assert sensors["user_action_count"].extra_state_attributes["yearly"]["summary"] == {
        "pOnNum": 20908,
        "pOffNum": 34081,
    }
    assert sensors["user_action_count"].extra_state_attributes["yearly"]["details"] == [
        {"dateStr": "8月", "pOnNum": 2872}
    ]
    assert "secret-device" not in str(sensors["user_action_count"].extra_state_attributes)


def test_analytics_sensors_keep_endpoint_error_diagnostics_without_fake_values() -> None:
    """analytics 端点不可用时实体应可诊断，但不能把失败误显示为 0。"""
    snapshot = AnalyticsSnapshot(
        date_code="2024-08",
        day_code="2024-08-08",
        trend_start_date="2024-08-02",
        trend_end_date="2024-08-08",
        endpoint_errors={
            "alarm_top": "ConnectionError",
            "energy_analysis": "InvalidResponse",
        },
        endpoint_count=8,
        successful_endpoint_count=6,
    )
    coordinator = SimpleNamespace(
        data=snapshot,
        house_id=12345,
        entry_data={"house_name": "星河暖居"},
        houses=[],
    )
    sensors = {
        description.key: YeelightProAnalyticsSensor(coordinator, description)
        for description in ANALYTICS_SENSOR_DESCRIPTIONS
    }

    assert sensors["alarm_high_risk_count"].available is True
    assert sensors["endpoint_success_count"].native_value == 6
    assert sensors["endpoint_success_count"].extra_state_attributes == {
        "date_code": "2024-08",
        "day_code": "2024-08-08",
        "trend_start_date": "2024-08-02",
        "trend_end_date": "2024-08-08",
        "failed_endpoint_count": 2,
        "endpoint_count": 8,
        "successful_endpoint_count": 6,
        "endpoint_errors": {
            "alarm_top": "ConnectionError",
            "energy_analysis": "InvalidResponse",
        },
    }
    assert sensors["alarm_high_risk_count"].native_value is None
    assert sensors["energy_total"].native_value is None
    assert sensors["alarm_high_risk_count"].extra_state_attributes == {
        "date_code": "2024-08",
        "endpoint_count": 8,
        "successful_endpoint_count": 6,
        "endpoint_errors": {
            "alarm_top": "ConnectionError",
            "energy_analysis": "InvalidResponse",
        },
    }


def test_analytics_endpoint_health_reports_zero_without_fake_business_values() -> None:
    """所有 analytics 端点失败时只健康实体显示 0，业务指标仍保持 unknown。"""
    snapshot = AnalyticsSnapshot(
        date_code="2024-08",
        day_code="2024-08-08",
        trend_start_date="2024-08-02",
        trend_end_date="2024-08-08",
        endpoint_errors={
            "alarm_analysis": "CommandError",
            "alarm_top": "CommandError",
            "alarm_trend": "CommandError",
            "energy_analysis": "CommandError",
            "energy_trend": "CommandError",
            "user_actions": "CommandError",
            "monthly_user_actions": "CommandError",
            "yearly_user_actions": "CommandError",
        },
        endpoint_count=8,
        successful_endpoint_count=0,
    )
    coordinator = SimpleNamespace(
        data=snapshot,
        house_id=12345,
        entry_data={"house_name": "星河暖居"},
        houses=[],
    )
    sensors = {
        description.key: YeelightProAnalyticsSensor(coordinator, description)
        for description in ANALYTICS_SENSOR_DESCRIPTIONS
    }

    assert sensors["endpoint_success_count"].native_value == 0
    assert sensors["endpoint_success_count"].extra_state_attributes[
        "failed_endpoint_count"
    ] == 8
    assert sensors["alarm_total"].native_value is None
    assert sensors["energy_total"].native_value is None
    assert sensors["user_action_count"].native_value is None
