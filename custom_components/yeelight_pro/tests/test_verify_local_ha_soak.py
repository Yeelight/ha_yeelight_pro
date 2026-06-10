"""Tests for the dedicated local HA soak verification entrypoint."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

from scripts import verify_local_ha_soak

ROOT = Path(__file__).resolve().parents[3]


def test_build_soak_argv_adds_bounded_defaults() -> None:
    """Dedicated soak entrypoint should default to a bounded stability window."""
    assert verify_local_ha_soak.build_soak_argv(["--skip-docker"]) == [
        "--skip-docker",
        "--soak-seconds",
        "60",
        "--soak-interval",
        "15",
    ]


def test_build_soak_argv_preserves_explicit_window() -> None:
    """Operators can lengthen or shorten the soak window explicitly."""
    assert verify_local_ha_soak.build_soak_argv([
        "--soak-seconds",
        "300",
        "--soak-interval",
        "30",
    ]) == [
        "--soak-seconds",
        "300",
        "--soak-interval",
        "30",
    ]


def test_soak_main_delegates_to_shared_verifier(monkeypatch) -> None:
    """The soak script must reuse the shared verifier instead of copying checks."""
    calls: list[list[str]] = []

    def fake_main(argv: list[str]) -> int:
        calls.append(argv)
        return 7

    monkeypatch.setattr(verify_local_ha_soak, "verify_local_ha_main", fake_main)

    assert verify_local_ha_soak.main(["--skip-url"]) == 7
    assert calls == [["--skip-url", "--soak-seconds", "60", "--soak-interval", "15"]]


def test_script_help_path_execution_imports_cleanly() -> None:
    """Direct script execution should work from its file path."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "verify_local_ha_soak.py"), "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "--soak-seconds" in result.stdout
    assert "ModuleNotFoundError" not in result.stderr
