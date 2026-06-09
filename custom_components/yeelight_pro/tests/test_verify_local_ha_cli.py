"""Local HA verification CLI tests."""

from __future__ import annotations

import sys
from unittest.mock import Mock

import pytest

from scripts.local_ha_verification import cli
from scripts.verify_local_ha import VerificationReport, build_parser


def test_build_parser_accepts_repeat_options() -> None:
    """本地 HA verifier 应支持短时 repeat 检查，默认仍为单轮."""
    args = build_parser().parse_args(["--repeat", "3", "--repeat-delay", "0.5"])

    assert args.repeat == 3
    assert args.repeat_delay == 0.5


def test_build_parser_accepts_soak_options() -> None:
    """本地 HA verifier 应支持有上限的稳定性窗口采样."""
    args = build_parser().parse_args(["--soak-seconds", "1", "--soak-interval", "0.5"])

    assert args.soak_seconds == 1
    assert args.soak_interval == 0.5


@pytest.mark.parametrize(
    "args",
    [
        ["--repeat", "0"],
        ["--repeat-delay", "-1"],
        ["--soak-seconds", "-1"],
        ["--soak-interval", "0"],
    ],
)
def test_build_parser_rejects_invalid_repeat_options(args: list[str]) -> None:
    """repeat 参数必须避免无意义或负延迟配置."""
    with pytest.raises(SystemExit):
        build_parser().parse_args(args)


def test_main_runs_requested_repeat_count(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """repeat 模式应逐轮独立验证并输出运行次数."""
    run_once = Mock(
        side_effect=[
            _passing_report("first"),
            _passing_report("second"),
        ]
    )
    monkeypatch.setattr(sys, "argv", ["verify_local_ha.py", "--repeat", "2"])
    monkeypatch.setattr(cli, "_run_once", run_once)

    assert cli.main() == 0

    output = capsys.readouterr().out
    assert run_once.call_count == 2
    assert "-- run 1/2 --" in output
    assert "Local HA verification passed (2 runs)." in output


def test_main_fails_when_any_repeat_run_fails(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """任一 repeat 轮次失败时，CLI 结果必须失败."""
    run_once = Mock(
        side_effect=[
            _passing_report("first"),
            _failed_report("second"),
        ]
    )
    monkeypatch.setattr(sys, "argv", ["verify_local_ha.py", "--repeat", "2"])
    monkeypatch.setattr(cli, "_run_once", run_once)

    assert cli.main() == 1

    output = capsys.readouterr().out
    assert run_once.call_count == 2
    assert "[FAIL] second" in output
    assert "Local HA verification failed." in output


def test_main_fails_when_repeat_metrics_drift(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """repeat 模式应阻断关键聚合指标漂移."""
    run_once = Mock(
        side_effect=[
            _passing_report("first", metrics={"entities": 140}),
            _passing_report("second", metrics={"entities": 139}),
        ]
    )
    monkeypatch.setattr(sys, "argv", ["verify_local_ha.py", "--repeat", "2"])
    monkeypatch.setattr(cli, "_run_once", run_once)

    assert cli.main() == 1

    output = capsys.readouterr().out
    assert "stable metric drift in run 2: entities expected 140, got 139" in output
    assert "Local HA verification failed." in output


def test_main_reports_stable_metrics_when_repeat_metrics_match(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """repeat 模式应明确记录关键聚合指标未漂移."""
    run_once = Mock(
        side_effect=[
            _passing_report("first", metrics={"entities": 140}),
            _passing_report("second", metrics={"entities": 140}),
        ]
    )
    monkeypatch.setattr(sys, "argv", ["verify_local_ha.py", "--repeat", "2"])
    monkeypatch.setattr(cli, "_run_once", run_once)

    assert cli.main() == 0

    output = capsys.readouterr().out
    assert "stable metrics unchanged across verification runs" in output
    assert "Local HA verification passed (2 runs)." in output


def test_main_runs_soak_until_window_is_covered(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """soak 模式应在有界时间窗口内追加稳定性采样."""
    clock = _FakeClock()
    run_once = Mock(
        side_effect=[
            _passing_report("first"),
            _passing_report("second"),
            _passing_report("third"),
        ]
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["verify_local_ha.py", "--soak-seconds", "1", "--soak-interval", "0.5"],
    )
    monkeypatch.setattr(cli.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(cli.time, "sleep", clock.sleep)
    monkeypatch.setattr(cli, "_run_once", run_once)

    assert cli.main() == 0

    output = capsys.readouterr().out
    assert run_once.call_count == 3
    assert "-- run 3/3 --" in output
    assert "Local HA verification passed (3 runs, 1s soak)." in output


def test_main_fails_when_soak_run_fails(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """soak 窗口内任一采样失败时整体必须失败."""
    clock = _FakeClock()
    run_once = Mock(
        side_effect=[
            _passing_report("first"),
            _failed_report("second"),
            _passing_report("third"),
        ]
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["verify_local_ha.py", "--soak-seconds", "1", "--soak-interval", "0.5"],
    )
    monkeypatch.setattr(cli.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(cli.time, "sleep", clock.sleep)
    monkeypatch.setattr(cli, "_run_once", run_once)

    assert cli.main() == 1

    output = capsys.readouterr().out
    assert run_once.call_count == 3
    assert "[FAIL] second" in output
    assert "Local HA verification failed." in output


def test_run_once_keeps_synthetic_recovery_check_when_docker_is_skipped(
    tmp_path,
) -> None:
    """跳过 Docker 时仍应执行离线 runtime recovery 合同自检."""
    args = build_parser().parse_args([
        "--config-dir",
        str(tmp_path / "missing-config"),
        "--skip-docker",
        "--skip-url",
    ])

    report = cli._run_once(args)

    assert "synthetic runtime recovery classification passed" in report.facts
    assert report.metrics["synthetic_runtime_recovery"] == "passed"


class _FakeClock:
    """Tiny monotonic clock for deterministic CLI soak tests."""

    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        """Return the current fake monotonic timestamp."""
        return self.now

    def sleep(self, seconds: float) -> None:
        """Advance the fake monotonic timestamp."""
        self.now += seconds


def _passing_report(
    message: str,
    *,
    metrics: dict[str, object] | None = None,
) -> VerificationReport:
    """Return a passing synthetic verification report."""
    report = VerificationReport()
    report.fact(message)
    if metrics:
        report.metrics.update(metrics)
    return report


def _failed_report(message: str) -> VerificationReport:
    """Return a failing synthetic verification report."""
    report = VerificationReport()
    report.fail(message)
    return report
