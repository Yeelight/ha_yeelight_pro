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


def test_verify_storage_rejects_house_selects_without_name_or_translation_key(
    tmp_path: Path,
) -> None:
    """固定 select 同时缺少友好名称和翻译键时必须阻断."""
    entities = _yeelight_entities()
    entities.extend([
        {
            "platform": "yeelight_pro",
            "entity_id": "select.yeelight_pro_1",
            "unique_id": "yeelight_pro_1_select_room",
            "original_name": None,
            "device_id": None,
        },
        {
            "platform": "yeelight_pro",
            "entity_id": "select.yeelight_pro_2",
            "unique_id": "yeelight_pro_1_select_group",
            "original_name": "当前灯组",
            "device_id": None,
        },
        {
            "platform": "yeelight_pro",
            "entity_id": "select.yeelight_pro_3",
            "unique_id": "yeelight_pro_1_select_scene",
            "original_name": "当前场景",
            "device_id": None,
        },
    ])
    _write_storage(tmp_path, "core.config_entries", {"entries": [_config_entry()]})
    _write_storage(tmp_path, "core.device_registry", {"devices": _yeelight_devices()})
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

    assert not report.ok
    assert any("unfriendly names" in failure for failure in report.failures)


def test_verify_storage_rejects_missing_entity_categories(
    tmp_path: Path,
) -> None:
    """设备页没有 config/diagnostic 分组时必须阻断."""
    entities = _yeelight_entities()
    for entity in entities:
        entity.pop("entity_category", None)
    _write_storage(tmp_path, "core.config_entries", {"entries": [_config_entry()]})
    _write_storage(tmp_path, "core.device_registry", {"devices": _yeelight_devices()})
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

    assert not report.ok
    assert any("entity registry category distribution" in failure for failure in report.failures)


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


def test_verify_storage_rejects_device_backed_entities_without_device_id(
    tmp_path: Path,
) -> None:
    """设备来源实体必须挂到 HA device registry."""
    entities = _yeelight_entities()
    for entity in entities:
        if entity.get("unique_id") == "yeelight_pro_304784333_light_0":
            entity["device_id"] = None
            break
    _write_storage(tmp_path, "core.config_entries", {"entries": [_config_entry()]})
    _write_storage(tmp_path, "core.device_registry", {"devices": _yeelight_devices()})
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

    assert not report.ok
    assert any(
        "device-backed entity registry entries missing device_id" in failure
        for failure in report.failures
    )


def test_verify_storage_rejects_raw_numeric_entity_names(
    tmp_path: Path,
) -> None:
    """多键开关等实体不能在 HA 设备页显示裸数字名称."""
    entities = _yeelight_entities()
    entities.append({
        "platform": "yeelight_pro",
        "entity_id": "switch.raw_channel",
        "unique_id": "yeelight_pro_304784336_switch_4",
        "original_name": "4",
        "device_id": "device-registry-2",
    })
    _write_storage(tmp_path, "core.config_entries", {"entries": [_config_entry()]})
    _write_storage(tmp_path, "core.device_registry", {"devices": _yeelight_devices()})
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

    assert not report.ok
    assert any("raw channel/action names" in failure for failure in report.failures)


def test_verify_storage_rejects_generated_switch_and_light_entity_names(
    tmp_path: Path,
) -> None:
    """旧一键/二键/照明名称应阻断，避免设备页继续显示生成名."""
    entities = _yeelight_entities()
    entities.extend([
        {
            "platform": "yeelight_pro",
            "entity_id": "switch.generated_channel",
            "unique_id": "yeelight_pro_304784336_switch_1",
            "original_name": "一键",
            "device_id": "device-registry-2",
        },
        {
            "platform": "yeelight_pro",
            "entity_id": "light.generated_light",
            "unique_id": "yeelight_pro_304784333_light",
            "original_name": "照明",
            "device_id": "device-registry-1",
        },
    ])
    _write_storage(tmp_path, "core.config_entries", {"entries": [_config_entry()]})
    _write_storage(tmp_path, "core.device_registry", {"devices": _yeelight_devices()})
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

    assert not report.ok
    assert any("raw channel/action names" in failure for failure in report.failures)


def test_verify_storage_rejects_generated_light_name_without_switch_noise(
    tmp_path: Path,
) -> None:
    """单独的旧 light“照明”名称也应阻断，避免主实体卡片继续显示泛化控制项."""
    entities = _yeelight_entities()
    entities.append({
        "platform": "yeelight_pro",
        "entity_id": "light.generated_light",
        "unique_id": "yeelight_pro_304784333_light",
        "original_name": "照明",
        "device_id": "device-registry-1",
    })
    _write_storage(tmp_path, "core.config_entries", {"entries": [_config_entry()]})
    _write_storage(tmp_path, "core.device_registry", {"devices": _yeelight_devices()})
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

    assert not report.ok
    assert any("raw channel/action names" in failure for failure in report.failures)


def test_verify_storage_rejects_unavailable_yeelight_restore_states(
    tmp_path: Path,
) -> None:
    """Yeelight restore state 大量不可用应阻断本地 HA 验证."""
    _write_storage(tmp_path, "core.config_entries", {"entries": [_config_entry()]})
    _write_storage(tmp_path, "core.device_registry", {"devices": _yeelight_devices()})
    _write_storage(tmp_path, "core.entity_registry", {"entities": _yeelight_entities()})
    _write_storage(
        tmp_path,
        "core.restore_state",
        [
            {"state": {"entity_id": "light.sample_0", "state": "on"}},
            {"state": {"entity_id": "switch.sample_0", "state": "unavailable"}},
            {"state": {"entity_id": "button.xiaomi_sample", "state": "unavailable"}},
        ],
    )
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
    assert any("restored states are unavailable" in failure for failure in report.failures)
    restore_metric = report.metrics["yeelight_restore_state"]
    assert isinstance(restore_metric, dict)
    assert restore_metric["restored"] == 2
    assert restore_metric["unavailable"] == 1
