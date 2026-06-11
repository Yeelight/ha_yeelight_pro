"""Release-facing preflight guard tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import hacs_preflight
from scripts import hacs_preflight_core


def test_python_file_line_count_guard_rejects_oversized_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """release preflight 应阻断超过项目行数边界的 Python 文件."""
    root = tmp_path
    component_root = root / "custom_components" / "yeelight_pro"
    component_root.mkdir(parents=True)
    _write_test_file(component_root / "oversized.py", "\n".join(["pass"] * 401))
    monkeypatch.setattr(hacs_preflight, "ROOT", root)

    errors = hacs_preflight._check_python_file_line_counts()

    assert errors == [
        "custom_components/yeelight_pro/oversized.py exceeds 400 lines: 401"
    ]


def test_python_file_line_count_guard_includes_root_scripts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """release preflight 应覆盖根目录手工验证脚本和发布脚本."""
    root = tmp_path
    (root / "custom_components" / "yeelight_pro").mkdir(parents=True)
    (root / "scripts").mkdir()
    _write_test_file(root / "manual_oversized.py", "\n".join(["pass"] * 401))
    monkeypatch.setattr(hacs_preflight, "ROOT", root)

    errors = hacs_preflight._check_python_file_line_counts()

    assert errors == ["manual_oversized.py exceeds 400 lines: 401"]


def test_required_release_file_guard_rejects_gitignored_docs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """required release docs 不能被 .gitignore 静默忽略."""
    root = tmp_path
    docs_root = root / "docs"
    docs_root.mkdir()
    _write_test_file(root / ".gitignore", "docs/\n")
    _write_test_file(docs_root / "GOAL_COMPLETION_AUDIT.md", "")
    _write_test_file(docs_root / "IOT_SPEC_REGISTRY.md", "")
    monkeypatch.setattr(
        hacs_preflight_core,
        "REQUIRED_RELEASE_FILES",
        {
            "docs/GOAL_COMPLETION_AUDIT.md",
            "docs/IOT_SPEC_REGISTRY.md",
        },
    )
    monkeypatch.setattr(hacs_preflight, "ROOT", root)

    errors = hacs_preflight._check_exists()

    assert (
        "required release file is git-ignored: docs/GOAL_COMPLETION_AUDIT.md"
        in errors
    )
    assert "required release file is git-ignored: docs/IOT_SPEC_REGISTRY.md" in errors


def test_required_release_file_guard_allows_unignored_docs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """必备 docs 可在忽略 docs/ 的同时用精确 negation 放行."""
    root = tmp_path
    docs_root = root / "docs"
    docs_root.mkdir()
    _write_test_file(
        root / ".gitignore",
        "\n".join([
            "docs/",
            "!docs/",
            "!docs/GOAL_COMPLETION_AUDIT.md",
            "!docs/IOT_SPEC_REGISTRY.md",
        ]),
    )
    _write_test_file(docs_root / "GOAL_COMPLETION_AUDIT.md", "")
    _write_test_file(docs_root / "IOT_SPEC_REGISTRY.md", "")
    monkeypatch.setattr(
        hacs_preflight_core,
        "REQUIRED_RELEASE_FILES",
        {
            "docs/GOAL_COMPLETION_AUDIT.md",
            "docs/IOT_SPEC_REGISTRY.md",
        },
    )
    monkeypatch.setattr(hacs_preflight, "ROOT", root)

    assert hacs_preflight._check_exists() == []


@pytest.mark.parametrize("version", ["1", "v1.0.0", "1.0", "01.0.0", "1.0.0-01"])
def test_json_guard_rejects_non_semantic_manifest_version(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    version: str,
) -> None:
    """manifest version 必须可直接对齐 GitHub release tag 语义化版本."""
    root = tmp_path
    _write_minimal_json_release_files(root, manifest_version=version)
    monkeypatch.setattr(hacs_preflight, "ROOT", root)

    errors = hacs_preflight._check_json()

    assert errors == ["manifest.json version must use semantic versioning"]


@pytest.mark.parametrize("version", ["1.0.0", "1.2.3-beta.1", "1.2.3+build.5"])
def test_json_guard_accepts_semantic_manifest_version(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    version: str,
) -> None:
    """release preflight 应接受标准 MAJOR.MINOR.PATCH 及预发布/构建后缀."""
    root = tmp_path
    _write_minimal_json_release_files(root, manifest_version=version)
    monkeypatch.setattr(hacs_preflight, "ROOT", root)

    assert hacs_preflight._check_json() == []


def test_user_visible_error_redaction_guard_rejects_dynamic_error_text(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """preflight 应拒绝在 HA 用户可见错误里插入运行时值."""
    component_root = tmp_path / "custom_components" / "yeelight_pro"
    component_root.mkdir(parents=True)
    _write_test_file(
        component_root / "bad_service.py",
        "\n".join([
            "from homeassistant.exceptions import HomeAssistantError",
            "",
            "def fail(entry_id):",
            "    raise HomeAssistantError(f'entry {entry_id} failed')",
        ]),
    )
    monkeypatch.setattr(hacs_preflight, "COMPONENT_ROOT", component_root)

    errors = hacs_preflight._check_user_visible_error_redaction()

    assert errors == [
        (
            "custom_components/yeelight_pro/bad_service.py:4 uses dynamic "
            "user-visible HA error text"
        )
    ]


def test_user_visible_error_redaction_guard_allows_constant_error_text(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """preflight 应允许固定错误文本和常量引用."""
    component_root = tmp_path / "custom_components" / "yeelight_pro"
    component_root.mkdir(parents=True)
    _write_test_file(
        component_root / "safe_service.py",
        "\n".join([
            "from homeassistant.exceptions import ServiceValidationError",
            "",
            "ERROR_ENTRY_NOT_LOADED = 'Requested entry is not loaded'",
            "",
            "def fail():",
            "    raise ServiceValidationError(ERROR_ENTRY_NOT_LOADED)",
        ]),
    )
    monkeypatch.setattr(hacs_preflight, "COMPONENT_ROOT", component_root)

    assert hacs_preflight._check_user_visible_error_redaction() == []


def test_platform_guard_rejects_unsupported_runtime_platform_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """preflight 应拒绝易来协议无支撑的平台文件重新进入 runtime."""
    component_root = tmp_path / "custom_components" / "yeelight_pro"
    projector_root = component_root / "projector"
    projector_root.mkdir(parents=True)
    _write_test_file(component_root / "const.py", "PLATFORMS = ['light']\n")
    _write_test_file(component_root / "lock.py", "")
    _write_test_file(component_root / "scene.py", "")
    _write_test_file(projector_root / "vacuum.py", "")
    monkeypatch.setattr(hacs_preflight, "COMPONENT_ROOT", component_root)

    errors = hacs_preflight._check_platform_constants()

    assert (
        "unsupported runtime platform file must be removed: lock.py"
        in errors
    )
    assert (
        "unsupported runtime platform file must be removed: scene.py"
        in errors
    )
    assert (
        "unsupported projector platform file must be removed: projector/vacuum.py"
        in errors
    )


def test_forbidden_open_api_runtime_guard_rejects_house_transfer_endpoint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """preflight 应拒绝 runtime 暴露家庭转移危险接口."""
    component_root = tmp_path / "custom_components" / "yeelight_pro"
    core_root = component_root / "core"
    core_root.mkdir(parents=True)
    _write_test_file(
        core_root / "client_paths.py",
        "\n".join([
            "def house_transfer_path(house_id, target_uid):",
            "    return f'/v1/open/node/house/{house_id}/deliver/{target_uid}'",
        ]),
    )
    monkeypatch.setattr(hacs_preflight, "COMPONENT_ROOT", component_root)

    errors = hacs_preflight._check_forbidden_open_api_runtime()

    assert any("house_transfer" in error for error in errors)
    assert any("/deliver/" in error for error in errors)


def test_forbidden_open_api_runtime_guard_ignores_tests(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """危险接口扫描只针对 runtime，允许测试文件描述禁止项."""
    component_root = tmp_path / "custom_components" / "yeelight_pro"
    tests_root = component_root / "tests"
    tests_root.mkdir(parents=True)
    _write_test_file(
        tests_root / "test_house_transfer_guard.py",
        "house_transfer /deliver/ targetUid 家庭转移",
    )
    monkeypatch.setattr(hacs_preflight, "COMPONENT_ROOT", component_root)

    assert hacs_preflight._check_forbidden_open_api_runtime() == []


def _write_test_file(path: Path, content: str) -> None:
    """Write a minimal synthetic test file for preflight inspection."""
    path.write_text(content, encoding="utf-8")


def _write_minimal_json_release_files(root: Path, *, manifest_version: str) -> None:
    """Create only the JSON files needed by check_json."""
    component_root = root / "custom_components" / "yeelight_pro"
    translations_root = component_root / "translations"
    translations_root.mkdir(parents=True)
    _write_json_file(
        component_root / "manifest.json",
        {
            "domain": "yeelight_pro",
            "name": "Yeelight Pro",
            "codeowners": ["@yeelight"],
            "config_flow": True,
            "documentation": "https://github.com/yeelight/ha_yeelight_pro",
            "iot_class": "cloud_polling",
            "version": manifest_version,
        },
    )
    _write_json_file(component_root / "strings.json", {})
    _write_json_file(translations_root / "en.json", {})
    _write_json_file(translations_root / "zh-Hans.json", {})
    _write_json_file(
        root / "hacs.json",
        {
            "name": "Yeelight Pro",
            "homeassistant": "2024.1.0",
            "render_readme": True,
            "zip_release": True,
            "filename": "yeelight_pro.zip",
        },
    )


def _write_json_file(path: Path, data: object) -> None:
    """Write compact JSON for synthetic preflight fixtures."""
    path.write_text(f"{json.dumps(data)}\n", encoding="utf-8")
