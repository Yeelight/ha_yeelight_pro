"""Local HA storage verification tests."""

from __future__ import annotations

from pathlib import Path

from scripts.verify_local_ha import (
    DEFAULT_ENTITY_COUNTS,
    VerificationReport,
    verify_storage,
)
from .storage_verifier_helpers import (
    config_entry as _config_entry,
    write_storage as _write_storage,
    yeelight_devices as _yeelight_devices,
    yeelight_entities as _yeelight_entities,
)


def test_verify_storage_checks_counts_without_raw_ids(tmp_path: Path) -> None:
    """Storage verification should pass on aggregate local HA facts."""
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
    assert any("entity registry entries: 140" in fact for fact in report.facts)
    assert any("config entry versions: 1.6 x 1" in fact for fact in report.facts)
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
            "experimental_platforms",
            "hide_unknown_entities",
            "scan_interval",
            "topology_change_repairs",
        ],
    }
    platform_options = report.metrics["platform_options"]
    assert isinstance(platform_options, dict)
    assert platform_options["experimental"] == ["vacuum"]
    assert "vacuum" not in platform_options["expected_union"]


def test_verify_storage_reports_platform_options_alignment(tmp_path: Path) -> None:
    """默认安装态不应把实验平台计入启用平台集合."""
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
    assert any("experimental=['vacuum']" in fact for fact in report.facts)
    platform_options = report.metrics["platform_options"]
    assert isinstance(platform_options, dict)
    assert platform_options["per_entry_expected_counts"] == [(13, 1)]


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


def test_verify_storage_rejects_experimental_domain_without_opt_in(
    tmp_path: Path,
) -> None:
    """未启用 experimental_platforms 时，vacuum 实体域应阻断本地 HA 验证."""
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
    assert any("config entry title mismatch" in failure for failure in report.failures)
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
    assert any("config entry data missing required keys" in failure for failure in report.failures)
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


def test_verify_storage_rejects_missing_required_option_keys(tmp_path: Path) -> None:
    """安装态 options 缺失必需键时应阻断，且不泄露过滤规则内容."""
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

    assert not report.ok
    assert any("options missing required keys" in failure for failure in report.failures)
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


def test_verify_storage_rejects_removed_analytics_options(tmp_path: Path) -> None:
    """安装态 options 不应残留已删除的 analytics runtime 配置键."""
    entry = _config_entry()
    options = dict(entry["options"])
    options["analytics_runtime"] = True
    options["analytics_retention_days"] = 90
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
    assert any("options contain removed keys" in failure for failure in report.failures)
    assert all("True" not in failure for failure in report.failures)
    assert all("90" not in failure for failure in report.failures)


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
