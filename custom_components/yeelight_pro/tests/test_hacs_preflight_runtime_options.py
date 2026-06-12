"""Runtime options 与 device-trigger automation preflight 测试."""

from __future__ import annotations

from pathlib import Path

from scripts.hacs_preflight_runtime_options import (
    check_automation_contract_tests,
    check_runtime_options_contract_tests,
)


def test_automation_contract_requires_split_device_trigger_tests(tmp_path: Path) -> None:
    """device-trigger preflight 应保护 trigger 列表、runtime bus 和 helper 覆盖."""
    component_root = tmp_path / "custom_components" / "yeelight_pro"
    tests_root = component_root / "tests"
    tests_root.mkdir(parents=True)
    _write_test_file(component_root / "device_trigger.py", "async_get_triggers")
    _write_test_file(
        tests_root / "test_device_trigger.py",
        "async_get_triggers async_validate_trigger_config async_attach_trigger "
        "InvalidDeviceAutomationConfig knob_spin",
    )
    _write_test_file(tests_root / "test_device_trigger_runtime.py", "")
    _write_test_file(tests_root / "device_trigger_helpers.py", "")

    errors = check_automation_contract_tests(component_root)

    assert any("matches Yeelight Pro runtime event bus payload" in error for error in errors)
    assert any("device trigger event payload fixture" in error for error in errors)


def test_automation_contract_rejects_cloud_automation_runtime(
    tmp_path: Path,
) -> None:
    """没有公开接口支撑时，Yeelight 云端 automation 不得重新进入 runtime."""
    component_root = tmp_path / "custom_components" / "yeelight_pro"
    tests_root = component_root / "tests"
    (component_root / "core").mkdir(parents=True)
    tests_root.mkdir(parents=True)
    _write_test_file(component_root / "device_trigger.py", "async_get_triggers")
    _write_test_file(
        tests_root / "test_device_trigger.py",
        "async_get_triggers async_validate_trigger_config async_attach_trigger "
        "InvalidDeviceAutomationConfig knob_spin",
    )
    _write_test_file(
        tests_root / "test_device_trigger_runtime.py",
        "async_attach_trigger DEVICE_EVENT_TYPE register_switch_event_device "
        "trigger-context",
    )
    _write_test_file(
        tests_root / "device_trigger_helpers.py",
        "event_device_payload register_event_device register_switch_event_device "
        "knob spin",
    )
    _write_test_file(
        component_root / "core" / "client_node_lists.py",
        "def get_automations(): pass\nhouse_automations_path",
    )
    _write_test_file(
        component_root / "core" / "auxiliary_data.py",
        "automations: list[dict]\nclient.get_automations",
    )
    _write_test_file(
        component_root / "entity_candidates.py",
        'def _iter_automation_candidates(): pass\nsource = "automation"',
    )

    errors = check_automation_contract_tests(component_root)

    assert any("cloud automation list API is not documented" in error for error in errors)
    assert any("cloud automations must not be cached as topology" in error for error in errors)
    assert any("cloud automations must not create entities" in error for error in errors)


def test_runtime_options_contract_requires_debug_service_gate(
    tmp_path: Path,
) -> None:
    """runtime options preflight 应保护 debug service 的关闭态拒绝路径."""
    component_root = tmp_path / "custom_components" / "yeelight_pro"
    tests_root = component_root / "tests"
    tests_root.mkdir(parents=True)
    _write_test_file(
        component_root / "runtime_options.py",
        "CONF_HIDE_UNKNOWN_ENTITIES "
        "CONF_LIVE_UPDATES CONF_LOCAL_GATEWAY_CONTROL CONF_LOCAL_GATEWAY_HOST "
        "CONF_LOCAL_GATEWAY_PORT apply_options "
        "async_delete_topology_changed_issues async_reload",
    )
    _write_test_file(
        tests_root / "test_runtime_options.py",
        "without_reload entity_projection_changes runtime_missing "
        "clears_topology_repairs "
        "test_options_update_reloads_when_background_runtime_option_changes "
        "live_updates_websocket local_gateway_control local_gateway_host "
        "local_gateway_port",
    )
    _write_test_file(
        tests_root / "test_options_flow_contract.py",
        "test_options_flow_background_runtime_options_require_reload "
        "CONF_LIVE_UPDATES CONF_LOCAL_GATEWAY_CONTROL CONF_LOCAL_GATEWAY_HOST "
        "CONF_LOCAL_GATEWAY_PORT confirm_reload",
    )
    _write_complete_options_picker_test(tests_root)
    _write_test_file(
        component_root / "debug_service.py",
        "async_register_admin_service coordinator.debug_mode async_handle_runtime_event",
    )
    _write_test_file(tests_root / "test_debug_service.py", "")

    errors = check_runtime_options_contract_tests(component_root)

    assert any("disabled debug-mode service rejection coverage" in error for error in errors)
    assert any("disabled debug service does not dispatch event" in error for error in errors)


