"""HACS publication helper CLI tests."""

from __future__ import annotations

import subprocess

import pytest

import hacs_publish


def test_check_mode_runs_local_release_checks(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--check 是显式只读本地发布检查入口."""
    called = False

    def fake_run_checks() -> bool:
        nonlocal called
        called = True
        return True

    monkeypatch.setattr(hacs_publish, "_run_checks", fake_run_checks)

    assert hacs_publish.main(["--check"]) == 0

    assert called is True
    assert "Local checks passed." in capsys.readouterr().out


def test_unknown_argument_fails_fast() -> None:
    """未知参数不能被发布脚本静默忽略."""
    with pytest.raises(SystemExit) as exc_info:
        hacs_publish.main(["--unknown"])

    assert exc_info.value.code == 2


def test_run_checks_uses_release_root_cwd(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """发布检查必须固定在扩展根目录执行."""
    calls: list[tuple[list[str], bool, object]] = []

    def fake_run(command: list[str], *, check: bool, cwd: object) -> object:
        calls.append((command, check, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(hacs_publish.subprocess, "run", fake_run)

    assert hacs_publish._run_checks() is True

    assert calls
    assert all(check is False for _, check, _ in calls)
    assert {cwd for _, _, cwd in calls} == {hacs_publish.ROOT}
