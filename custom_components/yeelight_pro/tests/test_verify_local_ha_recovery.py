"""Tests for the dedicated local HA recovery verification entrypoint."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

from scripts import verify_local_ha_recovery

ROOT = Path(__file__).resolve().parents[3]


def test_build_recovery_argv_adds_repeat_and_log_tail_defaults() -> None:
    """Dedicated recovery entrypoint should default to repeated log validation."""
    assert verify_local_ha_recovery.build_recovery_argv(["--skip-url"]) == [
        "--skip-url",
        "--repeat",
        "2",
        "--log-tail",
        "2000",
    ]


def test_build_recovery_argv_preserves_explicit_repeat_and_log_tail() -> None:
    """Operators can explicitly choose a wider recovery validation window."""
    assert verify_local_ha_recovery.build_recovery_argv([
        "--repeat",
        "4",
        "--log-tail",
        "5000",
    ]) == [
        "--repeat",
        "4",
        "--log-tail",
        "5000",
    ]


def test_build_recovery_argv_rejects_skip_docker() -> None:
    """Recovery validation must not skip Docker logs or container health."""
    try:
        verify_local_ha_recovery.build_recovery_argv(["--skip-docker"])
    except ValueError as err:
        assert "requires Docker log access" in str(err)
    else:
        raise AssertionError("expected --skip-docker to be rejected")


def test_recovery_main_delegates_to_shared_verifier(monkeypatch) -> None:
    """The recovery script must reuse the shared verifier instead of copying checks."""
    calls: list[list[str]] = []

    def fake_main(argv: list[str]) -> int:
        calls.append(argv)
        return 9

    monkeypatch.setattr(verify_local_ha_recovery, "verify_local_ha_main", fake_main)

    assert verify_local_ha_recovery.main(["--skip-url"]) == 9
    assert calls == [["--skip-url", "--repeat", "2", "--log-tail", "2000"]]


def test_recovery_main_reports_skip_docker_rejection(capsys) -> None:
    """The script path should fail closed when asked to skip Docker logs."""
    assert verify_local_ha_recovery.main(["--skip-docker"]) == 2
    assert "requires Docker log access" in capsys.readouterr().err


def test_script_help_path_execution_imports_cleanly() -> None:
    """Direct script execution should work from its file path."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "verify_local_ha_recovery.py"), "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "--log-tail" in result.stdout
    assert "ModuleNotFoundError" not in result.stderr
