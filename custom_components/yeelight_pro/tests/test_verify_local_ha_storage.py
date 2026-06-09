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
    assert any("config entry versions: 1.3 x 1" in fact for fact in report.facts)
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


def test_verify_storage_allows_missing_optional_oauth_client_id(
    tmp_path: Path,
) -> None:
    """手动 token 旧 entry 可缺少 oauth_client_id，但 verifier 应记录聚合事实."""
    entry = _config_entry()
    data = dict(entry["data"])
    data.pop("oauth_client_id")
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
