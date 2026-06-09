"""Device-filter release claim guard tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import hacs_preflight


def test_release_claim_guard_rejects_destructive_device_filter_claims(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """release-facing 文档不能误称设备导入过滤会清理既有实体."""
    root = tmp_path
    docs_root = root / "docs"
    iot_root = docs_root / "iot"
    docs_root.mkdir()
    iot_root.mkdir()
    _write_test_file(
        root / "README.md",
        "device import filter deletes existing entities",
    )
    _write_test_file(root / "README_zh.md", "设备导入过滤会清理既有实体")
    _write_test_file(root / "CHANGELOG.md", "")
    _write_test_file(root / "RELEASE_GUIDE.md", "")
    _write_test_file(
        docs_root / "HA_XIAOMI_HOME_GAP_REVIEW.md",
        "device import filter cleans device registry",
    )
    _write_test_file(
        iot_root / "易来照明系统开放平台.md",
        "设备导入过滤会清理既有实体",
    )
    monkeypatch.setattr(hacs_preflight, "ROOT", root)

    errors = hacs_preflight._check_readme_claims()

    assert any(
        "README.md: device import filter deletes existing entities" in error
        for error in errors
    )
    assert any("README_zh.md: 设备导入过滤会清理既有实体" in error for error in errors)
    assert any("HA_XIAOMI_HOME_GAP_REVIEW.md" in error for error in errors)
    assert all("docs/iot" not in error for error in errors)


def _write_test_file(path: Path, content: str) -> None:
    """Write a minimal synthetic test file for preflight inspection."""
    path.write_text(content, encoding="utf-8")
