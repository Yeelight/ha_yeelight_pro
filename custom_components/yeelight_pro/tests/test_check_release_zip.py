"""Release zip structure contract tests."""
from __future__ import annotations

import zipfile
from pathlib import Path

from scripts import check_release_zip


def test_release_zip_required_files_include_runtime_contracts() -> None:
    """发布 zip 校验必须覆盖关键运行时和协议边界文件。"""
    assert {
        "custom_components/yeelight_pro/capabilities/product_catalog.py",
        "custom_components/yeelight_pro/capabilities/product_catalog_data.py",
        "custom_components/yeelight_pro/capabilities/spec_correction_normalizers.py",
        "custom_components/yeelight_pro/capabilities/documented_catalog.py",
        "custom_components/yeelight_pro/capabilities/ha_core_platforms.py",
        "custom_components/yeelight_pro/capabilities/platform_candidate_projection.py",
        "custom_components/yeelight_pro/capabilities/platform_contract_data.py",
        "custom_components/yeelight_pro/capabilities/platform_contract_evidence.py",
        "custom_components/yeelight_pro/capabilities/platform_contract_logging.py",
        "custom_components/yeelight_pro/capabilities/sensor_safety.py",
        "custom_components/yeelight_pro/capabilities/property_index.py",
        "custom_components/yeelight_pro/converter/openapi_properties.py",
        "custom_components/yeelight_pro/converter/runtime_inference_helpers.py",
        "custom_components/yeelight_pro/converter/runtime_property_builder.py",
        "custom_components/yeelight_pro/converter/runtime_template_controls.py",
        "custom_components/yeelight_pro/converter/runtime_template_hvac.py",
        "custom_components/yeelight_pro/converter/runtime_template_selector.py",
        "custom_components/yeelight_pro/converter/runtime_template_sensors.py",
        "custom_components/yeelight_pro/converter/runtime_templates.py",
        "custom_components/yeelight_pro/converter/runtime_subdevices.py",
        "custom_components/yeelight_pro/config_flow_account.py",
        "custom_components/yeelight_pro/config_flow_device_picker.py",
        "custom_components/yeelight_pro/config_flow_options.py",
        "custom_components/yeelight_pro/device_display.py",
        "custom_components/yeelight_pro/device_select.py",
        "custom_components/yeelight_pro/core/client_node_base.py",
        "custom_components/yeelight_pro/core/client_node_api.py",
        "custom_components/yeelight_pro/core/client_node_lists.py",
        "custom_components/yeelight_pro/core/client_node_properties.py",
        "custom_components/yeelight_pro/core/coordinator_controls.py",
        "custom_components/yeelight_pro/core/device_classification_categories.py",
        "custom_components/yeelight_pro/core/device_registry_classification.py",
        "custom_components/yeelight_pro/core/device_runtime_constants.py",
        "custom_components/yeelight_pro/core/device_metadata.py",
        "custom_components/yeelight_pro/core/firmware_metadata.py",
        "custom_components/yeelight_pro/core/lan_control.py",
        "custom_components/yeelight_pro/core/lan_sensor_values.py",
        "custom_components/yeelight_pro/core/lan_topology_payload.py",
        "custom_components/yeelight_pro/core/property_hydration_summary.py",
        "custom_components/yeelight_pro/core/scan_login.py",
        "custom_components/yeelight_pro/core/runtime_bridge.py",
        "custom_components/yeelight_pro/debug_service.py",
        "custom_components/yeelight_pro/diagnostics.py",
        "custom_components/yeelight_pro/entity_candidate_logging.py",
        "custom_components/yeelight_pro/entry_title.py",
        "custom_components/yeelight_pro/entity_category.py",
        "custom_components/yeelight_pro/lan_contract.py",
        "custom_components/yeelight_pro/lan_methods.py",
        "custom_components/yeelight_pro/lan_payload.py",
        "custom_components/yeelight_pro/lan_runtime.py",
        "custom_components/yeelight_pro/lan_runtime_endpoints.py",
        "custom_components/yeelight_pro/live_runtime.py",
        "custom_components/yeelight_pro/scan_login_contract.py",
        "custom_components/yeelight_pro/projector/climate_helpers.py",
        "custom_components/yeelight_pro/projector/event_identity_helpers.py",
        "custom_components/yeelight_pro/projector/event_helpers.py",
        "custom_components/yeelight_pro/projector/sensor_helpers.py",
        "custom_components/yeelight_pro/projector/sensor_metadata.py",
        "custom_components/yeelight_pro/push_contract.py",
        "custom_components/yeelight_pro/push_manager.py",
        "custom_components/yeelight_pro/push_transport.py",
    } <= check_release_zip.REQUIRED_FILES


def test_validate_existing_zip_rejects_missing_protocol_contract(tmp_path: Path) -> None:
    """已有 zip 缺少新增 runtime contract 文件时不能通过发布结构校验。"""
    zip_path = tmp_path / "yeelight_pro.zip"
    missing_file = "custom_components/yeelight_pro/scan_login_contract.py"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in check_release_zip.REQUIRED_FILES - {missing_file}:
            archive.writestr(name, "")

    names = check_release_zip._read_zip(zip_path)
    errors = check_release_zip._validate_names(names)

    assert f"missing required file: {missing_file}" in errors


def test_validate_existing_zip_rejects_unsafe_paths() -> None:
    """已有 zip 不能包含 ZipSlip、绝对路径或目录 entry。"""
    names = {
        *check_release_zip.REQUIRED_FILES,
        "custom_components/yeelight_pro/../secrets.txt",
        "/custom_components/yeelight_pro/absolute.py",
        "custom_components/yeelight_pro/tests/",
    }

    errors = check_release_zip._validate_names(names)

    assert (
        "unsafe zip path: custom_components/yeelight_pro/../secrets.txt"
    ) in errors
    assert "unsafe zip path: /custom_components/yeelight_pro/absolute.py" in errors
    assert (
        "directory entry is not allowed: custom_components/yeelight_pro/tests/"
    ) in errors


def test_validate_existing_zip_rejects_unsupported_runtime_platform_files() -> None:
    """发布 zip 不能重新带入易来协议无支撑的平台文件."""
    names = {
        *check_release_zip.REQUIRED_FILES,
        "custom_components/yeelight_pro/lock.py",
        "custom_components/yeelight_pro/scene.py",
        "custom_components/yeelight_pro/projector/vacuum.py",
    }

    errors = check_release_zip._validate_names(names)

    assert (
        "forbidden release file: custom_components/yeelight_pro/lock.py"
        in errors
    )
    assert (
        "forbidden release file: custom_components/yeelight_pro/scene.py"
        in errors
    )
    assert (
        "forbidden release file: custom_components/yeelight_pro/projector/vacuum.py"
        in errors
    )


def test_write_zip_returns_validated_runtime_names(tmp_path: Path) -> None:
    """写出发布 zip 后应返回可直接通过结构校验的 runtime 文件名集合。"""
    zip_path = tmp_path / "yeelight_pro.zip"

    names = check_release_zip._write_zip(zip_path)

    assert check_release_zip._validate_names(names) == []
    assert zip_path.exists()
