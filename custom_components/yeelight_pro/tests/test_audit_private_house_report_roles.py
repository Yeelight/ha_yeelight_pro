"""Private-house coverage report role and stale-sample tests."""

from __future__ import annotations

from custom_components.yeelight_pro.entity_candidates import iter_device_entity_candidates
from custom_components.yeelight_pro.identity import IDENTITY_SCOPE_KEY
from scripts.private_house_audit.io_helpers import entity_registry_by_unique_id
from scripts.private_house_audit.report import build_report

from .projection_helpers import projection_payload


def test_build_report_summarizes_user_visible_entity_roles() -> None:
    """审计报告应区分主实体、诊断和事件，便于逐设备验收。"""
    payload = {
        "id": 1001,
        "name": "Scene Panel",
        "category": "scene_panel",
        "type": "scene_panel",
        "params": {"o": 1},
        "ha_product_model": {
            "components": [
                {
                    "component_id": "scene_panel_1",
                    "category": "scene_panel",
                    "events": [{"event_id": "click"}],
                }
            ]
        },
    }
    diagnostic_unique_id = next(
        candidate.unique_id
        for candidate in iter_device_entity_candidates(payload)
        if candidate.entity_category == "diagnostic"
    )
    report = build_report(
        entry={"entry_id": "entry-1", "title": "Private"},
        entry_data={"connection_mode": "private", "house_id": 1},
        runtime_data={1001: payload},
        registry_entries={
            diagnostic_unique_id: {
                "entity_id": "sensor.scene_panel_online_status",
                "entity_category": "diagnostic",
            }
        },
        hydration={},
        endpoint_errors={},
    )

    device = report["devices"][0]

    assert report["summary"]["expected_roles"] == {
        "diagnostic": 1,
        "event": 1,
    }
    assert report["summary"]["actual_roles"] == {"diagnostic": 1}
    assert report["summary"]["missing_roles"] == {"event": 1}
    assert report["summary"]["missing_platforms"] == {"event": 1}
    assert report["summary"]["registry_reload_required"] == {
        "required": True,
        "missing_devices": 1,
        "missing_entities": 1,
        "missing_platforms": {"event": 1},
        "missing_roles": {"event": 1},
        "missing_devices_by_category": {"scene_panel": 1},
    }
    assert device["expected_roles"] == {"diagnostic": 1, "event": 1}
    assert device["actual_roles"] == {"diagnostic": 1}
    assert device["missing_roles"] == {"event": 1}
    assert device["expected_samples"] == [
        {
            "platform": "sensor",
            "component_id": "online_status",
            "name": "在线状态",
            "entity_category": "diagnostic",
            "role": "diagnostic",
            "unique_id_hash": "86b16970b8fe99b0",
        },
        {
            "platform": "event",
            "component_id": "scene_panel_1",
            "name": "scene_panel_1 事件",
            "entity_category": "primary",
            "role": "event",
            "unique_id_hash": "86443800dc8b51d1",
        },
    ]
    assert device["missing_samples"][0]["role"] == "event"


def test_build_report_redacts_property_values_but_counts_presence() -> None:
    """源数据证据只暴露属性值是否存在，不暴露真实值。"""
    payload = {
        "id": 1001,
        "name": "Undocumented Speaker",
        "category": "unknown",
        "type": "",
        "params": {"o": True},
        "properties": [
            {"propId": "o", "value": True},
            {"propId": "amicvol", "value": 42},
            {"propId": "ams", "data": None},
            {"propId": "private_flag"},
        ],
    }

    report = build_report(
        entry={"entry_id": "entry-1", "title": "Private"},
        entry_data={"connection_mode": "private", "house_id": 1},
        runtime_data={1001: payload},
        registry_entries={},
        hydration={},
        endpoint_errors={},
    )

    evidence = report["devices"][0]["source_evidence"]

    assert evidence["raw_property_count"] == 4
    assert evidence["raw_property_keys"] == ["amicvol", "ams", "o", "private_flag"]
    assert evidence["raw_property_value_count"] == 2
    assert evidence["raw_property_empty_count"] == 2
    assert evidence["raw_property_value_fields"] == ["data", "value"]
    assert "42" not in str(evidence)


def test_build_report_includes_redacted_stale_registry_samples() -> None:
    """审计报告应保留旧 registry 行样本，便于识别实体类型迁移。"""
    scope = "private_endpoint_scope_house_1"
    payload = projection_payload(
        device_id="1001",
        category="other",
        component_id="other",
        component_category="other",
        state={},
        params={},
    )
    payload["name"] = "P20"
    payload[IDENTITY_SCOPE_KEY] = scope
    payload["ha_device_instance"][IDENTITY_SCOPE_KEY] = scope
    payload["ha_product_model"]["components"][0]["properties"] = [
        {
            "prop_id": "mpml",
            "access": "read_write",
            "property_type": "int",
            "format": "uint16",
            "value_range": {"min": 0, "max": 65535, "step": 1},
        }
    ]
    expected_unique_id = next(
        candidate.unique_id
        for candidate in iter_device_entity_candidates(payload)
        if candidate.component_id == "other_mpml_number"
    )
    stale_unique_id = expected_unique_id.removesuffix("_number") + "_switch"

    report = build_report(
        entry={"entry_id": "entry-1", "title": "Private"},
        entry_data={"connection_mode": "private", "house_id": 1},
        runtime_data={1001: payload},
        registry_entries={
            stale_unique_id: {
                "entity_id": "switch.p20_music_list",
                "entity_category": "config",
                "original_name": "音乐播放器歌单ID",
                "unique_id": stale_unique_id,
            }
        },
        hydration={},
        endpoint_errors={},
    )

    device = report["devices"][0]

    assert device["missing_samples"][0]["component_id"] == "other_mpml_number"
    assert device["stale_samples"] == [
        {
            "platform": "switch",
            "component_id": "other_mpml_switch",
            "name": "音乐播放器歌单ID",
            "entity_category": "config",
            "role": "config",
            "unique_id_hash": device["stale_samples"][0]["unique_id_hash"],
        }
    ]


def test_entity_registry_by_unique_id_ignores_disabled_rows(tmp_path) -> None:
    """覆盖审计只统计 HA 页面可见实体，已禁用旧实体不应继续算作 extra."""
    storage = tmp_path / ".storage"
    storage.mkdir()
    (storage / "core.entity_registry").write_text(
        """
        {
          "data": {
            "entities": [
              {
                "config_entry_id": "entry-1",
                "disabled_by": null,
                "unique_id": "visible-uid",
                "entity_id": "switch.visible"
              },
              {
                "config_entry_id": "entry-1",
                "disabled_by": "integration",
                "unique_id": "disabled-uid",
                "entity_id": "switch.disabled"
              },
              {
                "config_entry_id": "entry-2",
                "disabled_by": null,
                "unique_id": "other-entry-uid",
                "entity_id": "switch.other"
              }
            ]
          }
        }
        """,
        encoding="utf-8",
    )

    rows = entity_registry_by_unique_id(tmp_path, "entry-1")

    assert set(rows) == {"visible-uid"}
