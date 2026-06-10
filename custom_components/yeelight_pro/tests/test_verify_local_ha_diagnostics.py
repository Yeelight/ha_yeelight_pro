"""Local HA diagnostics capability verification tests."""

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


def test_verify_diagnostics_capabilities_accepts_release_boundaries(
    tmp_path: Path,
) -> None:
    """安装态 diagnostics capability flags 应保持已验证能力和禁用 live 能力边界."""
    install_root = _install_root(tmp_path)
    _write_diagnostics(install_root)
    _write_diagnostic_options(install_root)
    _write_diagnostic_payloads(install_root)
    _write_websocket_event_runtime(install_root)
    report = VerificationReport()

    verify_diagnostics_capabilities(tmp_path, report)

    assert report.ok
    assert any("diagnostics capability flags" in fact for fact in report.facts)
    assert any("diagnostics option_status fields" in fact for fact in report.facts)
    assert any("scan-login device identifier" in fact for fact in report.facts)
    assert any("WebSocket-only event runtime contract" in fact for fact in report.facts)


def test_verify_diagnostics_capabilities_rejects_enabled_live_flag(
    tmp_path: Path,
) -> None:
    """仍未验证的 live capability flag 不能在安装态变成 true."""
    install_root = _install_root(tmp_path)
    _write_diagnostics(install_root, mqtt_subscription=True)
    _write_diagnostic_options(install_root)
    _write_diagnostic_payloads(install_root)
    _write_websocket_event_runtime(install_root)
    report = VerificationReport()

    verify_diagnostics_capabilities(tmp_path, report)

    assert not report.ok
    assert any("mqtt_subscription" in failure for failure in report.failures)


def test_verify_diagnostics_capabilities_rejects_ambiguous_oauth_flow_flag(
    tmp_path: Path,
) -> None:
    """安装态 diagnostics 不应恢复容易误解的 OAuth flow capability key."""
    install_root = _install_root(tmp_path)
    _write_diagnostics(install_root, include_ambiguous_oauth=True)
    _write_diagnostic_options(install_root)
    _write_diagnostic_payloads(install_root)
    _write_websocket_event_runtime(install_root)
    report = VerificationReport()

    verify_diagnostics_capabilities(tmp_path, report)

    assert not report.ok
    assert any("oauth_authorization_code_flow" in failure for failure in report.failures)


def test_verify_diagnostics_capabilities_requires_literal_flags(tmp_path: Path) -> None:
    """本地 HA verifier 不应导入 runtime，应要求静态可解析的 capability flags."""
    install_root = _install_root(tmp_path)
    (install_root / "diagnostics.py").write_text(
        "def _client_capabilities_for_entry(entry):\n    return flags_from_runtime()\n",
        encoding="utf-8",
    )
    _write_diagnostic_options(install_root)
    _write_diagnostic_payloads(install_root)
    _write_websocket_event_runtime(install_root)
    report = VerificationReport()

    verify_diagnostics_capabilities(tmp_path, report)

    assert not report.ok
    assert any("literal client capability flags" in failure for failure in report.failures)


def test_verify_diagnostics_capabilities_requires_option_status_fields(
    tmp_path: Path,
) -> None:
    """安装态 verifier 应阻断 option_status 丢失 runtime-only options 字段."""
    install_root = _install_root(tmp_path)
    _write_diagnostics(install_root)
    _write_diagnostic_options(install_root, include_scan_interval=False)
    _write_diagnostic_payloads(install_root)
    _write_websocket_event_runtime(install_root)
    report = VerificationReport()

    verify_diagnostics_capabilities(tmp_path, report)

    assert not report.ok
    assert any("scan_interval_seconds" in failure for failure in report.failures)


def test_verify_diagnostics_capabilities_requires_option_status_tokens(
    tmp_path: Path,
) -> None:
    """安装态 verifier 应阻断弱化归一化或 filter 聚合语义的 option_status."""
    install_root = _install_root(tmp_path)
    _write_diagnostics(install_root)
    _write_diagnostic_options(install_root, include_normalize_token=False)
    _write_diagnostic_payloads(install_root)
    _write_websocket_event_runtime(install_root)
    report = VerificationReport()

    verify_diagnostics_capabilities(tmp_path, report)

    assert not report.ok
    assert any("normalize_entry_options" in failure for failure in report.failures)


def test_verify_diagnostics_capabilities_requires_scan_login_device_redaction(
    tmp_path: Path,
) -> None:
    """安装态 diagnostics 必须脱敏扫码登录 device 唯一标识."""
    install_root = _install_root(tmp_path)
    _write_diagnostics(install_root)
    _write_diagnostic_options(install_root)
    _write_diagnostic_payloads(install_root, include_scan_login_device=False)
    _write_websocket_event_runtime(install_root)
    report = VerificationReport()

    verify_diagnostics_capabilities(tmp_path, report)

    assert not report.ok
    assert any("CONF_SCAN_LOGIN_DEVICE" in failure for failure in report.failures)
    assert any("TO_REDACT" in failure for failure in report.failures)
