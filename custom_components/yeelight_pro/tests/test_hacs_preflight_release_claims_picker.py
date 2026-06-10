"""Release-facing device picker claim guard tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import hacs_preflight


def test_release_claim_guard_rejects_setup_only_device_picker_claims(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """release-facing 文档不能回退为真实设备 picker 只在配置期可用."""
    root = tmp_path
    docs_root = root / "docs"
    iot_root = docs_root / "iot"
    docs_root.mkdir()
    iot_root.mkdir()
    _write_test_file(root / "README.md", "device picker is setup-only")
    _write_test_file(root / "README_zh.md", "设备 picker 仅配置期可用")
    _write_test_file(root / "CHANGELOG.md", "")
    _write_test_file(root / "RELEASE_GUIDE.md", "")
    _write_test_file(
        docs_root / "PROJECT_SUMMARY.md",
        "options cannot reopen the device picker",
    )
    _write_test_file(
        iot_root / "易来照明系统开放平台.md",
        "device picker only works during setup",
    )
    monkeypatch.setattr(hacs_preflight, "ROOT", root)

    errors = hacs_preflight._check_readme_claims()

    assert any("README.md: device picker is setup-only" in error for error in errors)
    assert any("README_zh.md: 设备 picker 仅配置期可用" in error for error in errors)
    assert any(
        "docs/PROJECT_SUMMARY.md: options cannot reopen the device picker" in error
        for error in errors
    )
    assert all("docs/iot" not in error for error in errors)


def _write_test_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
