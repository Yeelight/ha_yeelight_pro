"""Release quality gate preflight tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import hacs_preflight


def test_release_quality_gate_check_requires_lint_and_type_check(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """preflight 应阻断本地/CI 发布质量门禁漂移."""
    root = tmp_path
    (root / ".github" / "workflows").mkdir(parents=True)
    _write_test_file(root / "requirements_test.txt", "pytest")
    _write_test_file(root / "hacs_publish.py", 'CHECKS = [["pytest", "-q"]]')
    _write_test_file(root / ".github" / "workflows" / "validate.yaml", "pytest")
    _write_test_file(root / "README.md", "pytest")
    _write_test_file(root / "README_zh.md", "pytest")
    _write_test_file(root / "RELEASE_GUIDE.md", "pytest")
    monkeypatch.setattr(hacs_preflight, "ROOT", root)

    errors = hacs_preflight._check_release_quality_gates()

    assert any("ruff dependency" in error for error in errors)
    assert any("mypy dependency" in error for error in errors)
    assert any("GitHub validate lint step" in error for error in errors)
    assert any("local release lint gate" in error for error in errors)
    assert any("local release compile command" in error for error in errors)


def test_release_quality_gate_reports_missing_publish_script(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """preflight 应报告缺失的发布脚本而不是崩溃."""
    root = tmp_path
    (root / ".github" / "workflows").mkdir(parents=True)
    _write_test_file(root / "requirements_test.txt", "ruff mypy")
    _write_test_file(root / ".github" / "workflows" / "validate.yaml", "")
    _write_test_file(root / ".github" / "workflows" / "release.yaml", "")
    _write_test_file(root / "README.md", "")
    _write_test_file(root / "README_zh.md", "")
    _write_test_file(root / "RELEASE_GUIDE.md", "")
    monkeypatch.setattr(hacs_preflight, "ROOT", root)

    errors = hacs_preflight._check_release_quality_gates()

    assert "release quality gate requires hacs_publish.py" in errors


def test_release_quality_gate_rejects_dynamic_publish_checks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """hacs_publish.py 的 CHECKS 必须是可静态审查的字面量."""
    root = tmp_path
    (root / ".github" / "workflows").mkdir(parents=True)
    _write_test_file(root / "requirements_test.txt", "ruff mypy")
    _write_test_file(root / "hacs_publish.py", "CHECKS = build_checks()")
    _write_test_file(root / ".github" / "workflows" / "validate.yaml", "")
    _write_test_file(root / ".github" / "workflows" / "release.yaml", "")
    _write_test_file(root / "README.md", "")
    _write_test_file(root / "README_zh.md", "")
    _write_test_file(root / "RELEASE_GUIDE.md", "")
    monkeypatch.setattr(hacs_preflight, "ROOT", root)

    errors = hacs_preflight._check_release_quality_gates()

    assert "hacs_publish.py must define literal CHECKS" in errors


def _write_test_file(path: Path, content: str) -> None:
    """Write a minimal synthetic file for preflight inspection."""
    path.write_text(content, encoding="utf-8")
