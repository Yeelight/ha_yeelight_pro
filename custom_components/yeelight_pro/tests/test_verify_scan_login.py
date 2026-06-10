"""Tests for the guarded production APP scan-login probe script."""

from __future__ import annotations

from argparse import Namespace
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import AsyncMock

from scripts import verify_scan_login

ROOT = Path(__file__).resolve().parents[3]


def _args(**overrides) -> Namespace:
    values = {
        "confirm_production_scan_login": False,
        "device_env": "YEELIGHT_PRO_SCAN_LOGIN_DEVICE",
        "region": "cn",
        "duration_seconds": 60,
        "poll_interval_seconds": 2,
        "max_polls": 60,
    }
    values.update(overrides)
    return Namespace(**values)


def test_validate_run_request_requires_explicit_confirm() -> None:
    """没有显式确认时必须 fail closed，不读取或输出 device."""
    safety = verify_scan_login.validate_run_request(
        _args(),
        {"YEELIGHT_PRO_SCAN_LOGIN_DEVICE": "secret-device"},
    )

    assert safety.allowed is False
    assert safety.device == ""
    assert safety.error == "missing_confirm_flag"


def test_validate_run_request_requires_device_env() -> None:
    """显式确认后仍必须从环境变量读取 device，不能走命令行参数."""
    safety = verify_scan_login.validate_run_request(
        _args(confirm_production_scan_login=True),
        {},
    )

    assert safety.allowed is False
    assert safety.device == ""
    assert safety.error == "missing_device_env"


def test_validate_run_request_accepts_bounded_explicit_run() -> None:
    """显式确认、device 环境变量和有界参数同时满足时才允许网络验证."""
    safety = verify_scan_login.validate_run_request(
        _args(confirm_production_scan_login=True, region="eu"),
        {"YEELIGHT_PRO_SCAN_LOGIN_DEVICE": "secret-device"},
    )

    assert safety.allowed is True
    assert safety.region == "de"
    assert safety.device == "secret-device"
    assert safety.error is None


def test_validate_run_request_rejects_invalid_region_and_unbounded_probe() -> None:
    """真实扫码轮询必须有明确区域、时间、轮询间隔和次数上限."""
    environ = {"YEELIGHT_PRO_SCAN_LOGIN_DEVICE": "secret-device"}

    assert (
        verify_scan_login.validate_run_request(
            _args(confirm_production_scan_login=True, region="moon"),
            environ,
        ).error
        == "invalid_region"
    )
    assert (
        verify_scan_login.validate_run_request(
            _args(confirm_production_scan_login=True, duration_seconds=301),
            environ,
        ).error
        == "invalid_duration"
    )
    assert (
        verify_scan_login.validate_run_request(
            _args(confirm_production_scan_login=True, poll_interval_seconds=0.5),
            environ,
        ).error
        == "invalid_poll_interval"
    )
    assert (
        verify_scan_login.validate_run_request(
            _args(confirm_production_scan_login=True, max_polls=301),
            environ,
        ).error
        == "invalid_max_polls"
    )


def test_summary_redacts_qr_device_token_and_user_values() -> None:
    """摘要只能保留状态、计数和布尔值，不能复制扫码敏感值."""
    summary = verify_scan_login.ScanLoginProbeSummary(
        ok=True,
        network_attempted=True,
        region="cn",
        created_qrcode=True,
        polls=2,
        login_received=True,
        token_received=True,
        last_status=verify_scan_login.ScanLoginStatus.LOGIN,
        remaining_seconds=120,
    )

    output = json.dumps(summary.as_dict(), sort_keys=True)

    assert "secret-device" not in output
    assert "secret-token" not in output
    assert "secret-refresh" not in output
    assert "secret-qr" not in output
    assert "secret-user" not in output
    assert summary.as_dict()["token_received"] is True


