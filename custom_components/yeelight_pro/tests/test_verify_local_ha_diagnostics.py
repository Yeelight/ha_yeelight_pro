"""Local HA diagnostics capability verification tests."""

from __future__ import annotations

from pathlib import Path

from scripts.verify_local_ha import (
    VerificationReport,
    verify_diagnostics_capabilities,
)


def test_verify_diagnostics_capabilities_accepts_release_boundaries(
    tmp_path: Path,
) -> None:
    """安装态 diagnostics capability flags 应保持已验证能力和禁用 live 能力边界."""
    install_root = _install_root(tmp_path)
    _write_diagnostics(install_root)
    _write_diagnostic_options(install_root)
    report = VerificationReport()

    verify_diagnostics_capabilities(tmp_path, report)

    assert report.ok
    assert any("diagnostics capability flags" in fact for fact in report.facts)
    assert any("diagnostics option_status fields" in fact for fact in report.facts)


def test_verify_diagnostics_capabilities_rejects_enabled_live_flag(
    tmp_path: Path,
) -> None:
    """仍未验证的 live capability flag 不能在安装态变成 true."""
    install_root = _install_root(tmp_path)
    _write_diagnostics(install_root, mqtt_subscription=True)
    _write_diagnostic_options(install_root)
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
    report = VerificationReport()

    verify_diagnostics_capabilities(tmp_path, report)

    assert not report.ok
    assert any("normalize_entry_options" in failure for failure in report.failures)


def _install_root(config_dir: Path) -> Path:
    """Create a minimal installed component root."""
    install_root = config_dir / "custom_components" / "yeelight_pro"
    install_root.mkdir(parents=True)
    return install_root


def _write_diagnostics(
    install_root: Path,
    *,
    mqtt_subscription: bool = False,
    include_ambiguous_oauth: bool = False,
) -> None:
    """Write minimal diagnostics.py capability flags."""
    ambiguous_oauth = (
        '        "oauth_authorization_code_flow": True,\n'
        if include_ambiguous_oauth
        else ""
    )
    install_root.joinpath("diagnostics.py").write_text(
        f"""
def _client_capabilities_for_entry(entry):
    return {{
        "oauth_contract": True,
        "oauth_token_runtime": True,
        "manual_oauth_authorization_code_exchange": True,
        "scan_login_contract": True,
        "scan_login_runtime": True,
{ambiguous_oauth.rstrip()}
        "oauth_flow": False,
        "refresh_token_contract": True,
        "refresh_token_runtime": True,
        "push_message_adapter": True,
        "runtime_payload_bridge": True,
        "websocket_message_contract": True,
        "websocket_transport_skeleton": True,
        "push_manager_contract": True,
        "lan_discovery_parser": True,
        "lan_message_contract": True,
        "lan_payload_adapter": True,
        "analytics_contract": True,
        "push_connection": True,
        "websocket_subscription": True,
        "local_gateway_control": True,
        "lan_control": True,
        "mqtt_subscription": {mqtt_subscription},
        "analytics_runtime": True,
    }}
""",
        encoding="utf-8",
    )


def _write_diagnostic_options(
    install_root: Path,
    *,
    include_scan_interval: bool = True,
    include_normalize_token: bool = True,
) -> None:
    """Write minimal diagnostic_options.py option_status contract."""
    normalize_token = (
        "normalize_entry_options(entry_options)\n"
        if include_normalize_token
        else "dict(entry_options)\n"
    )
    scan_field = (
        '        "scan_interval_seconds": 30,\n'
        if include_scan_interval
        else ""
    )
    install_root.joinpath("diagnostic_options.py").write_text(
        f"""
CONF_DEVICE_IMPORT_FILTER = "device_import_filter"
CONF_ANALYTICS_RUNTIME = "analytics_runtime"
CONF_ANALYTICS_RETENTION_DAYS = "analytics_retention_days"

def option_status_diagnostics(entry, runtime, coordinator):
    entry_options = {{}}
    {normalize_token.rstrip()}
    return {{
        "debug_mode_enabled": False,
{scan_field.rstrip()}
        "live_updates_enabled": False,
        "local_gateway_control_enabled": False,
        "analytics_runtime_enabled": False,
        "analytics_retention_days": 30,
        "import_filter_active": bool(entry_options.get(CONF_DEVICE_IMPORT_FILTER)),
    }}
""",
        encoding="utf-8",
    )
