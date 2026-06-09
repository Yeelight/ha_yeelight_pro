"""Local HA runtime verification tests."""

from __future__ import annotations

import subprocess
from unittest.mock import Mock

from scripts.verify_local_ha import (
    VerificationReport,
    verify_logs,
    verify_synthetic_log_recovery,
)


def test_verify_logs_records_recovered_polling_errors_as_fact(
    monkeypatch,
) -> None:
    """已恢复的轮询连接错误不应阻断本地 HA 验证."""
    output = "\n".join([
        (
            "2026-06-07 ERROR (MainThread) "
            "[custom_components.yeelight_pro.core.coordinator] "
            "Connection error while updating Yeelight Pro data: ConnectionError"
        ),
        (
            "2026-06-07 ERROR (MainThread) "
            "[custom_components.yeelight_pro.core.coordinator] "
            "Error fetching yeelight_pro data: Connection error: ConnectionError"
        ),
        (
            "2026-06-07 INFO (MainThread) "
            "[custom_components.yeelight_pro.core.coordinator] "
            "Fetching yeelight_pro data recovered"
        ),
        "Yeelight Pro integration setup complete",
    ])
    monkeypatch.setattr(
        "scripts.local_ha_verification.runtime._run",
        Mock(return_value=subprocess.CompletedProcess([], 0, output, "")),
    )
    report = VerificationReport()

    verify_logs("ha", report, tail=100)

    assert report.ok
    assert not report.warnings
    assert any("transient polling error" in fact for fact in report.facts)


def test_verify_logs_fails_for_unrecovered_yeelight_errors(monkeypatch) -> None:
    """没有恢复日志的 Yeelight Pro ERROR 仍应阻断验证."""
    output = (
        "2026-06-07 ERROR (MainThread) "
        "[custom_components.yeelight_pro.core.coordinator] "
        "Error communicating with API while updating Yeelight Pro data: TimeoutError"
    )
    monkeypatch.setattr(
        "scripts.local_ha_verification.runtime._run",
        Mock(return_value=subprocess.CompletedProcess([], 0, output, "")),
    )
    report = VerificationReport()

    verify_logs("ha", report, tail=100)

    assert not report.ok
    assert any("unrecovered error" in failure for failure in report.failures)


def test_verify_logs_fails_for_error_after_latest_recovery(monkeypatch) -> None:
    """恢复标记之后再次出现的轮询错误必须视为未恢复."""
    repeated_error = (
        "2026-06-07 ERROR (MainThread) "
        "[custom_components.yeelight_pro.core.coordinator] "
        "Error fetching yeelight_pro data: Connection error: ConnectionError"
    )
    output = "\n".join([
        repeated_error,
        (
            "2026-06-07 INFO (MainThread) "
            "[custom_components.yeelight_pro.core.coordinator] "
            "Fetching yeelight_pro data recovered"
        ),
        repeated_error,
        "Yeelight Pro integration setup complete",
    ])
    monkeypatch.setattr(
        "scripts.local_ha_verification.runtime._run",
        Mock(return_value=subprocess.CompletedProcess([], 0, output, "")),
    )
    report = VerificationReport()

    verify_logs("ha", report, tail=100)

    assert not report.ok
    assert any("unrecovered error log lines found: 1" in failure for failure in report.failures)
    assert any("transient polling error log lines recovered: 1" in fact for fact in report.facts)


def test_verify_synthetic_log_recovery_records_contract_fact() -> None:
    """每轮本地 HA 验证都应自检恢复分类合同."""
    report = VerificationReport()

    verify_synthetic_log_recovery(report)

    assert report.ok
    assert "synthetic runtime recovery classification passed" in report.facts
    assert report.metrics["synthetic_runtime_recovery"] == "passed"


def test_verify_synthetic_log_recovery_fails_on_classifier_drift(
    monkeypatch,
) -> None:
    """恢复分类逻辑漂移时 synthetic 检查必须阻断."""
    monkeypatch.setattr(
        "scripts.local_ha_verification.runtime._split_blocking_yeelight_errors",
        Mock(return_value=([], [])),
    )
    report = VerificationReport()

    verify_synthetic_log_recovery(report)

    assert not report.ok
    assert "synthetic runtime recovery classification failed" in report.failures
