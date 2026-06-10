"""Analytics release claim guard tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import hacs_preflight


def test_release_claim_guard_rejects_disabled_analytics_runtime_claim(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """release-facing 文档不能回退为 analytics runtime/service 仍完全禁用."""
    root = tmp_path
    docs_root = root / "docs"
    iot_root = docs_root / "iot"
    docs_root.mkdir()
    iot_root.mkdir()
    _write_test_file(root / "README.md", "")
    _write_test_file(root / "README_zh.md", "")
    _write_test_file(root / "CHANGELOG.md", "")
    _write_test_file(root / "RELEASE_GUIDE.md", "")
    _write_test_file(
        docs_root / "HA_XIAOMI_HOME_GAP_REVIEW.md",
        "Runtime analytics entities/services stay disabled.",
    )
    _write_test_file(
        iot_root / "易来照明系统开放平台.md",
        "Runtime analytics entities/services stay disabled.",
    )
    monkeypatch.setattr(hacs_preflight, "ROOT", root)

    errors = hacs_preflight._check_readme_claims()

    assert any(
        "HA_XIAOMI_HOME_GAP_REVIEW.md: Runtime analytics entities/services stay disabled"
        in error
        for error in errors
    )
    assert all("docs/iot" not in error for error in errors)


def _write_test_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
