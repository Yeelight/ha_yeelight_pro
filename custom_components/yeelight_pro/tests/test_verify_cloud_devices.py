"""Tests for the guarded production cloud device picker probe script."""

from __future__ import annotations

from argparse import Namespace
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import AsyncMock

from scripts import verify_cloud_devices

ROOT = Path(__file__).resolve().parents[3]


def _args(**overrides) -> Namespace:
    values = {
        "confirm_production_cloud_devices": False,
        "access_token_env": "YEELIGHT_PRO_CLOUD_ACCESS_TOKEN",
        "house_id_env": "YEELIGHT_PRO_CLOUD_HOUSE_ID",
        "client_id_env": "YEELIGHT_PRO_CLOUD_CLIENT_ID",
        "region": "cn",
        "timeout_seconds": 30,
    }
    values.update(overrides)
    return Namespace(**values)


def test_validate_run_request_requires_explicit_confirm() -> None:
    """没有显式确认时必须 fail closed，不读取或输出 token/house."""
    safety = verify_cloud_devices.validate_run_request(
        _args(),
        {
            "YEELIGHT_PRO_CLOUD_ACCESS_TOKEN": "secret-token",
            "YEELIGHT_PRO_CLOUD_HOUSE_ID": "429392",
        },
    )

    assert safety.allowed is False
    assert safety.access_token == ""
    assert safety.house_id == 0
    assert safety.error == "missing_confirm_flag"


def test_validate_run_request_requires_token_env() -> None:
    """显式确认后仍必须从环境变量读取 token，不能走命令行参数."""
    safety = verify_cloud_devices.validate_run_request(
        _args(confirm_production_cloud_devices=True),
        {"YEELIGHT_PRO_CLOUD_HOUSE_ID": "429392"},
    )

    assert safety.allowed is False
    assert safety.error == "missing_token_env"


def test_validate_run_request_requires_house_id_env() -> None:
    """显式确认后仍必须从环境变量读取有效 house id."""
    safety = verify_cloud_devices.validate_run_request(
        _args(confirm_production_cloud_devices=True),
        {"YEELIGHT_PRO_CLOUD_ACCESS_TOKEN": "secret-token"},
    )

    assert safety.allowed is False
    assert safety.error == "missing_house_id_env"


def test_validate_run_request_accepts_bounded_explicit_run() -> None:
    """显式确认、token/house 环境变量和有界参数同时满足时才允许网络验证."""
    safety = verify_cloud_devices.validate_run_request(
        _args(confirm_production_cloud_devices=True, region="eu"),
        {
            "YEELIGHT_PRO_CLOUD_ACCESS_TOKEN": "secret-token",
            "YEELIGHT_PRO_CLOUD_HOUSE_ID": "429392",
            "YEELIGHT_PRO_CLOUD_CLIENT_ID": "secret-client",
        },
    )

    assert safety.allowed is True
    assert safety.region == "de"
    assert safety.domain == "https://api-de.yeelight.com/apis/iot"
    assert safety.access_token == "secret-token"
    assert safety.house_id == 429392
    assert safety.client_id == "secret-client"
    assert safety.error is None


def test_validate_run_request_rejects_invalid_region_and_unbounded_probe() -> None:
    """真实设备列表读取必须有明确区域和时间上限."""
    environ = {
        "YEELIGHT_PRO_CLOUD_ACCESS_TOKEN": "secret-token",
        "YEELIGHT_PRO_CLOUD_HOUSE_ID": "429392",
    }

    assert (
        verify_cloud_devices.validate_run_request(
            _args(confirm_production_cloud_devices=True, region="moon"),
            environ,
        ).error
        == "invalid_region"
    )
    assert (
        verify_cloud_devices.validate_run_request(
            _args(confirm_production_cloud_devices=True, timeout_seconds=61),
            environ,
        ).error
        == "invalid_timeout"
    )
    assert (
        verify_cloud_devices.validate_run_request(
            _args(confirm_production_cloud_devices=True),
            {**environ, "YEELIGHT_PRO_CLOUD_HOUSE_ID": "not-int"},
        ).error
        == "missing_house_id_env"
    )


def test_summary_counts_devices_without_identifier_values() -> None:
    """摘要只能保留数量和 category 聚合，不能复制设备/房间/MAC 等值."""
    summary = verify_cloud_devices.CloudDevicesProbeSummary(
        ok=True,
        network_attempted=True,
        region="cn",
    )

    verify_cloud_devices._update_summary_from_devices(
        summary,
        [
            {
                "id": "secret-device-1",
                "name": "Secret Light",
                "roomName": "Secret Room",
                "mac": "aa:bb:cc:dd:ee:ff",
                "category": "light",
            },
            {"deviceId": "secret-device-2", "deviceCategory": "curtain"},
            {"device_id": "secret-device-3"},
        ],
    )
    result = summary.as_dict()
    visible = json.dumps(result, sort_keys=True)

    assert result["device_count"] == 3
    assert result["has_devices"] is True
    assert result["categories"] == {"curtain": 1, "light": 1, "unknown": 1}
    assert "secret-device" not in visible
    assert "Secret Light" not in visible
    assert "Secret Room" not in visible
    assert "aa:bb:cc" not in visible


