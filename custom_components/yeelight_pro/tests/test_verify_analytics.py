"""Tests for the guarded production analytics probe script."""

from __future__ import annotations

from argparse import Namespace
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import AsyncMock

from scripts import verify_analytics
from scripts.verify_analytics_support import (
    AnalyticsProbeSummary,
    update_summary_from_payload,
)

ROOT = Path(__file__).resolve().parents[3]


def _args(**overrides) -> Namespace:
    values = {
        "confirm_production_analytics": False,
        "access_token_env": "YEELIGHT_PRO_ANALYTICS_ACCESS_TOKEN",
        "house_id_env": "YEELIGHT_PRO_ANALYTICS_HOUSE_ID",
        "client_id_env": "YEELIGHT_PRO_ANALYTICS_CLIENT_ID",
        "region": "cn",
        "endpoint": "energy_analyse",
        "date_code": "2026-06",
        "start_date": None,
        "end_date": None,
        "area_id_env": None,
        "timeout_seconds": 30,
    }
    values.update(overrides)
    return Namespace(**values)


def test_validate_run_request_requires_explicit_confirm() -> None:
    """没有显式确认时必须 fail closed，不读取或输出 token/house."""
    safety = verify_analytics.validate_run_request(
        _args(),
        {
            "YEELIGHT_PRO_ANALYTICS_ACCESS_TOKEN": "secret-token",
            "YEELIGHT_PRO_ANALYTICS_HOUSE_ID": "429392",
        },
    )

    assert safety.allowed is False
    assert safety.access_token == ""
    assert safety.house_id == 0
    assert safety.error == "missing_confirm_flag"


def test_validate_run_request_requires_token_and_house_env() -> None:
    """显式确认后仍必须从环境变量读取 token 和 house id."""
    assert (
        verify_analytics.validate_run_request(
            _args(confirm_production_analytics=True),
            {"YEELIGHT_PRO_ANALYTICS_HOUSE_ID": "429392"},
        ).error
        == "missing_token_env"
    )
    assert (
        verify_analytics.validate_run_request(
            _args(confirm_production_analytics=True),
            {"YEELIGHT_PRO_ANALYTICS_ACCESS_TOKEN": "secret-token"},
        ).error
        == "missing_house_id_env"
    )


def test_validate_run_request_accepts_bounded_explicit_run() -> None:
    """显式确认、env 凭据和有界 analytics 参数同时满足时才允许网络验证."""
    safety = verify_analytics.validate_run_request(
        _args(
            confirm_production_analytics=True,
            region="us",
            endpoint="alarm_trend",
            date_code=None,
            start_date="2026-06-01",
            end_date="2026-06-08",
            area_id_env="YEELIGHT_PRO_ANALYTICS_AREA_ID",
        ),
        {
            "YEELIGHT_PRO_ANALYTICS_ACCESS_TOKEN": "secret-token",
            "YEELIGHT_PRO_ANALYTICS_HOUSE_ID": "429392",
            "YEELIGHT_PRO_ANALYTICS_CLIENT_ID": "secret-client",
            "YEELIGHT_PRO_ANALYTICS_AREA_ID": "secret-area",
        },
    )

    assert safety.allowed is True
    assert safety.region == "us"
    assert safety.domain == "https://api-us.yeelight.com/apis/iot"
    assert safety.access_token == "secret-token"
    assert safety.house_id == 429392
    assert safety.client_id == "secret-client"
    assert safety.endpoint == "alarm_trend"
    assert safety.area_id == "secret-area"
    assert safety.error is None


def test_validate_run_request_rejects_invalid_region_endpoint_and_timeout() -> None:
    """analytics 生产探针必须拒绝错误区域、错误日期形态和无界运行."""
    environ = {
        "YEELIGHT_PRO_ANALYTICS_ACCESS_TOKEN": "secret-token",
        "YEELIGHT_PRO_ANALYTICS_HOUSE_ID": "429392",
    }

    assert (
        verify_analytics.validate_run_request(
            _args(confirm_production_analytics=True, region="moon"),
            environ,
        ).error
        == "invalid_region"
    )
    assert (
        verify_analytics.validate_run_request(
            _args(
                confirm_production_analytics=True,
                endpoint="action_day",
                date_code="2026-06",
            ),
            environ,
        ).error
        == "invalid_analytics_request"
    )
    assert (
        verify_analytics.validate_run_request(
            _args(confirm_production_analytics=True, timeout_seconds=61),
            environ,
        ).error
        == "invalid_timeout"
    )


def test_summary_describes_payload_shape_without_raw_values() -> None:
    """摘要只能保留字段形态和类型聚合，不能复制 analytics raw payload 值."""
    summary = AnalyticsProbeSummary(
        ok=True,
        network_attempted=True,
        region="cn",
        endpoint="energy_analyse",
    )

    update_summary_from_payload(
        summary,
        {
            "houseId": "429392",
            "deviceId": "secret-device",
            "roomName": "Secret Room",
            "energy": {"used": 12.5, "saved": 2},
            "rows": [
                {"deviceName": "Secret Light", "value": 1},
                {"deviceName": "Secret Curtain", "value": 2},
            ],
        },
    )
    result = summary.as_dict()
    visible = json.dumps(result, sort_keys=True)

    assert result["top_level_type"] == "object"
    assert result["numeric_fields"]["$.energy.used"] == 1
    assert result["numeric_fields"]["$.energy.saved"] == 1
    assert result["list_lengths"]["$.rows:1-3"] == 1
    assert "houseId" in visible
    assert "secret-device" not in visible
    assert "Secret Room" not in visible
    assert "Secret Light" not in visible
    assert "429392" not in visible
    assert "12.5" not in visible


