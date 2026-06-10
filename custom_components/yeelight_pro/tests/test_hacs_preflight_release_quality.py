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
    (root / ".github" / "ISSUE_TEMPLATE").mkdir(parents=True)
    _write_test_file(root / "requirements_test.txt", "pytest")
    _write_test_file(root / "hacs_publish.py", 'CHECKS = [["pytest", "-q"]]')
    _write_test_file(root / ".github" / "workflows" / "validate.yaml", "pytest")
    _write_test_file(root / ".github" / "workflows" / "release.yaml", "pytest")
    _write_test_file(root / ".github" / "ISSUE_TEMPLATE" / "bug_report.yml", "")
    _write_test_file(root / ".github" / "ISSUE_TEMPLATE" / "feature_request.yml", "")
    _write_test_file(root / ".github" / "ISSUE_TEMPLATE" / "support.yml", "")
    _write_test_file(root / "README.md", "pytest")
    _write_test_file(root / "README_zh.md", "pytest")
    _write_test_file(root / "RELEASE_GUIDE.md", "pytest")
    (root / "docs").mkdir()
    _write_test_file(root / "docs" / "RELEASE_STATUS.md", "pytest")
    _write_test_file(root / "docs" / "GOAL_COMPLETION_AUDIT.md", "pytest")
    _write_test_file(root / "docs" / "IOT_SPEC_REGISTRY.md", "pytest")
    _write_test_file(root / "docs" / "TEST_REPORT.md", "pytest")
    monkeypatch.setattr(hacs_preflight, "ROOT", root)

    errors = hacs_preflight._check_release_quality_gates()

    assert any("ruff dependency" in error for error in errors)
    assert any("mypy dependency" in error for error in errors)
    assert any("GitHub validate lint step" in error for error in errors)
    assert any("local release lint gate" in error for error in errors)
    assert any("local release compile command" in error for error in errors)
    assert any("bug report redacted diagnostics field" in error for error in errors)
    assert any("feature request protocol evidence field" in error for error in errors)
    assert any("support redacted verifier field" in error for error in errors)
    assert any("release guide semantic versioning policy" in error for error in errors)
    assert any("release guide support workflow policy" in error for error in errors)
    assert any("release status support privacy policy" in error for error in errors)
    assert any("release status version review policy" in error for error in errors)
    assert any(
        "English README WebSocket-only event-notification boundary" in error
        for error in errors
    )
    assert any(
        "English README production LAN gateway probe command" in error
        for error in errors
    )
    assert any(
        "English README production probe fail-closed boundary" in error
        for error in errors
    )
    assert any(
        "Chinese README WebSocket-only event-notification boundary" in error
        for error in errors
    )
    assert any(
        "Chinese README production LAN gateway probe command" in error
        for error in errors
    )
    assert any(
        "Chinese README production probe fail-closed boundary" in error
        for error in errors
    )
    assert any(
        "release guide production LAN gateway probe command" in error
        for error in errors
    )
    assert any(
        "release guide production probe fail-closed policy" in error
        for error in errors
    )
    assert any(
        "test report production LAN gateway probe command" in error
        for error in errors
    )
    assert any(
        "test report production probe fail-closed boundary" in error
        for error in errors
    )
    assert any(
        "test report external validation boundary" in error
        for error in errors
    )
    assert any(
        "IoT registry WebSocket-only runtime boundary" in error
        for error in errors
    )
    assert any("goal audit WebSocket-only runtime chain" in error for error in errors)
    assert any(
        "goal audit WebSocket-only event-notification status" in error
        for error in errors
    )
    assert any("goal audit production scan-login probe command" in error for error in errors)
    assert any(
        "goal audit production scan-login explicit confirm flag" in error
        for error in errors
    )
    assert any("goal audit production scan-login device env guard" in error for error in errors)
    assert any(
        "goal audit production cloud devices probe command" in error
        for error in errors
    )
    assert any(
        "goal audit production cloud devices explicit confirm flag" in error
        for error in errors
    )
    assert any(
        "goal audit production cloud devices token env guard" in error
        for error in errors
    )
    assert any(
        "goal audit production cloud devices house env guard" in error
        for error in errors
    )
    assert any(
        "goal audit production LAN gateway probe command" in error
        for error in errors
    )
    assert any(
        "goal audit production LAN gateway explicit confirm flag" in error
        for error in errors
    )
    assert any(
        "goal audit production LAN gateway host env guard" in error
        for error in errors
    )
    assert any("goal audit cleanup non-destructive boundary" in error for error in errors)


def test_release_quality_gate_reports_missing_publish_script(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """preflight 应报告缺失的发布脚本而不是崩溃."""
    root = tmp_path
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / ".github" / "ISSUE_TEMPLATE").mkdir(parents=True)
    _write_test_file(root / "requirements_test.txt", "ruff mypy")
    _write_test_file(root / ".github" / "workflows" / "validate.yaml", "")
    _write_test_file(root / ".github" / "workflows" / "release.yaml", "")
    _write_test_file(root / ".github" / "ISSUE_TEMPLATE" / "bug_report.yml", "")
    _write_test_file(root / ".github" / "ISSUE_TEMPLATE" / "feature_request.yml", "")
    _write_test_file(root / ".github" / "ISSUE_TEMPLATE" / "support.yml", "")
    _write_test_file(root / "README.md", "")
    _write_test_file(root / "README_zh.md", "")
    _write_test_file(root / "RELEASE_GUIDE.md", "")
    (root / "docs").mkdir()
    _write_test_file(root / "docs" / "RELEASE_STATUS.md", "")
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
    (root / ".github" / "ISSUE_TEMPLATE").mkdir(parents=True)
    _write_test_file(root / "requirements_test.txt", "ruff mypy")
    _write_test_file(root / "hacs_publish.py", "CHECKS = build_checks()")
    _write_test_file(root / ".github" / "workflows" / "validate.yaml", "")
    _write_test_file(root / ".github" / "workflows" / "release.yaml", "")
    _write_test_file(root / ".github" / "ISSUE_TEMPLATE" / "bug_report.yml", "")
    _write_test_file(root / ".github" / "ISSUE_TEMPLATE" / "feature_request.yml", "")
    _write_test_file(root / ".github" / "ISSUE_TEMPLATE" / "support.yml", "")
    _write_test_file(root / "README.md", "")
    _write_test_file(root / "README_zh.md", "")
    _write_test_file(root / "RELEASE_GUIDE.md", "")
    (root / "docs").mkdir()
    _write_test_file(root / "docs" / "RELEASE_STATUS.md", "")
    monkeypatch.setattr(hacs_preflight, "ROOT", root)

    errors = hacs_preflight._check_release_quality_gates()

    assert "hacs_publish.py must define literal CHECKS" in errors


def _write_test_file(path: Path, content: str) -> None:
    """Write a minimal synthetic file for preflight inspection."""
    path.write_text(content, encoding="utf-8")
