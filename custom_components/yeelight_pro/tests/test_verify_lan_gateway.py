"""Tests for the guarded production LAN gateway probe script."""

from __future__ import annotations

from argparse import Namespace
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import AsyncMock

import pytest

from scripts import verify_lan_gateway

ROOT = Path(__file__).resolve().parents[3]


def _args(**overrides) -> Namespace:
    values = {
        "confirm_production_lan_gateway": False,
        "host_env": "YEELIGHT_PRO_LAN_GATEWAY_HOST",
        "port_env": "YEELIGHT_PRO_LAN_GATEWAY_PORT",
        "timeout_seconds": 5,
        "max_frames": 5,
    }
    values.update(overrides)
    return Namespace(**values)


def test_validate_run_request_requires_explicit_confirm() -> None:
    """没有显式确认时必须 fail closed，不读取或输出 LAN host."""
    safety = verify_lan_gateway.validate_run_request(
        _args(),
        {"YEELIGHT_PRO_LAN_GATEWAY_HOST": "192.168.1.20"},
    )

    assert safety.allowed is False
    assert safety.host == ""
    assert safety.error == "missing_confirm_flag"


def test_validate_run_request_requires_host_env() -> None:
    """显式确认后仍必须从环境变量读取 gateway host."""
    safety = verify_lan_gateway.validate_run_request(
        _args(confirm_production_lan_gateway=True),
        {},
    )

    assert safety.allowed is False
    assert safety.error == "missing_host_env"


def test_validate_run_request_accepts_bounded_explicit_run() -> None:
    """显式确认、host 环境变量和有界参数同时满足时才允许 LAN 验证."""
    safety = verify_lan_gateway.validate_run_request(
        _args(confirm_production_lan_gateway=True, timeout_seconds=3, max_frames=2),
        {
            "YEELIGHT_PRO_LAN_GATEWAY_HOST": "192.168.1.20",
            "YEELIGHT_PRO_LAN_GATEWAY_PORT": "65444",
        },
    )

    assert safety.allowed is True
    assert safety.host == "192.168.1.20"
    assert safety.port == 65444
    assert safety.timeout_seconds == 3
    assert safety.max_frames == 2
    assert safety.error is None


def test_validate_run_request_rejects_invalid_port_timeout_and_frame_limit() -> None:
    """真实 LAN 探针必须有合法端口和有界读取窗口."""
    environ = {"YEELIGHT_PRO_LAN_GATEWAY_HOST": "192.168.1.20"}

    assert (
        verify_lan_gateway.validate_run_request(
            _args(confirm_production_lan_gateway=True),
            {**environ, "YEELIGHT_PRO_LAN_GATEWAY_PORT": "not-int"},
        ).error
        == "invalid_port_env"
    )
    assert (
        verify_lan_gateway.validate_run_request(
            _args(confirm_production_lan_gateway=True, timeout_seconds=61),
            environ,
        ).error
        == "invalid_timeout"
    )
    assert (
        verify_lan_gateway.validate_run_request(
            _args(confirm_production_lan_gateway=True, max_frames=101),
            environ,
        ).error
        == "invalid_max_frames"
    )


def test_summary_classifies_lan_frames_without_payload_values() -> None:
    """摘要只能保留帧计数和 method 聚合，不能复制设备或 payload 值."""
    summary = verify_lan_gateway.LanGatewayProbeSummary(
        ok=True,
        network_attempted=True,
    )

    verify_lan_gateway._update_summary_from_payload(
        summary,
        {
            "version": "1.0",
            "id": 1,
            "method": "gateway_post.topology",
            "nodes": [{"id": "secret-device", "mac": "aa:bb:cc:dd:ee:ff"}],
        },
    )
    verify_lan_gateway._update_summary_from_payload(
        summary,
        {
            "version": "1.0",
            "id": 2,
            "method": "gateway_post.prop",
            "nodes": [{"id": "secret-device", "params": {"p": True}}],
        },
    )
    verify_lan_gateway._update_summary_from_payload(
        summary,
        {"version": "1.0", "id": 3, "method": "gateway_post.event"},
    )
    result = summary.as_dict()
    visible = json.dumps(result, sort_keys=True)

    assert result["frames_seen"] == 3
    assert result["topology_frames"] == 1
    assert result["property_frames"] == 1
    assert result["event_frames"] == 1
    assert result["methods"] == {
        "gateway_post.event": 1,
        "gateway_post.prop": 1,
        "gateway_post.topology": 1,
    }
    assert "secret-device" not in visible
    assert "aa:bb:cc" not in visible
    assert '"p"' not in visible


