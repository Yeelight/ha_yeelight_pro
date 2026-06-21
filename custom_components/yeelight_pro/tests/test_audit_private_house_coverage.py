"""Private-house coverage audit helper tests."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from custom_components.yeelight_pro.core.exceptions import CommandError
from scripts.audit_private_house_coverage import (
    _projected_property_keys,
    _unprojected_property_samples,
)
from scripts.private_house_audit.io_helpers import safe_mapping
from scripts.private_house_audit import io_helpers
from scripts.private_house_audit.report import build_report
from scripts.private_house_audit.schema_cache import (
    cached_product_schemas,
    merge_product_schemas,
)


def test_online_status_candidate_covers_documented_o_property() -> None:
    """online_status 诊断实体代表物模型 o，审计不应重复报缺口。"""
    keys = _projected_property_keys(
        {},
        [SimpleNamespace(platform="sensor", component_id="online_status")],
    )

    assert ("", "o") in keys


def test_cached_product_schemas_reads_ha_storage_shape(tmp_path) -> None:
    """审计脚本应复用 HA schema cache 的标准 .storage 外层结构."""
    storage = tmp_path / ".storage"
    storage.mkdir()
    (storage / "yeelight_pro.product_schemas").write_text(
        (
            '{"version":1,"minor_version":1,'
            '"key":"yeelight_pro.product_schemas",'
            '"data":{"schemas":{"100":{"pid":100,"name":"Cached"}}}}'
        ),
        encoding="utf-8",
    )

    assert cached_product_schemas(tmp_path) == {100: {"pid": 100, "name": "Cached"}}


def test_merge_product_schemas_prefers_fetched_schema() -> None:
    """远端 schema 可用时应覆盖缓存，远端失败时调用方仍可保留缓存."""
    merged = merge_product_schemas(
        {100: {"pid": 100, "name": "Cached"}},
        {100: {"pid": 100, "name": "Fetched"}},
    )

    assert merged == {100: {"pid": 100, "name": "Fetched"}}


@pytest.mark.asyncio
async def test_safe_mapping_preserves_redacted_endpoint_error_code() -> None:
    """审计 endpoint 错误应保留安全错误码，不能泄漏服务端 payload 细节."""
    endpoint_errors: dict[str, str] = {}

    async def failing_fetch() -> dict[int, dict]:
        raise CommandError("Open API request failed: code 10401 token-secret")

    assert await safe_mapping("product_schemas", failing_fetch(), endpoint_errors) == {}
    assert endpoint_errors == {"product_schemas": "CommandError code 10401"}
    assert "token-secret" not in str(endpoint_errors)


def test_build_report_includes_topology_entity_coverage() -> None:
    """审计报告必须覆盖灯组/房间/区域/整屋/情景等非设备实体."""
    entry_data = {
        "connection_mode": "private",
        "private_domain": "http://api-dev.yeedev.com",
        "house_id": 200171,
    }
    report = build_report(
        entry={"entry_id": "entry-1", "title": "sample"},
        entry_data=entry_data,
        runtime_data={},
        registry_entries={},
        hydration={},
        endpoint_errors={},
        install_runtime={
            "matched_source": False,
            "changed_files": 1,
            "changed_samples": ["dynamic_entities.py"],
        },
        rooms=[{"id": "room-1", "name": "客厅", "params": {"p": True}}],
        areas=[{"id": "area-1", "name": "一楼", "params": {"p": True}}],
        groups=[{"id": "group-1", "name": "灯组", "params": {"p": True}}],
        houses=[{"id": "house-1", "name": "整屋", "params": {"p": True}}],
        scenes=[{"id": "scene-1", "name": "回家"}],
        analytics_enabled=True,
    )

    summary = report["summary"]
    assert report["install_runtime"] == {
        "matched_source": False,
        "changed_files": 1,
        "changed_samples": ["dynamic_entities.py"],
    }
    assert summary["install_runtime"] == report["install_runtime"]
    assert summary["expected_topology_entities"] == 15
    assert summary["actual_topology_entities"] == 0
    assert summary["missing_topology_entities"] == 15
    assert summary["topology_missing_platforms"] == {
        "button": 1,
        "light": 4,
        "number": 2,
        "select": 3,
        "sensor": 5,
    }
    assert {
        item["source"]: item["missing_total"]
        for item in report["topology_entities"]
    } == {
        "analytics": 5,
        "area": 1,
        "group": 3,
        "house": 4,
        "room": 1,
        "scene": 1,
    }


def test_build_report_entry_context_includes_effective_private_test_push_url() -> None:
    """审计报告应自带私有 push 映射证据，但不能泄露原始 endpoint."""
    report = build_report(
        entry={
            "entry_id": "entry-test",
            "title": "Private Test",
            "options": {"live_updates": False},
        },
        entry_data={
            "connection_mode": "private",
            "private_domain": "http://api-test.yeedev.com",
            "private_push_domain": "",
            "house_id": 200171,
        },
        runtime_data={},
        registry_entries={},
        hydration={},
        endpoint_errors={},
    )

    assert report["entry"] == {
        "entry_id_hash": "8e8aca7f87a48b6d",
        "connection_mode": "private",
        "cloud_region": None,
        "private_endpoint_configured": True,
        "private_push_endpoint_configured": False,
        "effective_push_base_url_hash": "7f1c42c3433105f3",
        "live_updates": False,
        "house_id_hash": "d7cd99b6ec6ce7c7",
    }
    assert not {"house_id", "private_domain", "effective_push_base_url"} & set(report["entry"])


def test_installed_runtime_status_falls_back_to_install_root_when_source_missing(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """容器临时运行审计脚本时，不应因缺源码根误报安装态漂移。"""
    install_root = tmp_path / "custom_components" / "yeelight_pro"
    install_root.mkdir(parents=True)
    monkeypatch.setattr(io_helpers, "SOURCE_COMPONENT_ROOT", tmp_path / "missing")

    status = io_helpers.installed_runtime_status(tmp_path)

    assert status == {
        "matched_source": True,
        "missing_files": 0,
        "extra_files": 0,
        "changed_files": 0,
        "missing_samples": [],
        "extra_samples": [],
        "changed_samples": [],
    }


def test_sensor_candidate_covers_registry_sensor_property_aliases() -> None:
    """审计应识别 sensor component_id 与物模型属性缩写的映射。"""
    keys = _projected_property_keys(
        {},
        [
            SimpleNamespace(platform="sensor", component_id="external_supply_voltage"),
            SimpleNamespace(platform="sensor", component_id="active_power"),
            SimpleNamespace(platform="sensor", component_id="temperature"),
        ],
    )

    assert ("", "esv") in keys
    assert ("", "ap") in keys
    assert ("", "t") in keys
    assert ("", "temp") in keys


def test_internal_temperature_candidate_covers_documented_temp_property() -> None:
    """DALI 内部温度实体代表物模型 temp，审计不应反查成缺口。"""
    keys = _projected_property_keys(
        {},
        [SimpleNamespace(platform="sensor", component_id="internal_temperature")],
    )

    assert ("", "temp") in keys


def test_binary_sensor_candidate_covers_binary_property_aliases() -> None:
    """motion/door/tamper 等实体代表对应二进制属性。"""
    keys = _projected_property_keys(
        {},
        [
            SimpleNamespace(platform="binary_sensor", component_id="motion"),
            SimpleNamespace(platform="binary_sensor", component_id="door"),
            SimpleNamespace(platform="binary_sensor", component_id="tilt_route_calibrated"),
            SimpleNamespace(platform="binary_sensor", component_id="switch_1_slisaon_ready"),
        ],
    )

    assert ("", "mv") in keys
    assert ("", "dc") in keys
    assert ("", "trs") in keys
    assert ("", "slisaon_rdy") in keys


def test_helper_control_candidate_splits_multi_token_property_id() -> None:
    """helper 控件 component_id 中的多段 prop_id 不能被截断。"""
    payload = {
        "ha_product_model": {
            "components": [
                {
                    "component_id": "light",
                    "properties": [{"prop_id": "c_waf"}],
                },
                {
                    "component_id": "other",
                    "properties": [{"prop_id": "mpmp"}],
                },
            ]
        }
    }
    keys = _projected_property_keys(
        payload,
        [
            SimpleNamespace(platform="switch", component_id="other_mpmp_switch"),
            SimpleNamespace(platform="switch", component_id="light_c_waf_switch"),
        ],
    )

    assert ("other", "mpmp") in keys
    assert ("", "mpmp") in keys
    assert ("light", "c_waf") in keys
    assert ("", "c_waf") in keys


def test_event_input_power_property_is_owned_by_event_projection() -> None:
    """情景面板 p/m 属于事件输入状态，不应审计为普通开关缺口。"""
    samples = _unprojected_property_samples(
        [
            {
                "component_category": "scene_panel",
                "component_id": "scene_panel_1",
                "prop_id": "p",
                "access": "read_write",
            },
            {
                "component_category": "knob_switch",
                "component_id": "knob_switch_1",
                "prop_id": "m",
                "access": "read",
            },
        ],
        set(),
    )

    assert samples == []


def test_non_event_input_power_property_still_reports_unprojected() -> None:
    """普通继电器 p 若没被实体覆盖，仍必须暴露为审计缺口。"""
    samples = _unprojected_property_samples(
        [
            {
                "component_category": "relay_switch",
                "component_id": "relay_switch_1",
                "prop_id": "p",
                "access": "read_write",
                "documented": True,
            },
        ],
        set(),
    )

    assert samples == [
        {
            "component_category": "relay_switch",
            "component_id": "relay_switch_1",
            "prop_id": "p",
            "access": "read_write",
            "documented": True,
        }
    ]
