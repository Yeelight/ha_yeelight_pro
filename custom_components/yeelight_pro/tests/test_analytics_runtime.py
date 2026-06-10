"""Analytics runtime aggregation tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from custom_components.yeelight_pro.analytics_contract import (
    ANALYTICS_ACTION_MONTH,
    ANALYTICS_ALARM_ANALYSE,
    ANALYTICS_ALARM_TOP,
    ANALYTICS_ENERGY_ANALYSE,
    ANALYTICS_ENERGY_TREND,
)
from custom_components.yeelight_pro.analytics_runtime import AnalyticsRuntimeState


def test_analytics_runtime_stores_only_aggregate_alarm_metrics() -> None:
    """报警统计只能保留聚合计数，不保存高危设备 raw 明细。"""
    runtime = AnalyticsRuntimeState(retention_days=30)

    snapshot = runtime.record_response(
        ANALYTICS_ALARM_TOP,
        {
            "data": [
                {
                    "alarmNum": "40",
                    "deviceId": "device-secret",
                    "deviceName": "Kitchen secret",
                    "groupName": "Room secret",
                }
            ]
        },
    )

    assert snapshot.as_dict() == {
        "endpoint_key": ANALYTICS_ALARM_TOP,
        "refreshed_at": snapshot.refreshed_at,
        "sample_count": 1,
        "alarm_total": 40,
    }
    assert "device-secret" not in str(snapshot.as_dict())
    assert runtime.latest_summary()["alarm_total"] == 40


def test_analytics_runtime_state_cannot_retain_raw_payload_attribute() -> None:
    """runtime state 只能保留聚合 history，不能临时挂载 raw payload。"""
    runtime = AnalyticsRuntimeState(retention_days=30)

    runtime.record_response(
        ANALYTICS_ALARM_TOP,
        {"data": [{"alarmNum": "1", "deviceId": "device-secret"}]},
    )

    assert not hasattr(runtime, "__dict__")
    try:
        runtime.raw_payload = {"deviceId": "device-secret"}  # type: ignore[attr-defined]
    except AttributeError:
        pass
    else:  # pragma: no cover - guarded by the assertion below if slots regresses.
        raise AssertionError("analytics runtime accepted raw payload storage")


def test_analytics_runtime_summarizes_documented_endpoint_shapes() -> None:
    """聚合 helper 覆盖报警、能源和用户行为三类安全指标。"""
    runtime = AnalyticsRuntimeState(retention_days=30)

    runtime.record_response(
        ANALYTICS_ALARM_ANALYSE,
        {
            "data": {
                "deviceInfo": {"alarmDeviceNum": "2"},
                "statInfo": {"alarmNum": "17"},
            }
        },
    )
    runtime.record_response(
        ANALYTICS_ENERGY_ANALYSE,
        {"data": {"used": {"usedCnt": 1.5}, "saved": {"savedCnt": "0.5"}}},
    )
    runtime.record_response(
        ANALYTICS_ENERGY_TREND,
        {"data": [{"usedCnt": 1.25, "savedCnt": "0.25"}]},
    )
    runtime.record_response(
        ANALYTICS_ACTION_MONTH,
        {"data": {"summary": {"pOnNum": 3, "pOffNum": 2, "sceneNum": 1}}},
    )

    summary = runtime.latest_summary()
    assert summary["alarm_total"] == 17
    assert summary["alarm_device_count"] == 2
    assert summary["energy_used_kwh"] == 1.25
    assert summary["energy_saved_kwh"] == 0.25
    assert summary["action_total"] == 6


def test_analytics_runtime_drops_non_finite_numeric_values() -> None:
    """异常数字不能进入 analytics 传感器或 diagnostics 聚合值。"""
    runtime = AnalyticsRuntimeState(retention_days=30)

    snapshot = runtime.record_response(
        ANALYTICS_ENERGY_TREND,
        {
            "data": [
                {
                    "usedCnt": "NaN",
                    "savedCnt": "Infinity",
                    "deviceId": "device-secret",
                },
                {"usedCnt": "-Infinity", "savedCnt": True},
            ]
        },
    )

    visible_snapshot = str(snapshot.as_dict())
    summary = runtime.latest_summary()
    assert snapshot.as_dict() == {
        "endpoint_key": ANALYTICS_ENERGY_TREND,
        "refreshed_at": snapshot.refreshed_at,
        "sample_count": 2,
    }
    assert summary["energy_used_kwh"] is None
    assert summary["energy_saved_kwh"] is None
    assert "nan" not in visible_snapshot.lower()
    assert "inf" not in visible_snapshot.lower()
    assert "device-secret" not in visible_snapshot


def test_analytics_runtime_prunes_by_retention_days() -> None:
    """内存 retention 应按天裁剪历史聚合样本。"""
    runtime = AnalyticsRuntimeState(retention_days=2)
    now = datetime(2026, 6, 9, tzinfo=timezone.utc)

    runtime.record_response(
        ANALYTICS_ALARM_ANALYSE,
        {"data": {"statInfo": {"alarmNum": "1"}}},
        now=now - timedelta(days=3),
    )
    runtime.record_response(
        ANALYTICS_ALARM_ANALYSE,
        {"data": {"statInfo": {"alarmNum": "2"}}},
        now=now,
    )

    summary = runtime.latest_summary()
    assert summary["history_size"] == 1
    assert summary["alarm_total"] == 2
