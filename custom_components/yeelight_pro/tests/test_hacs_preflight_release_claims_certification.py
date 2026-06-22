"""Certification and upstream release claim guard tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import hacs_preflight


def test_release_claim_guard_rejects_wwha_certification_claims(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """release-facing 文档不能提前声明 WWHA 已认证."""
    root = tmp_path
    docs_root = root / "docs"
    docs_root.mkdir()
    _write_test_file(root / "README.md", "Works with Home Assistant certified")
    _write_test_file(root / "README_zh.md", "已通过 WWHA 认证")
    _write_test_file(root / "CHANGELOG.md", "")
    _write_test_file(root / "RELEASE_GUIDE.md", "")
    _write_test_file(docs_root / "WORKS_WITH_HOME_ASSISTANT_HANDOVER.md", "")
    monkeypatch.setattr(hacs_preflight, "ROOT", root)

    errors = hacs_preflight._check_readme_claims()

    assert any("README.md: Works with Home Assistant certified" in error for error in errors)
    assert any("README_zh.md: 已通过 WWHA 认证" in error for error in errors)


def test_release_claim_guard_rejects_gold_and_core_overclaims(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """release-facing 文档不能提前声明 Gold 或 Core 已完成."""
    root = tmp_path
    docs_root = root / "docs"
    docs_root.mkdir()
    _write_test_file(root / "README.md", "Gold quality scale achieved")
    _write_test_file(root / "README_zh.md", "已达到 Gold 质量等级")
    _write_test_file(root / "CHANGELOG.md", "")
    _write_test_file(root / "RELEASE_GUIDE.md", "")
    _write_test_file(
        docs_root / "CORE_MIGRATION_STRATEGY.md",
        "merged into Home Assistant Core",
    )
    monkeypatch.setattr(hacs_preflight, "ROOT", root)

    errors = hacs_preflight._check_readme_claims()

    assert any("README.md: Gold quality scale achieved" in error for error in errors)
    assert any("README_zh.md: 已达到 Gold 质量等级" in error for error in errors)
    assert any("CORE_MIGRATION_STRATEGY.md" in error for error in errors)


def test_release_claim_guard_rejects_hacs_merged_claims(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """release-facing 文档不能把 HACS 审核中写成已合并."""
    root = tmp_path
    docs_root = root / "docs"
    docs_root.mkdir()
    _write_test_file(root / "README.md", "HACS default repository PR is merged")
    _write_test_file(root / "README_zh.md", "HACS 默认仓库已合并")
    _write_test_file(root / "CHANGELOG.md", "")
    _write_test_file(root / "RELEASE_GUIDE.md", "")
    _write_test_file(docs_root / "RELEASE_STATUS.md", "merged into HACS")
    monkeypatch.setattr(hacs_preflight, "ROOT", root)

    errors = hacs_preflight._check_readme_claims()

    assert any("README.md: HACS default repository PR is merged" in error for error in errors)
    assert any("README_zh.md: HACS 默认仓库已合并" in error for error in errors)
    assert any("docs/RELEASE_STATUS.md: merged into HACS" in error for error in errors)


def _write_test_file(path: Path, content: str) -> None:
    """Write a minimal synthetic test file for preflight inspection."""
    path.write_text(content, encoding="utf-8")
