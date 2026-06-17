"""Local HA storage entity registry quality verification tests."""

from __future__ import annotations

from pathlib import Path

from scripts.verify_local_ha import DEFAULT_ENTITY_COUNTS, VerificationReport, verify_storage

from .storage_verifier_helpers import (
    config_entry as _config_entry,
    write_storage as _write_storage,
    yeelight_devices as _yeelight_devices,
    yeelight_entities as _yeelight_entities,
)


def test_verify_storage_rejects_house_selects_without_name_or_translation_key(
    tmp_path: Path,
) -> None:
    """固定 select 同时缺少友好名称和翻译键时必须阻断."""
    entities = _yeelight_entities()
    entities.extend([
        {
            "platform": "yeelight_pro",
            "entity_id": "select.yeelight_pro_1",
            "unique_id": "yeelight_pro_cloud_cn_account_fixture_house_1_select_room",
            "original_name": None,
            "device_id": None,
        },
        {
            "platform": "yeelight_pro",
            "entity_id": "select.yeelight_pro_2",
            "unique_id": "yeelight_pro_cloud_cn_account_fixture_house_1_select_group",
            "original_name": "当前灯组",
            "device_id": None,
        },
        {
            "platform": "yeelight_pro",
            "entity_id": "select.yeelight_pro_3",
            "unique_id": "yeelight_pro_cloud_cn_account_fixture_house_1_select_scene",
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
    assert any(
        "entity registry category distribution" in failure
        for failure in report.failures
    )


def test_verify_storage_rejects_device_backed_entities_without_device_id(
    tmp_path: Path,
) -> None:
    """设备来源实体必须挂到 HA device registry."""
    entities = _yeelight_entities()
    for entity in entities:
        if entity.get("unique_id") == "yeelight_pro_cloud_cn_account_fixture_house_1_device_304784333_light_0":
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
    """多键开关等实体不能在 HA 设备页显示裸数字或英文字段名."""
    entities = _yeelight_entities()
    entities.extend([
        {
            "platform": "yeelight_pro",
            "entity_id": "switch.raw_channel",
            "unique_id": "yeelight_pro_304784336_switch_4",
            "original_name": "4",
            "device_id": "device-registry-2",
        },
        {
            "platform": "yeelight_pro",
            "entity_id": "number.raw_property",
            "unique_id": "yeelight_pro_304784333_light_dd_number",
            "original_name": "default duration",
            "device_id": "device-registry-1",
            "entity_category": "config",
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
    assert any(
        "raw channel/action/property names" in failure
        for failure in report.failures
    )


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
    assert any(
        "raw channel/action/property names" in failure
        for failure in report.failures
    )


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
    assert any(
        "raw channel/action/property names" in failure
        for failure in report.failures
    )
