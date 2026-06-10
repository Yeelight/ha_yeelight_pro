"""Release claim guards for the parent Home Assistant progress document."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import hacs_preflight


def test_release_claim_guard_scans_parent_progress_doc(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """父级进度文档不能把易来事件通知写回 WebSocket/SSE 混写."""
    root = tmp_path / "services" / "homeassistant" / "extensions" / "ha_yeelight_pro"
    homeassistant_root = root.parent.parent
    docs_root = root / "docs"
    docs_root.mkdir(parents=True)
    _write_test_file(root / "README.md", "")
    _write_test_file(root / "README_zh.md", "")
    _write_test_file(root / "CHANGELOG.md", "")
    _write_test_file(root / "RELEASE_GUIDE.md", "")
    _write_test_file(docs_root / "TEST_REPORT.md", "")
    _write_test_file(
        homeassistant_root / "最新进度.md",
        "live WebSocket or SSE runtime",
    )
    monkeypatch.setattr(hacs_preflight, "ROOT", root)

    errors = hacs_preflight._check_readme_claims()

    assert any(
        "最新进度.md: /WebSocket\\s*(?:or|and|\\+)\\s*SSE/" in error
        for error in errors
    )


def _write_test_file(path: Path, content: str) -> None:
    """Write a minimal synthetic test file for preflight inspection."""
    path.write_text(content, encoding="utf-8")
