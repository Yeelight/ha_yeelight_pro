"""Local HA runtime verification tests."""

from __future__ import annotations

import subprocess
from unittest.mock import Mock

from scripts.verify_local_ha import (
    DEFAULT_ENTITY_COUNTS,
    VerificationReport,
    verify_logs,
    verify_runtime_entity_counts,
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


def test_verify_runtime_entity_counts_accepts_active_distribution() -> None:
    """runtime active 分布来自日志，不应使用 retained registry 总量."""
    report = VerificationReport()

    verify_runtime_entity_counts(
        _runtime_entity_lines(DEFAULT_ENTITY_COUNTS),
        report,
        expected_entity_counts=DEFAULT_ENTITY_COUNTS,
    )

    assert report.ok
    assert any("runtime active entities: 158" in fact for fact in report.facts)
    assert report.metrics["runtime_entities"] == 158
    assert report.metrics["runtime_entity_domains"] == dict(
        sorted(DEFAULT_ENTITY_COUNTS.items())
    )


def test_verify_runtime_entity_counts_normalizes_spaced_platform_logs() -> None:
    """binary_sensor 平台日志会写成 binary sensor，verifier 必须归一化."""
    report = VerificationReport()
    lines = _runtime_entity_lines(DEFAULT_ENTITY_COUNTS, spaced_binary=True)

    verify_runtime_entity_counts(
        lines,
        report,
        expected_entity_counts=DEFAULT_ENTITY_COUNTS,
    )

    assert report.ok
    runtime_domains = report.metrics["runtime_entity_domains"]
    assert isinstance(runtime_domains, dict)
    assert runtime_domains["binary_sensor"] == 16


def test_verify_runtime_entity_counts_rejects_old_switch_leak() -> None:
    """旧的非开关品类泄漏 switch 数量必须在 runtime 侧失败."""
    counts = dict(DEFAULT_ENTITY_COUNTS)
    counts["switch"] = 87
    report = VerificationReport()

    verify_runtime_entity_counts(
        _runtime_entity_lines(counts),
        report,
        expected_entity_counts=DEFAULT_ENTITY_COUNTS,
    )

    assert not report.ok
    assert any(
        "runtime entity domain distribution exceeds retained registry" in failure
        for failure in report.failures
    )


def test_verify_runtime_entity_counts_allows_registry_retained_stale_domains() -> None:
    """runtime 可少于 registry retained，用于显式 cleanup 前的旧实体提示审计."""
    counts = dict(DEFAULT_ENTITY_COUNTS)
    counts.pop("sensor")
    counts.pop("binary_sensor")
    report = VerificationReport()

    verify_runtime_entity_counts(
        _runtime_entity_lines(counts),
        report,
        expected_entity_counts=DEFAULT_ENTITY_COUNTS,
    )

    assert report.ok
    assert any(
        "runtime omitted retained registry domains" in fact
        for fact in report.facts
    )


def test_verify_runtime_entity_counts_rejects_reconcile_total_mismatch() -> None:
    """runtime add 总量必须和 registry reconcile active 数一致."""
    report = VerificationReport()
    lines = _runtime_entity_lines(DEFAULT_ENTITY_COUNTS, active=170)

    verify_runtime_entity_counts(
        lines,
        report,
        expected_entity_counts=DEFAULT_ENTITY_COUNTS,
    )

    assert not report.ok
    assert any("runtime active entity total mismatch" in failure for failure in report.failures)


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


def _runtime_entity_lines(
    counts: dict[str, int],
    *,
    active: int | None = None,
    spaced_binary: bool = False,
) -> list[str]:
    """Return representative HA log lines for active entity verification."""
    active_count = sum(counts.values()) if active is None else active
    return [
        f"2026-06-10 INFO [custom_components.yeelight_pro.dynamic_entities] "
        f"Added {count} {_log_domain(domain, spaced_binary=spaced_binary)} entities"
        for domain, count in counts.items()
    ] + [
        "2026-06-10 INFO [custom_components.yeelight_pro.entity_lifecycle] "
        "Reconciled Yeelight Pro entity registry for entry entry-1: "
        f"active={active_count} pending_stale=0 disabled=0 restored=0",
    ]


def _log_domain(domain: str, *, spaced_binary: bool) -> str:
    """Return a domain as HA component logs print it."""
    if spaced_binary and domain == "binary_sensor":
        return "binary sensor"
    return domain