def test_main_does_not_probe_network_without_confirm(monkeypatch, capsys) -> None:
    """默认 CLI 路径不能触发真实云端 analytics HTTP 请求."""
    probe = AsyncMock()
    monkeypatch.setattr(verify_analytics, "async_probe_analytics", probe)

    exit_code = verify_analytics.main([])

    assert exit_code == 2
    probe.assert_not_awaited()
    assert json.loads(capsys.readouterr().out) == {
        "error": "missing_confirm_flag",
        "network_attempted": False,
        "ok": False,
    }


def test_script_path_execution_is_no_network_without_confirm() -> None:
    """直接执行脚本时也必须先 fail closed，不能因 import path 漏洞失败."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "verify_analytics.py")],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert json.loads(result.stdout) == {
        "error": "missing_confirm_flag",
        "network_attempted": False,
        "ok": False,
    }
    assert "ModuleNotFoundError" not in result.stderr


def test_main_runs_probe_only_after_confirm_and_env(monkeypatch, capsys) -> None:
    """显式确认和 token/house 环境变量存在时才调用 analytics 探测入口."""
    summary = AnalyticsProbeSummary(ok=True, region="sg")
    probe = AsyncMock(return_value=summary)
    monkeypatch.setenv("YEELIGHT_PRO_ANALYTICS_ACCESS_TOKEN", "secret-token")
    monkeypatch.setenv("YEELIGHT_PRO_ANALYTICS_HOUSE_ID", "429392")
    monkeypatch.setenv("YEELIGHT_PRO_ANALYTICS_CLIENT_ID", "secret-client")
    monkeypatch.setenv("YEELIGHT_PRO_ANALYTICS_AREA_ID", "secret-area")
    monkeypatch.setattr(verify_analytics, "async_probe_analytics", probe)

    exit_code = verify_analytics.main([
        "--confirm-production-analytics",
        "--region",
        "sg",
        "--endpoint",
        "energy_analyse",
        "--date-code",
        "2026-06",
        "--area-id-env",
        "YEELIGHT_PRO_ANALYTICS_AREA_ID",
        "--timeout-seconds",
        "3",
    ])

    assert exit_code == 0
    probe.assert_awaited_once_with(
        region="sg",
        domain="https://api-sg.yeelight.com/apis/iot",
        access_token="secret-token",
        house_id=429392,
        client_id="secret-client",
        endpoint="energy_analyse",
        date_code="2026-06",
        start_date=None,
        end_date=None,
        area_id="secret-area",
        timeout_seconds=3.0,
    )
    output = json.loads(capsys.readouterr().out)
    assert output["ok"] is True
    assert "secret-token" not in json.dumps(output)
    assert "429392" not in json.dumps(output)
    assert "secret-client" not in json.dumps(output)
    assert "secret-area" not in json.dumps(output)


async def test_probe_summarizes_analytics_payload_without_values(monkeypatch) -> None:
    """生产探针聚合 analytics payload 形态，不输出 house、area、token 或设备值."""

    class FakeClient:
        def __init__(
            self,
            *,
            domain,
            access_token,
            client_id,
            session,
            timeout,
        ) -> None:
            self.domain = domain
            self.access_token = access_token
            self.client_id = client_id
            self.session = session
            self.timeout = timeout

        async def request_analytics(
            self,
            *,
            house_id,
            endpoint_key,
            date_code,
            start_date,
            end_date,
            area_id,
        ):
            return {
                "houseId": house_id,
                "endpoint": endpoint_key,
                "areaId": area_id,
                "total": 2,
                "rows": [
                    {"deviceId": "secret-device-1", "value": 1},
                    {"deviceId": "secret-device-2", "value": 2},
                ],
            }

    class FakeClientSession:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(verify_analytics.aiohttp, "ClientSession", FakeClientSession)
    monkeypatch.setattr(verify_analytics, "load_yeelight_client", lambda: FakeClient)

    summary = await verify_analytics.async_probe_analytics(
        region="cn",
        domain="https://api.yeelight.com/apis/iot",
        access_token="secret-token",
        house_id=429392,
        client_id="secret-client",
        endpoint="energy_analyse",
        date_code="2026-06",
        start_date=None,
        end_date=None,
        area_id="secret-area",
        timeout_seconds=3,
    )
    result = summary.as_dict()
    visible = json.dumps(result, sort_keys=True)

    assert result["ok"] is True
    assert result["network_attempted"] is True
    assert result["top_level_type"] == "object"
    assert result["list_lengths"]["$.rows:1-3"] == 1
    assert result["numeric_fields"]["$.total"] == 1
    assert "secret-token" not in visible
    assert "secret-client" not in visible
    assert "secret-area" not in visible
    assert "secret-device" not in visible
    assert "429392" not in visible
