"""Release-facing documentation claim guard tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import hacs_preflight


def test_gap_review_is_scanned_for_stale_release_claims(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ha_xiaomi_home gap review 必须纳入 release-facing claim guard."""
    root = tmp_path
    docs_root = root / "docs"
    docs_root.mkdir()
    _write_test_file(root / "README.md", "")
    _write_test_file(root / "README_zh.md", "")
    _write_test_file(root / "CHANGELOG.md", "")
    _write_test_file(root / "RELEASE_GUIDE.md", "")
    _write_test_file(
        docs_root / "HA_XIAOMI_HOME_GAP_REVIEW.md",
        "live WebSocket is implemented",
    )
    _write_test_file(docs_root / "IOT_SPEC_REGISTRY.md", "")
    monkeypatch.setattr(hacs_preflight, "ROOT", root)

    errors = hacs_preflight._check_readme_claims()

    assert (
        "stale release claim in docs/HA_XIAOMI_HOME_GAP_REVIEW.md: "
        "live WebSocket is implemented"
    ) in errors


def test_all_top_level_docs_are_scanned_for_stale_release_claims(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """所有 release-facing docs/*.md 都必须纳入声明漂移扫描."""
    root = tmp_path
    docs_root = root / "docs"
    iot_root = docs_root / "iot"
    docs_root.mkdir()
    iot_root.mkdir()
    _write_test_file(root / "README.md", "")
    _write_test_file(root / "README_zh.md", "")
    _write_test_file(root / "CHANGELOG.md", "")
    _write_test_file(root / "RELEASE_GUIDE.md", "")
    _write_test_file(docs_root / "PROJECT_SUMMARY.md", "OAuth 已实现")
    _write_test_file(iot_root / "易来照明系统开放平台.md", "OAuth 已实现")
    monkeypatch.setattr(hacs_preflight, "ROOT", root)

    errors = hacs_preflight._check_readme_claims()

    assert (
        "stale release claim in docs/PROJECT_SUMMARY.md: OAuth 已实现"
    ) in errors
    assert all("docs/iot" not in error for error in errors)


def test_release_claim_guard_rejects_new_fixed_test_and_zip_counts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """release-facing 文档不能固定宣传新的测试数量、文件数或覆盖率."""
    root = tmp_path
    docs_root = root / "docs"
    docs_root.mkdir()
    _write_test_file(root / "README.md", "686 passed\n102 files\n80%")
    _write_test_file(root / "README_zh.md", "通过 686 个测试")
    _write_test_file(root / "CHANGELOG.md", "")
    _write_test_file(root / "RELEASE_GUIDE.md", "")
    _write_test_file(docs_root / "TEST_REPORT.md", "")
    monkeypatch.setattr(hacs_preflight, "ROOT", root)

    errors = hacs_preflight._check_readme_claims()

    assert any("README.md: /\\d+\\s+passed/" in error for error in errors)
    assert any("README.md: /\\d+\\s+files/" in error for error in errors)
    assert any("README.md: /\\d+\\s*%/" in error for error in errors)
    assert any(
        "README_zh.md: /(?:通过|共)\\s*\\d+\\s*个测试/" in error
        for error in errors
    )


def test_release_claim_guard_rejects_direct_component_copy_commands(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """release-facing 文档不能回退到复制整个组件目录的安装方式."""
    root = tmp_path
    docs_root = root / "docs"
    docs_root.mkdir()
    _write_test_file(root / "README.md", "cp -R custom_components/yeelight_pro")
    _write_test_file(root / "README_zh.md", "cp -r custom_components/yeelight_pro")
    _write_test_file(root / "CHANGELOG.md", "")
    _write_test_file(root / "RELEASE_GUIDE.md", "")
    _write_test_file(docs_root / "TEST_REPORT.md", "")
    monkeypatch.setattr(hacs_preflight, "ROOT", root)

    errors = hacs_preflight._check_readme_claims()

    assert any("README.md" in error for error in errors)
    assert any("README_zh.md" in error for error in errors)


def test_release_claim_guard_rejects_house_transfer_claims(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """release-facing 文档不能把家庭转移危险接口声明为已支持."""
    root = tmp_path
    docs_root = root / "docs"
    iot_root = docs_root / "iot"
    docs_root.mkdir()
    iot_root.mkdir()
    _write_test_file(root / "README.md", "house transfer is implemented")
    _write_test_file(root / "README_zh.md", "家庭转移已支持")
    _write_test_file(root / "CHANGELOG.md", "")
    _write_test_file(root / "RELEASE_GUIDE.md", "")
    _write_test_file(docs_root / "RELEASE_STATUS.md", "")
    _write_test_file(iot_root / "易来照明系统开放平台.md", "家庭转移已支持")
    monkeypatch.setattr(hacs_preflight, "ROOT", root)

    errors = hacs_preflight._check_readme_claims()

    assert any("README.md: house transfer is implemented" in error for error in errors)
    assert any("README_zh.md: 家庭转移已支持" in error for error in errors)
    assert all("docs/iot" not in error for error in errors)


def test_release_claim_guard_rejects_overstated_analytics_claims(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """release-facing 文档不能把 opt-in analytics 夸大成默认或完整能力."""
    root = tmp_path
    docs_root = root / "docs"
    iot_root = docs_root / "iot"
    docs_root.mkdir()
    iot_root.mkdir()
    _write_test_file(root / "README.md", "all analytics APIs are implemented")
    _write_test_file(root / "README_zh.md", "数据分析默认启用")
    _write_test_file(root / "CHANGELOG.md", "")
    _write_test_file(root / "RELEASE_GUIDE.md", "")
    _write_test_file(
        docs_root / "IOT_SPEC_REGISTRY.md",
        "opt-in analytics runtime is implemented",
    )
    _write_test_file(iot_root / "易来照明系统开放平台.md", "数据分析服务已实现")
    monkeypatch.setattr(hacs_preflight, "ROOT", root)

    errors = hacs_preflight._check_readme_claims()

    assert any("README.md: all analytics APIs are implemented" in error for error in errors)
    assert any("README_zh.md: 数据分析默认启用" in error for error in errors)
    assert all("docs/IOT_SPEC_REGISTRY.md" not in error for error in errors)
    assert all("docs/iot" not in error for error in errors)


def _write_test_file(path: Path, content: str) -> None:
    """Write a minimal synthetic test file for preflight inspection."""
    path.write_text(content, encoding="utf-8")
