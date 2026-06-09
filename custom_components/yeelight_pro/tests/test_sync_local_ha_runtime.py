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
