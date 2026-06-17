"""Local HA storage verification tests."""

from __future__ import annotations

from pathlib import Path

from custom_components.yeelight_pro.const import PLATFORMS
from custom_components.yeelight_pro.entry_migration import ENTRY_MINOR_VERSION
from scripts.verify_local_ha import (
    DEFAULT_ENTITY_COUNTS,
    VerificationReport,
    expected_runtime_entity_counts,
    verify_storage,
)
from .storage_verifier_helpers import (
    config_entry as _config_entry,
    lan_config_entry as _lan_config_entry,
    write_storage as _write_storage,
    yeelight_devices as _yeelight_devices,
    yeelight_entities as _yeelight_entities,
)


def test_verify_storage_checks_counts_without_raw_ids(tmp_path: Path) -> None:
    """Storage verification should pass on aggregate local HA facts."""
    entities = _yeelight_entities()
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

    assert report.ok
    expected_total = sum(DEFAULT_ENTITY_COUNTS.values())
    assert any(
        f"entity registry retained entries: {expected_total}" in fact
        for fact in report.facts
    )
    assert any(
        f"config entry versions: 1.{ENTRY_MINOR_VERSION} x 1" in fact
        for fact in report.facts
    )
    assert any("config entry titles" in fact for fact in report.facts)
    assert any("config entry unique_id isolation" in fact for fact in report.facts)
    assert any("config entry required data keys present" in fact for fact in report.facts)
    assert any("config entry required option keys present" in fact for fact in report.facts)
    assert any("config entry option bounds valid" in fact for fact in report.facts)
    assert any("platform options alignment" in fact for fact in report.facts)
    assert report.metrics["config_entry_options"] == {
        "device_filter_enabled": 0,
        "missing_optional": {"device_import_filter": 1},
        "required_keys": [
            "debug_mode",
            "hide_unknown_entities",
            "scan_interval",
            "topology_change_repairs",
        ],
    }
    platform_options = report.metrics["platform_options"]
    assert isinstance(platform_options, dict)
    assert platform_options["experimental"] == []
    assert "vacuum" not in platform_options["expected_union"]
    assert any("house selector entity metadata" in fact for fact in report.facts)
    assert any("entity registry categories" in fact for fact in report.facts)
    assert report.metrics["entity_registry_categories"] == _entity_category_counts(entities)


def _entity_category_counts(entities: list[dict[str, str | None]]) -> dict[str, int]:
    """Return expected entity-category counts from the fixture entries."""
    counts: dict[str, int] = {}
    for entity in entities:
        category = entity.get("entity_category")
        if category:
            counts[category] = counts.get(category, 0) + 1
    return counts


def test_verify_storage_reports_platform_options_alignment(tmp_path: Path) -> None:
    """默认安装态平台集合应直接来自当前 PLATFORMS。"""
    _write_storage(tmp_path, "core.config_entries", {"entries": [_config_entry()]})
    _write_storage(tmp_path, "core.device_registry", {"devices": _yeelight_devices()})
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
    assert any("experimental=[]" in fact for fact in report.facts)
    platform_options = report.metrics["platform_options"]
    assert isinstance(platform_options, dict)
    assert platform_options["per_entry_expected_counts"] == [(len(PLATFORMS), 1)]


def test_verify_storage_accepts_lan_only_entry_with_smaller_retained_baseline(
    tmp_path: Path,
) -> None:
    """LAN-only 验证环境没有云端大拓扑时不应被 cloud baseline 误判失败."""
    entities = [
        {
            "platform": "yeelight_pro",
            "entity_id": "light.lan_sample",
            "unique_id": "yeelight_pro_312613269_light",
            "device_id": "device-registry-1",
        },
        {
            "platform": "yeelight_pro",
            "entity_id": "sensor.lan_sample_online",
            "unique_id": "yeelight_pro_312613269_online_status",
            "device_id": "device-registry-1",
            "entity_category": "diagnostic",
            "original_name": "在线状态",
        },
        {
            "platform": "yeelight_pro",
            "entity_id": "number.lan_sample_dd",
            "unique_id": "yeelight_pro_312613269_light_dd_number",
            "device_id": "device-registry-1",
            "entity_category": "config",
            "original_name": "默认渐变时长",
        },
        {
            "platform": "yeelight_pro",
            "entity_id": "select.lan_sample_room",
            "unique_id": "yeelight_pro_0_select_room",
            "device_id": "device-registry-1",
            "translation_key": "active_room",
        },
        {
            "platform": "yeelight_pro",
            "entity_id": "select.lan_sample_group",
            "unique_id": "yeelight_pro_0_select_group",
            "device_id": "device-registry-1",
            "translation_key": "active_group",
        },
        {
            "platform": "yeelight_pro",
            "entity_id": "select.lan_sample_scene",
            "unique_id": "yeelight_pro_0_select_scene",
            "device_id": "device-registry-1",
            "translation_key": "active_scene",
        },
    ]
    _write_storage(tmp_path, "core.config_entries", {"entries": [_lan_config_entry()]})
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

    assert report.ok
    assert any("config entry titles" in fact and "lan=1" in fact for fact in report.facts)
    assert any("entity registry retained entries: 6" in fact for fact in report.facts)
    assert report.metrics["retained_entity_domains"] == {
        "light": 1,
        "number": 1,
        "select": 3,
        "sensor": 1,
    }


