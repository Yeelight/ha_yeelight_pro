"""Local HA runtime sync script tests."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

from scripts import sync_local_ha_runtime


def test_iter_runtime_files_excludes_tests_and_generated_artifacts(
    tmp_path: Path,
) -> None:
    """本地 HA 同步脚本不能把测试或生成产物复制进安装态."""
    source = tmp_path / "yeelight_pro"
    (source / "tests").mkdir(parents=True)
    (source / "__pycache__").mkdir()
    (source / "__init__.py").write_text("", encoding="utf-8")
    (source / "ha_device_registry.py").write_text("", encoding="utf-8")
    (source / "push_transport_dns.py").write_text("", encoding="utf-8")
    (source / "text.py").write_text("", encoding="utf-8")
    (source / "tests" / "test_runtime.py").write_text("", encoding="utf-8")
    (source / "__pycache__" / "__init__.pyc").write_bytes(b"cache")

    paths = {
        path.relative_to(source).as_posix()
        for path in sync_local_ha_runtime._iter_runtime_files(source)
    }

    assert paths == {"__init__.py", "ha_device_registry.py"}


def test_sync_script_is_directly_executable() -> None:
    """同步脚本必须支持 python3 scripts/sync_local_ha_runtime.py 直接执行."""
    result = subprocess.run(
        [sys.executable, "scripts/sync_local_ha_runtime.py", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "--config-dir" in result.stdout


def test_sync_runtime_files_removes_stale_runtime_files(tmp_path: Path) -> None:
    """源码已删除的运行时文件不能继续残留在本地 HA 安装态."""
    source = tmp_path / "source" / "custom_components" / "yeelight_pro"
    config_dir = tmp_path / "config"
    install_root = config_dir / "custom_components" / "yeelight_pro"
    source.mkdir(parents=True)
    install_root.mkdir(parents=True)
    (source / "__init__.py").write_text("current", encoding="utf-8")
    (install_root / "__init__.py").write_text("old", encoding="utf-8")
    (install_root / "stale_runtime.py").write_text("old", encoding="utf-8")
    (install_root / "__pycache__").mkdir()
    (install_root / "__pycache__" / "stale_runtime.pyc").write_bytes(b"cache")

    original_source_root = sync_local_ha_runtime.SOURCE_COMPONENT_ROOT
    sync_local_ha_runtime.SOURCE_COMPONENT_ROOT = source
    try:
        count, synced_root = sync_local_ha_runtime.sync_runtime_files(config_dir)
    finally:
        sync_local_ha_runtime.SOURCE_COMPONENT_ROOT = original_source_root

    assert count == 1
    assert synced_root == install_root
    assert (install_root / "__init__.py").read_text(encoding="utf-8") == "current"
    assert not (install_root / "stale_runtime.py").exists()
    assert not (install_root / "__pycache__").exists()


def test_planned_runtime_sync_reports_changes_without_mutation(tmp_path: Path) -> None:
    """dry-run 计划只能报告差异，不能改动本地 HA 安装态."""
    source = tmp_path / "source" / "custom_components" / "yeelight_pro"
    config_dir = tmp_path / "config"
    install_root = config_dir / "custom_components" / "yeelight_pro"
    source.mkdir(parents=True)
    install_root.mkdir(parents=True)
    (source / "__init__.py").write_text("current", encoding="utf-8")
    (source / "new_runtime.py").write_text("new", encoding="utf-8")
    (install_root / "__init__.py").write_text("old", encoding="utf-8")
    (install_root / "stale_runtime.py").write_text("old", encoding="utf-8")
    (install_root / "__pycache__").mkdir()
    (install_root / "__pycache__" / "stale_runtime.pyc").write_bytes(b"cache")

    original_source_root = sync_local_ha_runtime.SOURCE_COMPONENT_ROOT
    sync_local_ha_runtime.SOURCE_COMPONENT_ROOT = source
    try:
        plan = sync_local_ha_runtime.planned_runtime_sync(config_dir)
    finally:
        sync_local_ha_runtime.SOURCE_COMPONENT_ROOT = original_source_root

    assert plan["source_file_count"] == 2
    assert plan["changed_or_missing_files"] == ["__init__.py", "new_runtime.py"]
    assert plan["stale_files"] == ["stale_runtime.py"]
    assert plan["cache_artifact_count"] == 1
    assert (install_root / "__init__.py").read_text(encoding="utf-8") == "old"
    assert (install_root / "stale_runtime.py").exists()
    assert (install_root / "__pycache__" / "stale_runtime.pyc").exists()


def test_sync_script_dry_run_is_directly_executable(tmp_path: Path) -> None:
    """dry-run CLI 应输出同步计划并保持安装态不变."""
    config_dir = tmp_path / "config"
    install_root = config_dir / "custom_components" / "yeelight_pro"
    install_root.mkdir(parents=True)
    (install_root / "stale_runtime.py").write_text("old", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/sync_local_ha_runtime.py",
            "--config-dir",
            str(config_dir),
            "--dry-run",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Changed or missing files:" in result.stdout
    assert "Stale files:" in result.stdout
    assert (install_root / "stale_runtime.py").exists()


def test_sync_script_fails_when_install_target_still_contains_tests(
    tmp_path: Path,
) -> None:
    """同步脚本发现安装态残留 tests 时必须失败而不是静默通过."""
    config_dir = tmp_path / "config"
    install_root = config_dir / "custom_components" / "yeelight_pro"
    tests_root = install_root / "tests"
    tests_root.mkdir(parents=True)
    (tests_root / "test_runtime.py").write_text("", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/sync_local_ha_runtime.py",
            "--config-dir",
            str(config_dir),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "forbidden local HA install files remain" in result.stderr
