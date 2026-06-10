"""Local HA WebSocket runtime verifier tests."""

from __future__ import annotations

from pathlib import Path

from scripts.verify_local_ha import (
    VerificationReport,
    verify_diagnostics_capabilities,
)

from .local_ha_diagnostics_verifier_helpers import (
    install_root as _install_root,
    write_diagnostic_options as _write_diagnostic_options,
    write_diagnostic_payloads as _write_diagnostic_payloads,
    write_diagnostics as _write_diagnostics,
    write_websocket_event_runtime as _write_websocket_event_runtime,
)


def test_verify_diagnostics_capabilities_requires_websocket_event_runtime(
    tmp_path: Path,
) -> None:
    """安装态 verifier 应阻断丢失 WebSocket 事件通知 runtime 链路."""
    root = _install_root(tmp_path)
    _write_required_diagnostics(root)
    _write_websocket_event_runtime(root, include_transport=False)
    report = VerificationReport()

    verify_diagnostics_capabilities(tmp_path, report)

    assert not report.ok
    assert any("push_transport.py" in failure for failure in report.failures)


def test_verify_diagnostics_capabilities_accepts_websocket_event_runtime(
    tmp_path: Path,
) -> None:
    """安装态 WebSocket 事件通知 runtime 链路完整时应记录成功 fact."""
    root = _install_root(tmp_path)
    _write_required_diagnostics(root)
    _write_websocket_event_runtime(root)
    report = VerificationReport()

    verify_diagnostics_capabilities(tmp_path, report)

    assert report.ok
    assert any("WebSocket-only event runtime contract" in fact for fact in report.facts)


def test_verify_diagnostics_capabilities_requires_websocket_runtime_health(
    tmp_path: Path,
) -> None:
    """安装态 verifier 应阻断 WebSocket runtime 运行期错误诊断丢失."""
    root = _install_root(tmp_path)
    _write_required_diagnostics(root)
    _write_websocket_event_runtime(root, include_runtime_health=False)
    report = VerificationReport()

    verify_diagnostics_capabilities(tmp_path, report)

    assert not report.ok
    assert any("last_runtime_error_type" in failure for failure in report.failures)
    assert any("_sync_transport_runtime_error" in failure for failure in report.failures)


def test_verify_diagnostics_capabilities_rejects_eventsource_runtime(
    tmp_path: Path,
) -> None:
    """易来事件通知只有 WebSocket，安装态不能出现 SSE/EventSource runtime."""
    root = _install_root(tmp_path)
    _write_required_diagnostics(root)
    _write_websocket_event_runtime(root, include_eventsource=True)
    report = VerificationReport()

    verify_diagnostics_capabilities(tmp_path, report)

    assert not report.ok
    assert any("SSE runtime path" in failure for failure in report.failures)
    assert any("EventSource runtime path" in failure for failure in report.failures)


def test_verify_diagnostics_capabilities_requires_websocket_call_edges(
    tmp_path: Path,
) -> None:
    """安装态 WebSocket runtime 必须真实构造 transport 并调用 ws_connect."""
    root = _install_root(tmp_path)
    _write_required_diagnostics(root)
    _write_websocket_event_runtime(
        root,
        include_live_transport_call=False,
        include_ws_connect_call=False,
    )
    report = VerificationReport()

    verify_diagnostics_capabilities(tmp_path, report)

    assert not report.ok
    assert any("YeelightPushWebSocketTransport()" in failure for failure in report.failures)
    assert any("*.ws_connect()" in failure for failure in report.failures)


def _write_required_diagnostics(root: Path) -> None:
    """Write non-WebSocket diagnostics fixtures required by the aggregate verifier."""
    _write_diagnostics(root)
    _write_diagnostic_options(root)
    _write_diagnostic_payloads(root)
