"""Runtime options 与 automation preflight 测试."""

from __future__ import annotations

from pathlib import Path

from scripts.hacs_preflight_runtime_options import (
    check_automation_contract_tests,
    check_runtime_options_contract_tests,
)


def test_automation_contract_requires_split_device_trigger_tests(tmp_path: Path) -> None:
    """automation preflight 应同时保护 trigger 列表、runtime bus 和 helper 覆盖."""
    component_root = tmp_path / "custom_components" / "yeelight_pro"
    tests_root = component_root / "tests"
    tests_root.mkdir(parents=True)
    _write_test_file(component_root / "device_trigger.py", "async_get_triggers")
    _write_test_file(
        tests_root / "test_device_trigger.py",
        "async_get_triggers async_validate_trigger_config async_attach_trigger "
        "InvalidDeviceAutomationConfig multi_spin absolut_spin",
    )
    _write_test_file(tests_root / "test_device_trigger_runtime.py", "")
    _write_test_file(tests_root / "device_trigger_helpers.py", "")

    errors = check_automation_contract_tests(component_root)

    assert any("matches Yeelight Pro runtime event bus payload" in error for error in errors)
    assert any("device trigger event payload fixture" in error for error in errors)


def test_runtime_options_contract_requires_debug_service_gate(
    tmp_path: Path,
) -> None:
    """runtime options preflight 应保护 debug service 的关闭态拒绝路径."""
    component_root = tmp_path / "custom_components" / "yeelight_pro"
    tests_root = component_root / "tests"
    tests_root.mkdir(parents=True)
    _write_test_file(
        component_root / "runtime_options.py",
        "CONF_EXPERIMENTAL_PLATFORMS CONF_HIDE_UNKNOWN_ENTITIES apply_options "
        "async_delete_topology_changed_issues async_reload",
    )
    _write_test_file(
        tests_root / "test_runtime_options.py",
        "without_reload entity_projection_changes runtime_missing "
        "clears_topology_repairs",
    )
    _write_test_file(
        component_root / "debug_service.py",
        "async_register_admin_service coordinator.debug_mode async_handle_runtime_event",
    )
    _write_test_file(tests_root / "test_debug_service.py", "")

    errors = check_runtime_options_contract_tests(component_root)

    assert any("disabled debug-mode service rejection coverage" in error for error in errors)
    assert any("disabled debug service does not dispatch event" in error for error in errors)


def _write_test_file(path: Path, content: str) -> None:
    """写入最小 synthetic test 文件供 preflight 扫描."""
    path.write_text(content, encoding="utf-8")
