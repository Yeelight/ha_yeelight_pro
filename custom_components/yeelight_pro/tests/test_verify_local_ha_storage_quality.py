"""Local HA storage device/entity quality verification tests."""

from __future__ import annotations

from pathlib import Path

from scripts.verify_local_ha import DEFAULT_ENTITY_COUNTS, VerificationReport, verify_storage

from .storage_verifier_helpers import (
    config_entry as _config_entry,
    write_storage as _write_storage,
    yeelight_devices as _yeelight_devices,
    yeelight_entities as _yeelight_entities,
)


def test_verify_storage_rejects_source_devices_missing_registry_metadata(
    tmp_path: Path,
) -> None:
    """源设备缺名称、型号或区域时应阻断，避免前端设备页退化."""
    devices = _yeelight_devices()
    devices[0].pop("name", None)
    devices[0].pop("model", None)
    devices[0].pop("area_id", None)
    _write_storage(tmp_path, "core.config_entries", {"entries": [_config_entry()]})
    _write_storage(tmp_path, "core.device_registry", {"devices": devices})
    _write_storage(tmp_path, "core.entity_registry", {"entities": _yeelight_entities()})
    report = VerificationReport()

    verify_storage(
        tmp_path,
        report,
        expected_config_entries=1,
        expected_devices=2,
        expected_entities=sum(DEFAULT_ENTITY_COUNTS.values()),
        expected_entity_counts=DEFAULT_ENTITY_COUNTS,
    )

    assert not report.ok
    assert any("missing friendly names" in failure for failure in report.failures)
    assert any("missing model metadata" in failure for failure in report.failures)
    assert any("missing area metadata" in failure for failure in report.failures)


def test_verify_storage_warns_for_diagnostic_only_devices_missing_metadata(
    tmp_path: Path,
) -> None:
    """只有在线状态等诊断实体的未知设备不应阻断 private/LAN 实测验证."""
    devices = _yeelight_devices()
    devices.append({
        "id": "diagnostic-only-device",
        "identifiers": [["yeelight_pro", "private:device:40266062"]],
        "name": "华歌Mini7.2",
        "manufacturer": "Yeelight",
        "model": "",
    })
    entities = _yeelight_entities()
    entities.append({
        "platform": "yeelight_pro",
        "entity_id": "sensor.hua_ge_mini_online",
        "unique_id": "yeelight_pro_private_house_1_device_40266062_online_status",
        "original_name": "在线状态",
        "device_id": "diagnostic-only-device",
        "entity_category": "diagnostic",
    })
    _write_storage(tmp_path, "core.config_entries", {"entries": [_config_entry()]})
    _write_storage(tmp_path, "core.device_registry", {"devices": devices})
    _write_storage(tmp_path, "core.entity_registry", {"entities": entities})
    report = VerificationReport()

    verify_storage(
        tmp_path,
        report,
        expected_config_entries=1,
        expected_devices=2,
        expected_entities=sum(DEFAULT_ENTITY_COUNTS.values()),
        expected_entity_counts=DEFAULT_ENTITY_COUNTS,
    )

    assert report.ok
    assert any("diagnostic-only source devices" in warning for warning in report.warnings)
    quality = report.metrics["device_registry_quality"]
    assert isinstance(quality, dict)
    assert quality["diagnostic_only_with_gaps"] == 1


def test_verify_storage_rejects_generic_source_device_models(
    tmp_path: Path,
) -> None:
    """源设备不能继续用 light/relay_switch 这类泛化型号糊弄设备页."""
    devices = _yeelight_devices()
    devices[0]["model"] = "light"
    devices[1]["model"] = "relay_switch"
    _write_storage(tmp_path, "core.config_entries", {"entries": [_config_entry()]})
    _write_storage(tmp_path, "core.device_registry", {"devices": devices})
    _write_storage(tmp_path, "core.entity_registry", {"entities": _yeelight_entities()})
    report = VerificationReport()

    verify_storage(
        tmp_path,
        report,
        expected_config_entries=1,
        expected_devices=2,
        expected_entities=sum(DEFAULT_ENTITY_COUNTS.values()),
        expected_entity_counts=DEFAULT_ENTITY_COUNTS,
    )

    assert not report.ok
    assert any("generic model labels" in failure for failure in report.failures)


def test_verify_storage_rejects_chinese_generic_source_device_models(
    tmp_path: Path,
) -> None:
    """源设备不能继续用灯具/继电器开关这类中文泛化型号糊弄设备页."""
    devices = _yeelight_devices()
    devices[0]["model"] = "灯具"
    devices[1]["model"] = "继电器开关"
    _write_storage(tmp_path, "core.config_entries", {"entries": [_config_entry()]})
    _write_storage(tmp_path, "core.device_registry", {"devices": devices})
    _write_storage(tmp_path, "core.entity_registry", {"entities": _yeelight_entities()})
    report = VerificationReport()

    verify_storage(
        tmp_path,
        report,
        expected_config_entries=1,
        expected_devices=2,
        expected_entities=sum(DEFAULT_ENTITY_COUNTS.values()),
        expected_entity_counts=DEFAULT_ENTITY_COUNTS,
    )

    assert not report.ok
    assert any("generic model labels" in failure for failure in report.failures)


def test_verify_storage_warns_for_historical_runtime_source_device_model_ids(
    tmp_path: Path,
) -> None:
    """历史 runtime-* model_id 是 storage-only 遗留字段，应提示但不阻断."""
    devices = _yeelight_devices()
    devices[0]["model_id"] = "runtime-light"
    devices[1]["model_id"] = "runtime-relay_switch"
    _write_storage(tmp_path, "core.config_entries", {"entries": [_config_entry()]})
    _write_storage(tmp_path, "core.device_registry", {"devices": devices})
    _write_storage(tmp_path, "core.entity_registry", {"entities": _yeelight_entities()})
    report = VerificationReport()

    verify_storage(
        tmp_path,
        report,
        expected_config_entries=1,
        expected_devices=2,
        expected_entities=sum(DEFAULT_ENTITY_COUNTS.values()),
        expected_entity_counts=DEFAULT_ENTITY_COUNTS,
    )

    assert report.ok
    assert any(
        "historical runtime model_id values" in warning
        for warning in report.warnings
    )
    device_registry_quality = report.metrics["device_registry_quality"]
    assert isinstance(device_registry_quality, dict)
    assert device_registry_quality["runtime_model_id"] == 2


def test_verify_storage_rejects_house_placeholder_device_names(
    tmp_path: Path,
) -> None:
    """本地 HA 验证必须阻断 Yeelight Pro/House 加 id 的家庭壳设备名."""
    devices = _yeelight_devices()
    devices.append({
        "id": "house-device",
        "identifiers": [["yeelight_pro", "1"]],
        "name": "Yeelight Pro 1",
        "manufacturer": "Yeelight",
        "model": "Yeelight Pro 家庭",
    })
    _write_storage(tmp_path, "core.config_entries", {"entries": [_config_entry()]})
    _write_storage(tmp_path, "core.device_registry", {"devices": devices})
    _write_storage(tmp_path, "core.entity_registry", {"entities": _yeelight_entities()})
    report = VerificationReport()

    verify_storage(
        tmp_path,
        report,
        expected_config_entries=1,
        expected_devices=2,
        expected_entities=sum(DEFAULT_ENTITY_COUNTS.values()),
        expected_entity_counts=DEFAULT_ENTITY_COUNTS,
    )

    assert not report.ok
    assert any("generated house helper names" in failure for failure in report.failures)