def test_runtime_options_contract_requires_background_runtime_reload_coverage(
    tmp_path: Path,
) -> None:
    """preflight 必须保护 WebSocket/LAN runtime reload 合同."""
    component_root = tmp_path / "custom_components" / "yeelight_pro"
    tests_root = component_root / "tests"
    tests_root.mkdir(parents=True)
    _write_test_file(
        component_root / "runtime_options.py",
        "CONF_HIDE_UNKNOWN_ENTITIES apply_options "
        "async_delete_topology_changed_issues async_reload",
    )
    _write_test_file(
        tests_root / "test_runtime_options.py",
        "without_reload entity_projection_changes runtime_missing "
        "clears_topology_repairs",
    )
    _write_test_file(tests_root / "test_options_flow_contract.py", "confirm_reload")
    _write_complete_options_picker_test(tests_root)
    _write_test_file(
        component_root / "debug_service.py",
        "async_register_admin_service coordinator.debug_mode async_handle_runtime_event",
    )
    _write_test_file(
        tests_root / "test_debug_service.py",
        "test_debug_emit_event_service_rejects_disabled_debug_mode "
        "assert_not_awaited debug mode is disabled",
    )

    errors = check_runtime_options_contract_tests(component_root)

    assert any("reload on WebSocket live update changes" in error for error in errors)
    assert any("local gateway host reload case" in error for error in errors)
    assert any("options flow routes background runtime changes" in error for error in errors)


def test_runtime_options_contract_requires_options_device_picker_coverage(
    tmp_path: Path,
) -> None:
    """preflight 必须保护 options 中真实设备 picker 的可调导入范围."""
    component_root = tmp_path / "custom_components" / "yeelight_pro"
    tests_root = component_root / "tests"
    tests_root.mkdir(parents=True)
    _write_test_file(
        component_root / "runtime_options.py",
        "CONF_HIDE_UNKNOWN_ENTITIES "
        "CONF_LIVE_UPDATES CONF_LOCAL_GATEWAY_CONTROL CONF_LOCAL_GATEWAY_HOST "
        "CONF_LOCAL_GATEWAY_PORT apply_options "
        "async_delete_topology_changed_issues async_reload",
    )
    _write_test_file(
        tests_root / "test_runtime_options.py",
        "without_reload entity_projection_changes runtime_missing "
        "clears_topology_repairs "
        "test_options_update_reloads_when_background_runtime_option_changes "
        "live_updates_websocket local_gateway_control local_gateway_host "
        "local_gateway_port",
    )
    _write_test_file(
        tests_root / "test_options_flow_contract.py",
        "test_options_flow_background_runtime_options_require_reload "
        "CONF_LIVE_UPDATES CONF_LOCAL_GATEWAY_CONTROL CONF_LOCAL_GATEWAY_HOST "
        "CONF_LOCAL_GATEWAY_PORT confirm_reload",
    )
    _write_test_file(
        tests_root / "test_options_flow_device_picker.py",
        "test_options_flow_real_device_picker_loads_current_cloud_devices "
        "CONF_DEVICE_IMPORT_FILTER_PICKER",
    )
    _write_test_file(
        component_root / "debug_service.py",
        "async_register_admin_service coordinator.debug_mode async_handle_runtime_event",
    )
    _write_test_file(
        tests_root / "test_debug_service.py",
        "test_debug_emit_event_service_rejects_disabled_debug_mode "
        "assert_not_awaited debug mode is disabled",
    )

    errors = check_runtime_options_contract_tests(component_root)

    assert any("options picker reload confirmation coverage" in error for error in errors)
    assert any("options picker label privacy marker" in error for error in errors)
    assert any("options picker friendly type label coverage" in error for error in errors)


def _write_test_file(path: Path, content: str) -> None:
    """写入最小 synthetic test 文件供 preflight 扫描."""
    path.write_text(content, encoding="utf-8")


def _write_complete_options_picker_test(tests_root: Path) -> None:
    """写入满足 options picker preflight 的 synthetic test 文件."""
    _write_test_file(
        tests_root / "test_options_flow_device_picker.py",
        "test_options_flow_real_device_picker_loads_current_cloud_devices "
        "test_options_flow_real_device_picker_selection_requires_reload "
        "test_options_flow_real_device_picker_load_error_is_redacted "
        "CONF_DEVICE_IMPORT_FILTER_PICKER Kitchen Secret 易来开关设备",
    )
