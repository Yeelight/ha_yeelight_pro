"""Release preflight contract tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import hacs_preflight
from scripts.hacs_preflight_data import REQUIRED_RELEASE_FILES

from .hacs_preflight_expected import EXPECTED_RELEASE_FILES


def test_release_files_include_iot_registry_contract_tests() -> None:
    """发布包必须保留 IoT registry 关键测试."""
    assert EXPECTED_RELEASE_FILES <= REQUIRED_RELEASE_FILES


def test_iot_registry_contract_check_requires_coverage_tokens(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """preflight 应拒绝空测试文件冒充 registry 合同覆盖."""
    component_root = tmp_path / "custom_components" / "yeelight_pro"
    core_root = component_root / "core"
    tests_root = component_root / "tests"
    tests_root.mkdir(parents=True)
    core_root.mkdir()
    monkeypatch.setattr(hacs_preflight, "COMPONENT_ROOT", component_root)

    _write_test_file(
        tests_root / "test_iot_registry.py",
        "platform_for_category component_platform_hint property_capability",
    )
    _write_test_file(tests_root / "test_iot_registry_events.py", "normalize_event_type")
    _write_test_file(
        tests_root / "test_iot_registry_protocols.py",
        "connection_protocol",
    )
    _write_test_file(tests_root / "test_iot_registry_keys.py", "")
    _write_test_file(
        tests_root / "test_iot_registry_integrity.py",
        (
            "validate_iot_registry duplicate category "
            "HA platform must not be an IoT category maps to both"
        ),
    )
    _write_test_file(tests_root / "test_spec_correction.py", "")
    _write_test_file(tests_root / "test_product_schema_converter.py", "")
    _write_test_file(tests_root / "test_product_schema_metadata.py", "")
    _write_test_file(tests_root / "test_device_instance_converter.py", "")
    _write_test_file(tests_root / "test_projection_scaled_state.py", "")
    _write_test_file(tests_root / "test_event_projection.py", "")
    _write_test_file(tests_root / "test_capability_filter.py", "")
    _write_test_file(tests_root / "test_projection_boundaries.py", "")
    _write_test_file(tests_root / "test_projection_event_topology.py", "")
    _write_test_file(tests_root / "test_projection_matrix.py", "")
    _write_test_file(tests_root / "test_projection_state_sensors.py", "")
    _write_test_file(tests_root / "test_entity_candidates.py", "")
    _write_test_file(tests_root / "test_group_number_controls.py", "")
    _write_test_file(tests_root / "test_select_dynamic_options.py", "")

    errors = hacs_preflight._check_iot_registry_contract_tests()

    assert (
        "tests/test_spec_correction.py missing product schema property correction: "
        "correct_property_schema"
    ) in errors
    assert any("operator shape normalization" in error for error in errors)
    assert any("documented numeric access coverage" in error for error in errors)
    assert any("runtime filtering contract" in error for error in errors)
    assert any("canonical product schema conversion coverage" in error for error in errors)
    assert any("converter applies spec correction coverage" in error for error in errors)
    assert any("component source dedupe coverage" in error for error in errors)
    assert any("valueRange numeric normalization coverage" in error for error in errors)
    assert any("valueList enum normalization coverage" in error for error in errors)
    assert any("unit/zoom/scale metadata normalization coverage" in error for error in errors)
    assert any(
        "canonical action param zoom/scale preservation coverage" in error
        for error in errors
    )
    assert any("runtime read-side zoom/scale conversion coverage" in error for error in errors)
    assert any("HA projection uses scaled runtime state coverage" in error for error in errors)
    assert any("approach event component-scope coverage" in error for error in errors)
    assert any("panel event component-scope coverage" in error for error in errors)
    assert any("unassigned release-after-hold event boundary" in error for error in errors)
    assert any("DALI knob event conservative boundary" in error for error in errors)
    assert any("Open API node type coverage" in error for error in errors)
    assert any("documented Open API node type boundary" in error for error in errors)
    assert any("component property key formatting" in error for error in errors)
    assert any("component property key parsing" in error for error in errors)
    assert any("component property key validation coverage" in error for error in errors)
    assert any(
        "schema-declared sensor event projection coverage" in error
        for error in errors
    )
    assert any("human approach event projection coverage" in error for error in errors)
    assert any("power alarm schema event projection coverage" in error for error in errors)
    for reason in (
        "unknown bool/control fallback rejection coverage",
        "unknown writable platform fallback rejection coverage",
        "event-input unknown fallback rejection coverage",
        "low-frequency component fallback rejection coverage",
        "low-frequency diagnostics aggregate-only coverage",
        "unknown bool projection boundary coverage",
        "unknown enum/structured projection boundary coverage",
        "event-input sensor fallback boundary coverage",
        "low-frequency component projection boundary coverage",
        "bridge protocol metadata projection boundary coverage",
            "unsupported vacuum projection boundary coverage",
        "core IoT category exclusion coverage",
        "light component-state merge coverage",
        "gateway via_device projection coverage",
        "scene panel event-only projection coverage",
        "gateway topology-only projection coverage",
        "raw params and component state merge coverage",
        "unknown action button fallback rejection coverage",
        "group brightness control uses Yeelight l property",
        "group number command path assertion",
        "group brightness command payload",
        "group color temperature control uses Yeelight ct property",
        "group color temperature command payload",
        "room select dynamic options coverage",
        "group select dynamic options coverage",
        "scene select dynamic options coverage",
        "empty select option fallback coverage",
        "unknown scene select does not execute",
    ):
        assert any(reason in error for error in errors)


def test_iot_registry_integrity_check_does_not_import_ha_runtime() -> None:
    """preflight registry 检查不应依赖已安装 Home Assistant 包."""
    assert hacs_preflight._check_iot_registry_integrity() == []


def test_split_contract_check_requires_coverage_tokens(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """preflight 应拒绝空文件冒充拆分后的合同测试."""
    component_root = tmp_path / "custom_components" / "yeelight_pro"
    tests_root = component_root / "tests"
    tests_root.mkdir(parents=True)
    monkeypatch.setattr(hacs_preflight, "COMPONENT_ROOT", component_root)

    _write_test_file(tests_root / "test_capability_registry_contract.py", "")
    _write_test_file(tests_root / "conftest.py", "")
    _write_test_file(tests_root / "config_flow_helpers.py", "")
    _write_test_file(tests_root / "test_config_flow.py", "")
    _write_test_file(tests_root / "test_config_flow_cloud.py", "")
    _write_test_file(tests_root / "test_config_flow_cloud_devices.py", "")
    _write_test_file(tests_root / "test_config_flow_device_picker.py", "")
    _write_test_file(tests_root / "test_config_flow_entry_creation.py", "")
    _write_test_file(tests_root / "test_config_flow_scan_login.py", "")
    _write_test_file(tests_root / "test_config_flow_reauth.py", "")
    _write_test_file(tests_root / "test_config_flow_reauth_identity.py", "")
    _write_test_file(tests_root / "p0_client_helpers.py", "")
    _write_test_file(tests_root / "test_client_helpers.py", "")
    _write_test_file(tests_root / "test_client_control_contracts.py", "")
    _write_test_file(tests_root / "test_client_pagination.py", "")
    _write_test_file(tests_root / "test_p0_client_contracts.py", "")
    _write_test_file(tests_root / "test_p0_control_auth.py", "")
    _write_test_file(tests_root / "test_push_payloads.py", "")
    _write_test_file(tests_root / "config_entry_lifecycle_helpers.py", "")
    _write_test_file(tests_root / "test_config_entry_unload.py", "")
    _write_test_file(tests_root / "test_options_flow_contract.py", "")
    _write_test_file(tests_root / "test_translation_runtime_contract.py", "")
    _write_test_file(component_root / "config_flow_device_picker.py", "")
    _write_test_file(component_root / "config_flow_account.py", "")

    errors = hacs_preflight._check_split_contract_tests()

    assert any("backend event alias contract coverage" in error for error in errors)
    assert any("shared config-flow fixture coverage" in error for error in errors)
    assert any("fixture plugin registration" in error for error in errors)
    assert any("config-flow auth method label coverage" in error for error in errors)
    assert any("config-flow connection mode selector coverage" in error for error in errors)
    assert any(
        "cloud auth method selector translation-key coverage" in error
        for error in errors
    )
    assert any(
        "connection mode selector translation-key coverage" in error
        for error in errors
    )
    assert any("manual token auth path coverage" in error for error in errors)
    assert any("real device picker options privacy coverage" in error for error in errors)
    assert any("device picker unknown id rejection coverage" in error for error in errors)
    assert any(
        "manual token multi-account redacted unique-id coverage" in error
        for error in errors
    )
    assert any(
        "manual token multi-account separation coverage" in error
        for error in errors
    )
    assert any(
        "blank account id token-fingerprint fallback coverage" in error
        for error in errors
    )
    assert any(
        "blank stored user id reauth rejection coverage" in error
        for error in errors
    )
    assert any("scan-login LOGIN token flow coverage" in error for error in errors)
    assert any("reauth entry normalization coverage" in error for error in errors)
    assert any("shared scan-login client fake coverage" in error for error in errors)
    assert any("documented roomId query path coverage" in error for error in errors)
    assert any("pagination-before-query path coverage" in error for error in errors)
    assert any("documented read properties body coverage" in error for error in errors)
    assert any("documented multi-node single-property body coverage" in error for error in errors)
    assert any("documented multi-node multi-property body coverage" in error for error in errors)
    assert any("documented read properties path coverage" in error for error in errors)
    assert any("documented single-property read path coverage" in error for error in errors)
    assert any("documented multi-node single-property path coverage" in error for error in errors)
    assert any("documented multi-node multi-property path coverage" in error for error in errors)
    assert any("documented single-property control body coverage" in error for error in errors)
    assert any(
        "documented multi-node single-property control body coverage" in error
        for error in errors
    )
    assert any("documented single-property control path coverage" in error for error in errors)
    assert any("documented property control client coverage" in error for error in errors)
    assert any("documented house list pagination coverage" in error for error in errors)
    assert any("documented house list endpoint coverage" in error for error in errors)
    assert any("documented 3.1 list endpoint coverage" in error for error in errors)
    assert any("documented area list endpoint coverage" in error for error in errors)
    assert any("documented room list endpoint coverage" in error for error in errors)
    assert any("documented scene list endpoint coverage" in error for error in errors)
    assert any("room-scoped list pagination coverage" in error for error in errors)
    assert any(
        "documented house snapshot client request coverage" in error
        for error in errors
    )
    assert any("documented house snapshot endpoint coverage" in error for error in errors)
    assert any("client public method split stability coverage" in error for error in errors)
    assert any("client snapshot method remains on public client" in error for error in errors)
    assert any("client scene execution entrypoint coverage" in error for error in errors)
    assert any("documented scene execution endpoint coverage" in error for error in errors)
    assert any("client single-property control entrypoint coverage" in error for error in errors)
    assert any("client multi-node control entrypoint coverage" in error for error in errors)
    assert any("documented read properties client coverage" in error for error in errors)
    assert any("documented read property variants client coverage" in error for error in errors)
    assert any("read properties body field coverage" in error for error in errors)
    assert any("multi-node read body field coverage" in error for error in errors)
    assert any("client auth error classification coverage" in error for error in errors)
    assert any("command wrapper traceback redaction coverage" in error for error in errors)
    assert any("push property payload normalization coverage" in error for error in errors)
    assert any("setup coordinator fixture coverage" in error for error in errors)
    assert any("failed unload runtime preservation coverage" in error for error in errors)
    assert any("manual device filter reload coverage" in error for error in errors)
    assert any("unsupported platform removal coverage" in error for error in errors)
    assert any("Repairs placeholder runtime coverage" in error for error in errors)


def test_lifecycle_contract_check_requires_coverage_tokens(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """preflight 应拒绝空文件冒充 HA registry 生命周期覆盖."""
    component_root = tmp_path / "custom_components" / "yeelight_pro"
    tests_root = component_root / "tests"
    tests_root.mkdir(parents=True)
    monkeypatch.setattr(hacs_preflight, "COMPONENT_ROOT", component_root)

    _write_test_file(component_root / "__init__.py", "async_remove_config_entry_device")
    _write_test_file(component_root / "ha_device_registry.py", "")
    _write_test_file(component_root / "entity_lifecycle.py", "")
    _write_test_file(component_root / "entity_lifecycle_entity_id.py", "")
    _write_test_file(component_root / "entity_candidates.py", "")
    _write_test_file(component_root / "entity_lifecycle_cleanup.py", "")
    _write_test_file(component_root / "registry_cleanup_service.py", "")
    _write_test_file(component_root / "repair_issues.py", "")
    _write_test_file(tests_root / "test_device_removal.py", "")
    _write_test_file(tests_root / "entity_lifecycle_helpers.py", "")
    _write_test_file(tests_root / "test_entity_lifecycle.py", "")
    _write_test_file(tests_root / "test_entity_lifecycle_reconcile.py", "")
    _write_test_file(tests_root / "test_entity_lifecycle_reconcile_display.py", "")
    _write_test_file(tests_root / "test_entity_lifecycle_reconcile_entity_id.py", "")
    _write_test_file(tests_root / "test_registry_cleanup_service.py", "")
    _write_test_file(tests_root / "test_registry_cleanup_service_privacy.py", "")
    _write_test_file(tests_root / "test_repair_issue_cleanup.py", "")
    _write_test_file(tests_root / "test_repair_issues.py", "")
    _write_test_file(tests_root / "test_config_entry_lifecycle.py", "")

    errors = hacs_preflight._check_lifecycle_contract_tests()

    assert any("active device identifier guard" in error for error in errors)
    assert any("candidate-level device import filter match" in error for error in errors)
    assert any(
        "live WebSocket initial failure polling fallback coverage" in error
        for error in errors
    )
    assert any("config-entry runtime stop helper" in error for error in errors)
    assert any("optional push manager unload cleanup" in error for error in errors)
    assert any("confirmed cleanup disable helper" in error for error in errors)
    assert any("topology diff sanitizer" in error for error in errors)
    assert any(
        "active source device removal rejection coverage" in error
        for error in errors
    )
    assert any("automatic stale entity non-deletion coverage" in error for error in errors)
    assert any(
        "filtered device stale-without-removal coverage" in error
        for error in errors
    )
    assert any("removed scene platform stale coverage" in error for error in errors)
    assert any("legacy entity-id migration coverage" in error for error in errors)
    assert any("shared lifecycle registry fake" in error for error in errors)
    assert any(
        "cleanup service filtered-device confirm coverage" in error
        for error in errors
    )
    assert any(
        "cleanup service response/log identifier redaction coverage" in error
        for error in errors
    )
    assert any("diagnostics summary type guard coverage" in error for error in errors)
    assert any("stale Repairs issue cleanup coverage" in error for error in errors)
    assert any("Repairs diff sanitizer coverage" in error for error in errors)
    assert any("entry-scoped Repairs cleanup coverage" in error for error in errors)


def _write_test_file(path: Path, content: str) -> None:
    """Write a minimal synthetic test file for preflight inspection."""
    path.write_text(content, encoding="utf-8")
