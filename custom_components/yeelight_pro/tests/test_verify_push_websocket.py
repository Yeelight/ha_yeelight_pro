"""Tests for the guarded production WebSocket probe script."""

from __future__ import annotations

from argparse import Namespace
import asyncio
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import AsyncMock

from aiohttp import WSMsgType

from scripts import verify_push_websocket

ROOT = Path(__file__).resolve().parents[3]


def test_validate_run_request_requires_explicit_confirm() -> None:
    """没有显式确认时必须 fail closed，不读取或输出 token."""
    args = Namespace(
        confirm_production_websocket=False,
        token_env="YEELIGHT_PRO_PUSH_TOKEN",
        duration_seconds=30,
        max_frames=20,
    )

    safety = verify_push_websocket.validate_run_request(
        args,
        {"YEELIGHT_PRO_PUSH_TOKEN": "secret-token"},
    )

    assert safety.allowed is False
    assert safety.token == ""
    assert safety.error == "missing_confirm_flag"


def test_validate_run_request_requires_token_env() -> None:
    """显式确认后仍必须从环境变量读取 token，不能走命令行参数."""
    args = Namespace(
        confirm_production_websocket=True,
        token_env="YEELIGHT_PRO_PUSH_TOKEN",
        duration_seconds=30,
        max_frames=20,
    )

    safety = verify_push_websocket.validate_run_request(args, {})

    assert safety.allowed is False
    assert safety.error == "missing_token_env"


def test_validate_run_request_accepts_bounded_explicit_run() -> None:
    """显式确认、token 环境变量和有界参数同时满足时才允许网络验证."""
    args = Namespace(
        confirm_production_websocket=True,
        token_env="YEELIGHT_PRO_PUSH_TOKEN",
        duration_seconds=30,
        max_frames=20,
    )

    safety = verify_push_websocket.validate_run_request(
        args,
        {"YEELIGHT_PRO_PUSH_TOKEN": "secret-token"},
    )

    assert safety.allowed is True
    assert safety.token == "secret-token"
    assert safety.error is None


def test_validate_run_request_rejects_unbounded_probe() -> None:
    """真实连接必须有时间和帧数上限，避免误跑成长连接."""
    args = Namespace(
        confirm_production_websocket=True,
        token_env="YEELIGHT_PRO_PUSH_TOKEN",
        duration_seconds=301,
        max_frames=20,
    )

    assert (
        verify_push_websocket.validate_run_request(
            args,
            {"YEELIGHT_PRO_PUSH_TOKEN": "secret-token"},
        ).error
        == "invalid_duration"
    )

    args.duration_seconds = 30
    args.max_frames = 1001

    assert (
        verify_push_websocket.validate_run_request(
            args,
            {"YEELIGHT_PRO_PUSH_TOKEN": "secret-token"},
        ).error
        == "invalid_max_frames"
    )


def test_summary_classifies_control_and_data_frames_without_payload_values() -> None:
    """摘要只能保留字段形态和聚合计数，不能复制设备或 token 值."""
    summary = verify_push_websocket.PushWebSocketProbeSummary()

    verify_push_websocket.update_summary_from_payload(
        summary,
        {"method": "subscribe", "code": "200", "token": "secret-token"},
    )
    verify_push_websocket.update_summary_from_payload(
        summary,
        {"method": "heartbeat", "success": False, "msg": "device-secret"},
    )
    verify_push_websocket.update_summary_from_payload(
        summary,
        {"type": "prop", "nodes": [{"id": "device-secret"}]},
    )
    verify_push_websocket.update_summary_from_payload(
        summary,
        {"type": "event", "params": {"mac": "aa:bb:cc:dd:ee:ff"}},
    )

    result = summary.as_dict()

    assert result["control_ack_frames"] == 1
    assert result["control_error_frames"] == 1
    assert result["data_frames"] == 2
    assert result["data_types"] == {"event": 1, "prop": 1}
    assert "secret-token" not in json.dumps(result)
    assert "device-secret" not in json.dumps(result)
    assert "aa:bb:cc" not in json.dumps(result)