def test_main_does_not_probe_network_without_confirm(monkeypatch, capsys) -> None:
    """默认 CLI 路径不能触发真实 LAN TCP 连接."""
    probe = AsyncMock()
    monkeypatch.setattr(verify_lan_gateway, "async_probe_lan_gateway", probe)

    exit_code = verify_lan_gateway.main([])

    assert exit_code == 2
    probe.assert_not_awaited()
    assert json.loads(capsys.readouterr().out) == {
        "error": "missing_confirm_flag",
        "network_attempted": False,
        "ok": False,
    }


def test_script_path_execution_is_no_network_without_confirm() -> None:
    """直接执行脚本时也必须先 fail closed，不能尝试连接网关."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "verify_lan_gateway.py")],
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
    """显式确认和 host 环境变量存在时才调用 LAN 探测入口."""
    summary = verify_lan_gateway.LanGatewayProbeSummary(ok=True)
    probe = AsyncMock(return_value=summary)
    monkeypatch.setenv("YEELIGHT_PRO_LAN_GATEWAY_HOST", "192.168.1.20")
    monkeypatch.setenv("YEELIGHT_PRO_LAN_GATEWAY_PORT", "65444")
    monkeypatch.setattr(verify_lan_gateway, "async_probe_lan_gateway", probe)

    exit_code = verify_lan_gateway.main([
        "--confirm-production-lan-gateway",
        "--timeout-seconds",
        "3",
        "--max-frames",
        "2",
    ])

    assert exit_code == 0
    probe.assert_awaited_once_with(
        host="192.168.1.20",
        port=65444,
        timeout_seconds=3.0,
        max_frames=2,
    )
    output = json.loads(capsys.readouterr().out)
    assert output["ok"] is True
    assert "192.168.1.20" not in json.dumps(output)
    assert "65444" not in json.dumps(output)


@pytest.mark.asyncio
async def test_probe_summarizes_lan_frames_without_values(monkeypatch) -> None:
    """生产探针聚合 LAN 网关帧，不输出 host、设备或原始 payload."""

    class FakeReader:
        def __init__(self) -> None:
            self._chunks = [
                (
                    b'{"version":"1.0","id":1,"method":"gateway_post.topology",'
                    b'"nodes":[{"id":"secret-device","mac":"aa:bb:cc"}]}\r\n'
                    b'{"version":"1.0","id":2,"method":"gateway_post.prop",'
                    b'"nodes":[{"id":"secret-device","params":{"p":true}}]}\r\n'
                ),
                b"",
            ]

        async def read(self, size: int) -> bytes:
            return self._chunks.pop(0)

    class FakeWriter:
        def __init__(self) -> None:
            self.written: list[bytes] = []
            self.closed = False
            self.wait_closed_count = 0

        def write(self, data: bytes) -> None:
            self.written.append(data)

        async def drain(self) -> None:
            return None

        def close(self) -> None:
            self.closed = True

        async def wait_closed(self) -> None:
            self.wait_closed_count += 1

    writer = FakeWriter()

    async def fake_open_connection(host: str, port: int):
        assert (host, port) == ("192.168.1.20", 65444)
        return FakeReader(), writer

    monkeypatch.setattr(
        verify_lan_gateway.asyncio,
        "open_connection",
        fake_open_connection,
    )

    summary = await verify_lan_gateway.async_probe_lan_gateway(
        host="192.168.1.20",
        port=65444,
        timeout_seconds=3,
        max_frames=5,
    )
    result = summary.as_dict()
    visible = json.dumps(result, sort_keys=True)

    assert result["ok"] is True
    assert result["network_attempted"] is True
    assert result["connected"] is True
    assert result["sent_topology_request"] is True
    assert result["frames_seen"] == 2
    assert result["topology_frames"] == 1
    assert result["property_frames"] == 1
    assert writer.closed is True
    assert writer.wait_closed_count == 1
    sent = writer.written[0].decode("utf-8")
    assert '"method":"gateway_get.topology"' in sent
    assert "192.168.1.20" not in visible
    assert "65444" not in visible
    assert "secret-device" not in visible
    assert "aa:bb:cc" not in visible