def test_main_does_not_probe_network_without_confirm(monkeypatch, capsys) -> None:
    """默认 CLI 路径不能触发真实云端 devices HTTP 请求."""
    probe = AsyncMock()
    monkeypatch.setattr(verify_cloud_devices, "async_probe_cloud_devices", probe)

    exit_code = verify_cloud_devices.main([])

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
        [sys.executable, str(ROOT / "scripts" / "verify_cloud_devices.py")],
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


def test_probe_client_loader_is_homeassistant_free() -> None:
    """真实设备探针 loader 不得间接导入 Home Assistant runtime."""
    before = set(sys.modules)

    client_class = verify_cloud_devices._load_yeelight_client()

    loaded = set(sys.modules) - before
    assert client_class.__name__ == "ProbeYeelightClient"
    assert "homeassistant" not in loaded
    assert not any(module.startswith("homeassistant.") for module in loaded)
    assert not any("schema_cache" in module for module in loaded)


def test_probe_client_loader_does_not_need_homeassistant_package() -> None:
    """即使 homeassistant 包不可导入，真实设备探针 loader 也必须可用."""
    code = """
import importlib.abc
import json
import sys

class BlockHomeAssistant(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "homeassistant" or fullname.startswith("homeassistant."):
            raise ModuleNotFoundError("No module named 'homeassistant'")
        return None

sys.meta_path.insert(0, BlockHomeAssistant())
from scripts import verify_cloud_devices

client_class = verify_cloud_devices._load_yeelight_client()
print(json.dumps({
    "client": client_class.__name__,
    "homeassistant": any(
        name == "homeassistant" or name.startswith("homeassistant.")
        for name in sys.modules
    ),
    "schema_cache": any("schema_cache" in name for name in sys.modules),
}))
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload == {
        "client": "ProbeYeelightClient",
        "homeassistant": False,
        "schema_cache": False,
    }


def test_main_runs_probe_only_after_confirm_and_env(monkeypatch, capsys) -> None:
    """显式确认和 token/house 环境变量存在时才调用真实设备探测入口."""
    summary = verify_cloud_devices.CloudDevicesProbeSummary(ok=True, region="sg")
    probe = AsyncMock(return_value=summary)
    monkeypatch.setenv("YEELIGHT_PRO_CLOUD_ACCESS_TOKEN", "secret-token")
    monkeypatch.setenv("YEELIGHT_PRO_CLOUD_HOUSE_ID", "429392")
    monkeypatch.setenv("YEELIGHT_PRO_CLOUD_CLIENT_ID", "secret-client")
    monkeypatch.setattr(verify_cloud_devices, "async_probe_cloud_devices", probe)

    exit_code = verify_cloud_devices.main([
        "--confirm-production-cloud-devices",
        "--region",
        "sg",
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
        timeout_seconds=3.0,
    )
    output = json.loads(capsys.readouterr().out)
    assert output["ok"] is True
    assert "secret-token" not in json.dumps(output)
    assert "429392" not in json.dumps(output)
    assert "secret-client" not in json.dumps(output)


async def test_probe_summarizes_devices_without_values(monkeypatch) -> None:
    """生产探针聚合真实设备 picker 数据源，不输出设备、house 或 token."""

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

        async def get_devices(self, house_id):
            return [
                {
                    "id": "secret-device-1",
                    "name": "Secret Light",
                    "roomName": "Secret Room",
                    "category": "light",
                },
                {"id": "secret-device-2", "category": "curtain"},
                {"id": "secret-device-3"},
            ]

    class FakeClientSession:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(verify_cloud_devices.aiohttp, "ClientSession", FakeClientSession)
    monkeypatch.setattr(verify_cloud_devices, "_load_yeelight_client", lambda: FakeClient)

    summary = await verify_cloud_devices.async_probe_cloud_devices(
        region="cn",
        domain="https://api.yeelight.com/apis/iot",
        access_token="secret-token",
        house_id=429392,
        client_id="secret-client",
        timeout_seconds=3,
    )
    result = summary.as_dict()
    visible = json.dumps(result, sort_keys=True)

    assert result["ok"] is True
    assert result["network_attempted"] is True
    assert result["device_count"] == 3
    assert result["categories"] == {"curtain": 1, "light": 1, "unknown": 1}
    assert "secret-token" not in visible
    assert "429392" not in visible
    assert "secret-client" not in visible
    assert "secret-device" not in visible
    assert "Secret Light" not in visible
    assert "Secret Room" not in visible
