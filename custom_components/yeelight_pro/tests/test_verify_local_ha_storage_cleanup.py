"""Local HA storage cleanup verifier tests."""

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


def test_verify_storage_fails_for_enabled_legacy_scene_entities(
    tmp_path: Path,
) -> None:
    """旧原生 scene 实体启用时必须阻断，避免 UI 继续调用 scene.turn_on."""
    entities = _yeelight_entities()
    entities.append({
        "platform": "yeelight_pro",
        "entity_id": "scene.legacy_cloud_scene",
        "unique_id": "yeelight_pro_scene_legacy",
        "device_id": None,
        "disabled_by": None,
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
    assert any("legacy native scene registry entries" in item for item in report.failures)


def test_verify_storage_allows_disabled_stale_raw_channel_names(
    tmp_path: Path,
) -> None:
    """cleanup B 保留的旧 raw 名称实体禁用后不应继续阻断 UI 验证."""
    entities = _yeelight_entities()
    entities.append({
        "platform": "yeelight_pro",
        "entity_id": "switch.stale_raw_channel",
        "unique_id": "yeelight_pro_304784336_switch_stale",
        "original_name": "三键",
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
