"""Private-house zero-control classification edge cases."""

from __future__ import annotations

from scripts.private_house_audit.classification import (
    ACTION_NO_CODE_CHANGE,
    STATUS_OK,
    classify_device,
)
from scripts.private_house_audit.classification_rows import classified_device_row


def _writable_telemetry_device() -> dict[str, object]:
    """Return a sensor-like device whose writable telemetry is already projected."""
    return {
        "category": "light_sensor",
        "actual_total": 4,
        "expected_total": 4,
        "missing_total": 0,
        "params_count": 1,
        "model_components_count": 1,
        "model_properties_count": 3,
        "model_writable_properties_count": 1,
        "model_readable_properties_count": 3,
        "expected_roles": {
            "diagnostic": 1,
            "event": 1,
            "primary_control_or_state": 2,
        },
        "actual_roles": {
            "diagnostic": 1,
            "event": 1,
            "primary_control_or_state": 2,
        },
        "expected_platforms": {"binary_sensor": 1, "event": 1, "sensor": 2},
        "actual_platforms": {"binary_sensor": 1, "event": 1, "sensor": 2},
        "source_evidence": {
            "raw_property_count": 3,
            "raw_property_keys": ["luminance", "mv", "o"],
            "product_model_available": True,
            "product_schema_available": False,
        },
        "unprojected_writable_properties": [],
    }


def test_writable_telemetry_sensor_is_not_missing_a_control() -> None:
    """read_write telemetry already projected as sensor state should not need controls."""
    result = classify_device(_writable_telemetry_device())

    assert result["status"] == STATUS_OK
    assert result["action"] == ACTION_NO_CODE_CHANGE


def test_writable_telemetry_absence_reason_explains_state_coverage() -> None:
    """The per-device row should explain why a zero-control sensor is acceptable."""
    row = classified_device_row(
        _writable_telemetry_device(),
        {
            "status": STATUS_OK,
            "action": ACTION_NO_CODE_CHANGE,
            "reason": "projected_entities_match_current_registry_and_known_capabilities",
        },
    )

    assert row["coverage_view"]["control"] == {
        "expected": 0,
        "actual": 0,
        "missing": 0,
        "status": "not_expected",
    }
    assert row["strict_control"]["absence_reason"] == (
        "writable_properties_projected_as_state_or_event_entities"
    )


def test_scene_panel_absence_reason_explains_event_input_controls() -> None:
    """事件输入设备完整覆盖事件实体时，不应标记为控制缺失。"""
    row = classified_device_row(
        {
            "category": "scene_panel",
            "actual_total": 5,
            "expected_total": 5,
            "missing_total": 0,
            "params_count": 1,
            "model_components_count": 4,
            "model_writable_properties_count": 4,
            "expected_roles": {"diagnostic": 1, "event": 4},
            "actual_roles": {"diagnostic": 1, "event": 4},
            "expected_platforms": {"event": 4, "sensor": 1},
            "actual_platforms": {"event": 4, "sensor": 1},
        },
        {
            "status": STATUS_OK,
            "action": ACTION_NO_CODE_CHANGE,
            "reason": "projected_entities_match_current_registry_and_known_capabilities",
        },
    )

    assert row["coverage_view"]["control"] == {
        "expected": 0,
        "actual": 0,
        "missing": 0,
        "status": "not_expected",
    }
    assert row["strict_control"]["absence_reason"] == (
        "event_input_device_events_are_not_controls"
    )


def test_event_subdevice_absence_reason_explains_event_projection() -> None:
    """跨品类复合面板应解释为事件子设备，而不是缺控制。"""
    row = classified_device_row(
        {
            "category": "human_sensor",
            "actual_total": 8,
            "expected_total": 8,
            "missing_total": 0,
            "model_writable_properties_count": 6,
            "expected_roles": {
                "diagnostic": 1,
                "event": 6,
                "primary_control_or_state": 1,
            },
            "actual_roles": {
                "diagnostic": 1,
                "event": 6,
                "primary_control_or_state": 1,
            },
            "expected_platforms": {"binary_sensor": 1, "event": 6, "sensor": 1},
            "actual_platforms": {"binary_sensor": 1, "event": 6, "sensor": 1},
            "source_evidence": {
                "subdevice_property_count": 6,
                "subdevice_property_keys": ["1-p", "2-p", "3-p"],
            },
        },
        {
            "status": STATUS_OK,
            "action": ACTION_NO_CODE_CHANGE,
            "reason": "projected_entities_match_current_registry_and_known_capabilities",
        },
    )

    assert row["coverage_view"]["control"]["status"] == "not_expected"
    assert row["strict_control"]["absence_reason"] == (
        "event_input_subdevices_are_projected_as_events"
    )
