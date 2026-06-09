"""Dynamic entity filter release preflight contract tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import hacs_preflight


def test_dynamic_entity_filter_contract_requires_runtime_gate_tokens(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """preflight 应拒绝被削弱的动态实体过滤运行时契约."""
    component_root = tmp_path / "custom_components" / "yeelight_pro"
    tests_root = component_root / "tests"
    tests_root.mkdir(parents=True)
    _write_test_file(
        component_root / "dynamic_entities.py",
        "CONF_DEVICE_IMPORT_FILTER matches_device_import_filter",
    )
    _write_test_file(
        tests_root / "test_dynamic_entity_filters.py",
        "include_filter_blocks_unmatched_new_devices",
    )
    monkeypatch.setattr(hacs_preflight, "COMPONENT_ROOT", component_root)

    errors = hacs_preflight._check_dynamic_entity_filter_contract_tests()

    assert any("filter applies only to new registry entries" in error for error in errors)
    assert any("user-disabled registry guard" in error for error in errors)
    assert any("exclude rule runtime gate" in error for error in errors)
    assert any(
        "auxiliary entity preservation with registry context" in error
        for error in errors
    )
    assert any("existing registry restore coverage" in error for error in errors)


def _write_test_file(path: Path, content: str) -> None:
    """Write a minimal synthetic file for preflight inspection."""
    path.write_text(content, encoding="utf-8")