def test_main_does_not_probe_network_without_confirm(monkeypatch, capsys) -> None:
    """默认 CLI 路径不能触发真实扫码登录 HTTP 请求."""
    probe = AsyncMock()
    monkeypatch.setattr(verify_scan_login, "async_probe_scan_login", probe)

    exit_code = verify_scan_login.main([])

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
        [sys.executable, str(ROOT / "scripts" / "verify_scan_login.py")],
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
    """显式确认和 device 环境变量存在时才调用真实扫码探测入口."""
    summary = verify_scan_login.ScanLoginProbeSummary(ok=True, region="sg")
    probe = AsyncMock(return_value=summary)
    monkeypatch.setenv("YEELIGHT_PRO_SCAN_LOGIN_DEVICE", "secret-device")
    monkeypatch.setattr(verify_scan_login, "async_probe_scan_login", probe)

    exit_code = verify_scan_login.main([
        "--confirm-production-scan-login",
        "--region",
        "sg",
        "--duration-seconds",
        "3",
        "--poll-interval-seconds",
        "1",
        "--max-polls",
        "2",
    ])

    assert exit_code == 0
    probe.assert_awaited_once_with(
        region="sg",
        device="secret-device",
        duration_seconds=3.0,
        poll_interval_seconds=1.0,
        max_polls=2,
    )
    output = json.loads(capsys.readouterr().out)
    assert output["ok"] is True
    assert "secret-device" not in json.dumps(output)


async def test_probe_summarizes_created_scanned_login_without_values(monkeypatch) -> None:
    """生产探针聚合扫码状态，不输出二维码、device、token 或用户信息."""
    payloads = [
        _scan_payload("CREATED"),
        _scan_payload("SCANNED"),
        _scan_payload("LOGIN", token=True),
    ]
    session = _FakeSession(payloads)

    class FakeClientSession:
        async def __aenter__(self):
            return session

        async def __aexit__(self, exc_type, exc, tb):
            return False

    async def immediate_sleep(delay):
        return None

    monkeypatch.setattr(verify_scan_login.aiohttp, "ClientSession", FakeClientSession)
    monkeypatch.setattr(verify_scan_login.asyncio, "sleep", immediate_sleep)

    summary = await verify_scan_login.async_probe_scan_login(
        region="cn",
        device="secret-device",
        duration_seconds=5,
        poll_interval_seconds=1,
        max_polls=2,
    )
    result = summary.as_dict()
    visible = json.dumps(result, sort_keys=True)

    assert result["ok"] is True
    assert result["network_attempted"] is True
    assert result["created_qrcode"] is True
    assert result["polls"] == 2
    assert result["last_status"] == "LOGIN"
    assert result["login_received"] is True
    assert result["token_received"] is True
    assert "secret-device" not in visible
    assert "secret-token" not in visible
    assert "secret-refresh" not in visible
    assert "secret-qr" not in visible
    assert "secret-user" not in visible
    assert [call["path"] for call in session.calls] == [
        "/apis/account/user/scan-login/query/qrcode/secret-device",
        "/apis/account/user/scan-login/check/qrcode/secret-qr",
        "/apis/account/user/scan-login/check/qrcode/secret-qr",
    ]


def _scan_payload(status: str, *, token: bool = False) -> dict:
    data = {
        "qrCodeId": "secret-qr",
        "device": "secret-device",
        "status": status,
        "createAt": 1_700_000_000_000,
        "expireIn": 300_000,
        "expireAt": 4_102_444_800_000,
        "source": "home-assistant",
    }
    if token:
        data["token"] = {
            "accessToken": "secret-token",
            "refreshToken": "secret-refresh",
            "tokenType": "Bearer",
            "expiresIn": 3600,
            "id": "secret-user",
            "username": "secret-name",
        }
    return {"code": 200, "data": data}


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.status = 200

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def raise_for_status(self) -> None:
        return None

    async def json(self) -> dict:
        return self._payload


class _FakeSession:
    def __init__(self, payloads: list[dict]) -> None:
        self._payloads = list(payloads)
        self.calls: list[dict[str, str]] = []

    def post(self, url, *, data, headers, timeout):
        self.calls.append({"path": url.removeprefix("https://api.yeelight.com")})
        return _FakeResponse(self._payloads.pop(0))