def test_ws_message_summary_rejects_invalid_or_non_object_json() -> None:
    """非 object JSON 和不可解析 frame 只能进入 parse_error 聚合."""
    summary = verify_push_websocket.PushWebSocketProbeSummary()

    verify_push_websocket._update_summary_from_ws_message(
        summary,
        Namespace(type=WSMsgType.TEXT, data='["not-object"]'),
    )
    verify_push_websocket._update_summary_from_ws_message(
        summary,
        Namespace(type=WSMsgType.TEXT, data="not-json"),
    )

    assert summary.frames_seen == 2
    assert summary.parse_error_frames == 2
    assert summary.as_dict()["json_shapes"] == {}


def test_main_does_not_probe_network_without_confirm(monkeypatch, capsys) -> None:
    """默认 CLI 路径不能触发真实 WebSocket 连接."""
    probe = AsyncMock()
    monkeypatch.setattr(verify_push_websocket, "async_probe_push_websocket", probe)

    exit_code = verify_push_websocket.main([])

    assert exit_code == 2
    probe.assert_not_awaited()
    output = json.loads(capsys.readouterr().out)
    assert output == {
        "error": "missing_confirm_flag",
        "network_attempted": False,
        "ok": False,
    }


def test_script_path_execution_is_no_network_without_confirm() -> None:
    """直接执行脚本时也必须先 fail closed，不能因 import path 漏洞失败."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "verify_push_websocket.py")],
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
    """显式确认和 token 环境变量存在时才调用真实探测入口."""
    summary = verify_push_websocket.PushWebSocketProbeSummary(ok=True)
    probe = AsyncMock(return_value=summary)
    monkeypatch.setenv("YEELIGHT_PRO_PUSH_TOKEN", "secret-token")
    monkeypatch.setattr(verify_push_websocket, "async_probe_push_websocket", probe)

    exit_code = verify_push_websocket.main([
        "--confirm-production-websocket",
        "--duration-seconds",
        "1",
        "--max-frames",
        "1",
    ])

    assert exit_code == 0
    probe.assert_awaited_once_with(
        token="secret-token",
        duration_seconds=1.0,
        max_frames=1,
    )
    output = json.loads(capsys.readouterr().out)
    assert output["ok"] is True
    assert "secret-token" not in json.dumps(output)


async def test_probe_summarizes_heartbeat_cleanup_error_without_values(
    monkeypatch,
) -> None:
    """heartbeat task 清理失败只能进入异常类型摘要，不能泄漏 token 或消息."""

    class FailingHeartbeatWebSocket:
        def __init__(self):
            self.heartbeat_attempted = asyncio.Event()

        async def send_json(self, data):
            if data["method"] == "heartbeat":
                self.heartbeat_attempted.set()
                raise RuntimeError("secret-token device-secret")

        async def receive(self, *, timeout):
            await self.heartbeat_attempted.wait()
            return Namespace(type=WSMsgType.CLOSED, data=None)

    class FakeWebSocketContext:
        def __init__(self):
            self.websocket = FailingHeartbeatWebSocket()

        async def __aenter__(self):
            return self.websocket

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def ws_connect(self, url):
            assert "secret-token" in url
            return FakeWebSocketContext()

    async def immediate_sleep(delay):
        return None

    monkeypatch.setattr(verify_push_websocket.aiohttp, "ClientSession", FakeSession)
    monkeypatch.setattr(verify_push_websocket.asyncio, "sleep", immediate_sleep)

    summary = await verify_push_websocket.async_probe_push_websocket(
        token="secret-token",
        duration_seconds=1,
        max_frames=1,
    )
    result = summary.as_dict()

    assert result["ok"] is False
    assert result["network_attempted"] is True
    assert result["last_error_type"] == "RuntimeError"
    assert "secret-token" not in json.dumps(result)
    assert "device-secret" not in json.dumps(result)