def test_verify_storage_accepts_private_lan_real_account_baseline(
    tmp_path: Path,
) -> None:
    """private+LAN 实测环境按当前 registry 建 baseline，而不是云端大样本."""
    entities = [
        {
            "platform": "yeelight_pro",
            "entity_id": "light.private_room",
            "unique_id": "yeelight_pro_private_house_1_room_1",
            "device_id": "device-registry-1",
        },
        {
            "platform": "yeelight_pro",
            "entity_id": "switch.private_switch",
            "unique_id": "yeelight_pro_private_house_1_device_304784336_switch_1",
            "device_id": "device-registry-2",
        },
        {
            "platform": "yeelight_pro",
            "entity_id": "select.private_room",
            "unique_id": "yeelight_pro_private_house_1_select_room",
            "translation_key": "active_room",
            "entity_category": "config",
        },
        {
            "platform": "yeelight_pro",
            "entity_id": "select.private_group",
            "unique_id": "yeelight_pro_private_house_1_select_group",
            "translation_key": "active_group",
            "entity_category": "config",
        },
        {
            "platform": "yeelight_pro",
            "entity_id": "select.private_scene",
            "unique_id": "yeelight_pro_private_house_1_select_scene",
            "translation_key": "active_scene",
            "entity_category": "config",
        },
        {
            "platform": "yeelight_pro",
            "entity_id": "sensor.private_online",
            "unique_id": "yeelight_pro_private_house_1_device_304784336_online_status",
            "original_name": "在线状态",
            "device_id": "device-registry-2",
            "entity_category": "diagnostic",
        },
    ]
    private_entry = _config_entry()
    private_entry["unique_id"] = "private:https://private.example:1"
    private_entry["title"] = "Yeelight Pro Private (https://private.example · 家)"
    private_entry["data"] = {
        **private_entry["data"],
            "connection_mode": "private",
            "house_name": "家",
            "private_domain": "https://private.example",
            "private_push_domain": "wss://push.private.example/ws",
        }
    _write_storage(
        tmp_path,
        "core.config_entries",
        {"entries": [private_entry, _lan_config_entry()]},
    )
    _write_storage(tmp_path, "core.device_registry", {"devices": _yeelight_devices()})
    _write_storage(tmp_path, "core.entity_registry", {"entities": entities})
    report = VerificationReport()

    verify_storage(
        tmp_path,
        report,
        expected_config_entries=1,
        expected_devices=75,
        expected_entities=sum(DEFAULT_ENTITY_COUNTS.values()),
        expected_entity_counts=DEFAULT_ENTITY_COUNTS,
    )

    assert report.ok
    assert report.metrics["devices"] == 2
    assert report.metrics["retained_entities"] == 6
    assert expected_runtime_entity_counts(tmp_path, DEFAULT_ENTITY_COUNTS) == {
        "light": 1,
        "select": 3,
        "sensor": 1,
        "switch": 1,
    }


def test_verify_storage_allows_cleanup_b_retained_disabled_entities(
    tmp_path: Path,
) -> None:
    """cleanup B 会保留禁用的旧 registry，storage 侧不能按 active 精确计数."""
    entities = _yeelight_entities()
    entities.append({
        "platform": "yeelight_pro",
        "entity_id": "switch.stale_switch",
        "unique_id": "yeelight_pro_304784336_switch_stale",
        "device_id": "device-registry-2",
        "disabled_by": "integration",
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

    assert report.ok
    expected_retained = sum(DEFAULT_ENTITY_COUNTS.values()) + 1
    assert any(
        f"entity registry retained entries: {expected_retained}" in fact
        for fact in report.facts
    )
    assert any("entity registry disabled_by" in fact for fact in report.facts)
    assert report.metrics["retained_entities"] == expected_retained


def test_verify_storage_rejects_unsupported_platform_domain(
    tmp_path: Path,
) -> None:
    """不在当前 PLATFORMS 的实体域应阻断本地 HA 验证."""
    entities = [*_yeelight_entities(), {"platform": "yeelight_pro", "entity_id": "vacuum.sample_0"}]
    expected_counts = dict(DEFAULT_ENTITY_COUNTS)
    expected_counts["vacuum"] = 1
    _write_storage(tmp_path, "core.config_entries", {"entries": [_config_entry()]})
    _write_storage(tmp_path, "core.device_registry", {"devices": _yeelight_devices()})
    _write_storage(tmp_path, "core.entity_registry", {"entities": entities})
    report = VerificationReport()

    verify_storage(
        tmp_path,
        report,
        expected_config_entries=1,
        expected_devices=2,
        expected_entities=sum(expected_counts.values()),
        expected_entity_counts=expected_counts,
    )

    assert not report.ok
    assert any(
        "entity domains are not enabled by config entry options: ['vacuum']"
        in failure
        for failure in report.failures
    )


def test_verify_storage_reports_missing_files_without_raw_payload(tmp_path: Path) -> None:
    """Storage read failures should be aggregated instead of raising tracebacks."""
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
    assert any("core.config_entries" in failure for failure in report.failures)
    assert all("secret" not in failure for failure in report.failures)
