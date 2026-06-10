"""Tests for root-level compatibility local HA verification entrypoints."""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

ROOT = Path(__file__).resolve().parents[3]
ENTRYPOINTS = (
    "test_actual_environment.py",
    "test_complete_ha.py",
    "test_functional.py",
    "test_real_ha_environment.py",
)


@pytest.mark.parametrize("filename", ENTRYPOINTS)
def test_legacy_local_ha_entrypoint_delegates_to_shared_verifier(
    filename: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """旧入口必须复用 canonical local HA verifier，避免分叉环境检查."""
    module = _load_entrypoint(filename)
    verifier = Mock(return_value=7)
    monkeypatch.setattr(module, "verify_local_ha_main", verifier)

    assert module.main(["--skip-docker", "--skip-url"]) == 7

    verifier.assert_called_once_with(["--skip-docker", "--skip-url"])


@pytest.mark.parametrize("filename", ENTRYPOINTS)
def test_legacy_local_ha_entrypoint_help_imports_cleanly(filename: str) -> None:
    """旧入口脚本路径执行 --help 时不应直接导入 Home Assistant runtime."""
    result = subprocess.run(
        [sys.executable, str(ROOT / filename), "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "--config-dir" in result.stdout
    assert "No module named 'homeassistant'" not in result.stderr


def _load_entrypoint(filename: str):
    """Load one root-level entrypoint by file path."""
    path = ROOT / filename
    module_name = f"_yeelight_pro_{filename.removesuffix('.py')}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module
