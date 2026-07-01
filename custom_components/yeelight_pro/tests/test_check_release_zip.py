"""Release zip structure contract tests."""
from __future__ import annotations

import zipfile
from pathlib import Path

from scripts import check_release_zip
from scripts.hacs_preflight_release_file_groups import RELEASE_COMPONENT_FILES


def _source_names_to_zip_names(names: set[str]) -> set[str]:
    """把源码清单路径映射为 HACS release zip 内的根路径。"""
    return {check_release_zip._source_name_to_zip_name(name) for name in names}


def test_release_zip_required_files_include_runtime_contracts() -> None:
    """发布 zip 校验必须覆盖关键运行时和协议边界文件。"""
    assert _source_names_to_zip_names(RELEASE_COMPONENT_FILES) <= (
        check_release_zip.REQUIRED_FILES
    )
    assert {
        "capabilities/product_catalog.py",
        "capabilities/product_catalog_data.py",
        "capabilities/spec_correction_normalizers.py",
        "capabilities/documented_catalog.py",
        "capabilities/ha_core_platforms.py",
        "capabilities/platform_candidate_projection.py",
        "capabilities/platform_contract_data.py",
        "capabilities/platform_contract_evidence.py",
        "capabilities/platform_contract_logging.py",
        "capabilities/sensor_safety.py",
        "capabilities/property_index.py",
        "converter/openapi_properties.py",
        "converter/runtime_inference_helpers.py",
        "converter/runtime_property_builder.py",
        "converter/runtime_template_controls.py",
        "converter/runtime_template_hvac.py",
        "converter/runtime_template_selector.py",
        "converter/runtime_template_sensors.py",
        "converter/runtime_templates.py",
        "converter/runtime_subdevices.py",
        "config_flow_account.py",
        "config_flow_device_picker.py",
        "config_flow_options.py",
        "config_flow_precheck.py",
        "device_display.py",
        "device_select.py",
        "core/client_node_base.py",
        "core/client_node_api.py",
        "core/client_node_lists.py",
        "core/client_node_properties.py",
        "core/coordinator_controls.py",
        "core/device_classification_categories.py",
        "core/device_registry_classification.py",
        "core/device_runtime_constants.py",
        "core/device_metadata.py",
        "core/firmware_metadata.py",
        "core/lan_control.py",
        "core/lan_sensor_values.py",
        "core/lan_topology_payload.py",
        "core/lan_topology_specs.py",
        "core/property_hydration_summary.py",
        "core/scan_login.py",
        "core/runtime_bridge.py",
        "debug_push_service.py",
        "debug_runtime.py",
        "debug_service.py",
        "deployment_urls.py",
        "diagnostics.py",
        "entity_candidate_logging.py",
        "entry_title.py",
        "entity_category.py",
        "lan_contract.py",
        "lan_methods.py",
        "lan_payload.py",
        "lan_runtime.py",
        "lan_runtime_endpoints.py",
        "light_control_helpers.py",
        "live_runtime.py",
        "scan_login_contract.py",
        "projector/climate_helpers.py",
        "projector/event_identity_helpers.py",
        "projector/event_input.py",
        "projector/event_helpers.py",
        "projector/property_control_common.py",
        "projector/sensor_helpers.py",
        "projector/sensor_metadata.py",
        "diagnostic_push_flow.py",
        "push_contract.py",
        "push_manager.py",
        "push_transport.py",
        "push_transport_connection.py",
        "push_transport_frames.py",
        "push_transport_reconnect.py",
        "push_transport_runtime.py",
        "push_transport_shapes.py",
        "push_transport_types.py",
    } <= check_release_zip.REQUIRED_FILES
    assert "manifest.json" in check_release_zip.REQUIRED_FILES
    assert all(
        not name.startswith("custom_components/")
        for name in check_release_zip.REQUIRED_FILES
    )


def test_validate_existing_zip_rejects_missing_protocol_contract(tmp_path: Path) -> None:
    """已有 zip 缺少新增 runtime contract 文件时不能通过发布结构校验。"""
    zip_path = tmp_path / "yeelight_pro.zip"
    missing_file = "scan_login_contract.py"
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
        "../secrets.txt",
        "/absolute.py",
        "tests/",
    }

    errors = check_release_zip._validate_names(names)

    assert "unsafe zip path: ../secrets.txt" in errors
    assert "unsafe zip path: /absolute.py" in errors
    assert "directory entry is not allowed: tests/" in errors


def test_validate_existing_zip_rejects_unsupported_runtime_platform_files() -> None:
    """发布 zip 不能重新带入易来协议无支撑的平台文件."""
    names = {
        *check_release_zip.REQUIRED_FILES,
        "lock.py",
        "scene.py",
        "projector/vacuum.py",
        "push_transport_dns.py",
    }

    errors = check_release_zip._validate_names(names)

    assert "forbidden release file: lock.py" in errors
    assert "forbidden release file: scene.py" in errors
    assert "forbidden release file: projector/vacuum.py" in errors
    assert "forbidden release file: push_transport_dns.py" in errors


def test_validate_existing_zip_rejects_nested_integration_paths() -> None:
    """HACS zip 解压到本地集成目录，zip 内不能再包含 custom_components 层。"""
    names = {
        *check_release_zip.REQUIRED_FILES,
        "custom_components/yeelight_pro/manifest.json",
    }

    errors = check_release_zip._validate_names(names)

    assert (
        "unexpected nested integration path: custom_components/yeelight_pro/manifest.json"
        in errors
    )


def test_write_zip_returns_validated_runtime_names(tmp_path: Path) -> None:
    """写出发布 zip 后应返回可直接通过结构校验的 runtime 文件名集合。"""
    zip_path = tmp_path / "yeelight_pro.zip"

    names = check_release_zip._write_zip(zip_path)

    assert check_release_zip._validate_names(names) == []
    assert zip_path.exists()
    with zipfile.ZipFile(zip_path) as archive:
        zip_names = set(archive.namelist())

    assert "manifest.json" in zip_names
    assert "config_flow.py" in zip_names
    assert "translations/en.json" in zip_names
    assert "custom_components/yeelight_pro/manifest.json" not in zip_names
