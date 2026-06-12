"""Local HA config-entry storage verification tests."""

from __future__ import annotations

from pathlib import Path

from scripts.verify_local_ha import (
    DEFAULT_ENTITY_COUNTS,
    VerificationReport,
    verify_storage,
)
from .storage_verifier_helpers import (
    config_entry as _config_entry,
    lan_config_entry as _lan_config_entry,
    write_storage as _write_storage,
    yeelight_devices as _yeelight_devices,
    yeelight_entities as _yeelight_entities,
)


def test_verify_storage_rejects_unmigrated_config_entry_version(tmp_path: Path) -> None:
    """本地 HA 验证应发现未迁移的 config entry 版本."""
    old_entry = _config_entry()
    old_entry["minor_version"] = 1
    _write_storage(tmp_path, "core.config_entries", {"entries": [old_entry]})
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

    assert not report.ok
    assert any("migration version mismatch" in failure for failure in report.failures)


def test_verify_storage_rejects_legacy_cloud_unique_id(tmp_path: Path) -> None:
    """安装态 verifier 应阻断未迁移的旧 cloud unique_id."""
    entry = _config_entry()
    entry["unique_id"] = "yeelight_pro_cloud"
    _write_storage(tmp_path, "core.config_entries", {"entries": [entry]})
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

    assert not report.ok
    assert any("unique_id isolation mismatch" in failure for failure in report.failures)
    assert all("secret-token" not in failure for failure in report.failures)
    assert all("122349" not in failure for failure in report.failures)


def test_verify_storage_rejects_legacy_config_entry_title(tmp_path: Path) -> None:
    """安装态 verifier 应阻断无法区分账号/区域/家庭的旧标题."""
    entry = _config_entry()
    entry["title"] = "Yeelight Pro Cloud"
    _write_storage(tmp_path, "core.config_entries", {"entries": [entry]})
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

    assert not report.ok
    assert any(
        "config entry title or house name mismatch" in failure
        for failure in report.failures
    )
    assert all("secret-user" not in failure for failure in report.failures)
    assert all("secret-token" not in failure for failure in report.failures)


def test_verify_storage_reports_missing_config_entry_keys_without_values(
    tmp_path: Path,
) -> None:
    """config entry 必需键缺失时只能输出键名和计数，不能泄露敏感值."""
    entry = _config_entry()
    entry["data"] = {
        "access_token": "secret-token",
        "connection_mode": "cloud",
    }
    _write_storage(tmp_path, "core.config_entries", {"entries": [entry]})
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

    assert not report.ok
    assert any(
        "config entry data missing required keys" in failure
        for failure in report.failures
    )
    assert all("secret-token" not in failure for failure in report.failures)


def test_verify_storage_allows_missing_optional_open_api_client_id(
    tmp_path: Path,
) -> None:
    """手动 token 旧 entry 可缺少 open_api_client_id，但 verifier 应记录聚合事实."""
    entry = _config_entry()
    data = dict(entry["data"])
    data.pop("open_api_client_id")
    entry["data"] = data
    _write_storage(tmp_path, "core.config_entries", {"entries": [entry]})
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
    assert any("optional data keys absent" in fact for fact in report.facts)


def test_verify_storage_allows_cloud_and_lan_entries(tmp_path: Path) -> None:
    """本地 HA 验证应允许云端账号与 LAN 网关 entry 并存."""
    _write_storage(
        tmp_path,
        "core.config_entries",
        {"entries": [_config_entry(), _lan_config_entry()]},
    )
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
    assert any("enabled config entries: 2" in fact for fact in report.facts)
    assert report.metrics["config_entries"] == 2


def test_verify_storage_reports_defaulted_option_keys(tmp_path: Path) -> None:
    """安装态 options 缺省默认键时记录聚合事实，不阻断旧 entry 归一化."""
    entry = _config_entry()
    entry["options"] = {"scan_interval": 30}
    _write_storage(tmp_path, "core.config_entries", {"entries": [entry]})
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
    assert any("option keys defaulted by migration" in fact for fact in report.facts)
    assert all("device-1" not in failure for failure in report.failures)


def test_verify_storage_rejects_invalid_option_values(tmp_path: Path) -> None:
    """安装态 options 类型或范围异常时应输出聚合键名计数."""
    entry = _config_entry()
    options = dict(entry["options"])
    options["scan_interval"] = 5
    options["debug_mode"] = "yes"
    entry["options"] = options
    _write_storage(tmp_path, "core.config_entries", {"entries": [entry]})
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

    assert not report.ok
    assert any("options outside allowed bounds" in failure for failure in report.failures)
    assert all("yes" not in failure for failure in report.failures)
