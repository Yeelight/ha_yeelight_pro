"""Local HA restore-state quality verification tests."""

from __future__ import annotations

from pathlib import Path

from scripts.verify_local_ha import DEFAULT_ENTITY_COUNTS, VerificationReport, verify_storage

from .storage_verifier_helpers import (
    config_entry as _config_entry,
    write_storage as _write_storage,
    yeelight_devices as _yeelight_devices,
    yeelight_entities as _yeelight_entities,
)


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
    assert any(
        "restored states are unavailable" in failure
        for failure in report.failures
    )
    restore_metric = report.metrics["yeelight_restore_state"]
    assert isinstance(restore_metric, dict)
    assert restore_metric["restored"] == 2
    assert restore_metric["unavailable"] == 1


def test_verify_storage_ignores_event_restore_state_unavailable(
    tmp_path: Path,
) -> None:
    """event 实体的历史 unavailable restore state 不代表运行时同步失败."""
    _write_storage(tmp_path, "core.config_entries", {"entries": [_config_entry()]})
    _write_storage(tmp_path, "core.device_registry", {"devices": _yeelight_devices()})
    _write_storage(tmp_path, "core.entity_registry", {"entities": _yeelight_entities()})
    _write_storage(
        tmp_path,
        "core.restore_state",
        [
            {"state": {"entity_id": "event.sample_0", "state": "unavailable"}},
            {"state": {"entity_id": "sensor.sample_0", "state": "42"}},
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

    assert report.ok
    restore_metric = report.metrics["yeelight_restore_state"]
    assert isinstance(restore_metric, dict)
    assert restore_metric["restored"] == 1
    assert restore_metric["unavailable"] == 0
