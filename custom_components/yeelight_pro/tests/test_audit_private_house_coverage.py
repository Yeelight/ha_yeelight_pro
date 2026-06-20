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
from scripts.private_house_audit.inventory import property_inventory
from scripts.private_house_audit.projection import (
    runtime_property_keys,
    schema_gap_reason,
)
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
        {"100": {"pid": 100, "name": "Fetched"}},
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
    """审计报告应自带私有部署 API 到 WebSocket endpoint 的有效映射证据。"""
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
        "entry_id": "entry-test",
        "title": "Private Test",
        "connection_mode": "private",
        "cloud_region": None,
        "private_domain": "http://api-test.yeedev.com",
        "private_push_domain": "",
        "effective_push_base_url": "ws://192.168.0.89:7779/ws",
        "live_updates": False,
        "house_id_hash": "d7cd99b6ec6ce7c7",
    }
    assert "house_id" not in report["entry"]


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


def test_unprojected_samples_ignore_undocumented_runtime_model_only_props() -> None:
    """非 docs/iot 且非真实 schema 的兼容字段不应制造审计缺口。"""
    samples = _unprojected_property_samples(
        [
            {
                "component_category": "fan",
                "component_id": "fan_1",
                "prop_id": "lv",
                "access": "read_write",
                "documented": False,
                "schema_property": False,
            },
            {
                "component_category": "fan",
                "component_id": "fan_1",
                "prop_id": "dir",
                "access": "read_write",
                "documented": False,
                "schema_property": False,
            },
        ],
        set(),
    )

    assert samples == []


def test_unprojected_samples_keep_documented_music_control_props() -> None:
    """官方音乐组件属性仍应进入审计，避免把真实缺口过滤掉。"""
    samples = _unprojected_property_samples(
        [
            {
                "component_category": "music control",
                "component_id": "music_control_1",
                "prop_id": "mpmp",
                "access": "read_write",
                "documented": True,
                "schema_property": False,
            },
        ],
        set(),
    )

    assert samples == [
        {
            "component_category": "music control",
            "component_id": "music_control_1",
            "prop_id": "mpmp",
            "access": "read_write",
            "documented": True,
            "schema_property": False,
        }
    ]


def test_unprojected_samples_ignore_config_props_without_ha_control_shape() -> None:
    """无 range/list/capability 的配置类 int/json 字段不应强制实体化。"""
    samples = _unprojected_property_samples(
        [
            {
                "component_category": "music control",
                "component_id": "music_control_1",
                "prop_id": "mppm",
                "access": "read_write",
                "documented": True,
                "schema_property": False,
                "type": "config",
            },
            {
                "component_category": "gateway",
                "component_id": "gateway",
                "prop_id": "plugins",
                "access": "read_write",
                "documented": True,
                "schema_property": False,
                "type": "config",
            },
        ],
        set(),
        runtime_keys=frozenset({("", "mppm"), ("", "plugins")}),
    )

    assert samples == []


def test_unprojected_samples_ignore_gateway_config_props_without_runtime_shape() -> None:
    """网关保留配置项即使是 bool，也不应被审计为必须投影。"""
    samples = _unprojected_property_samples(
        [
            {
                "component_category": "gateway",
                "component_id": "gateway",
                "prop_id": "sonos_mgr",
                "access": "read_write",
                "documented": True,
                "schema_property": False,
                "type": "config",
            },
        ],
        set(),
        runtime_keys=frozenset({("", "sonos_mgr")}),
    )

    assert samples == []


def test_unprojected_samples_ignore_basic_metadata_without_runtime_state() -> None:
    """基础/全局元数据只来自产品目录时，不应被判成实体投影缺口。"""
    samples = _unprojected_property_samples(
        [
            {
                "component_category": "",
                "component_id": "basic",
                "prop_id": "dev_alarm",
                "access": "read_write",
                "documented": True,
                "schema_property": False,
                "type": "config",
            },
            {
                "component_category": "",
                "component_id": "basic",
                "prop_id": "fv",
                "access": "read",
                "documented": True,
                "schema_property": False,
                "type": "config",
            },
            {
                "component_category": "gateway",
                "component_id": "gateway",
                "prop_id": "li",
                "access": "read_write",
                "documented": True,
                "schema_property": False,
                "type": "config",
            },
        ],
        set(),
    )

    assert samples == []


def test_unprojected_samples_keep_runtime_backed_gateway_config_props() -> None:
    """网关运行态已返回 li/lc 时，审计仍应要求对应实体或配置覆盖。"""
    samples = _unprojected_property_samples(
        [
            {
                "component_category": "gateway",
                "component_id": "gateway",
                "prop_id": "li",
                "access": "read_write",
                "documented": True,
                "schema_property": False,
                "type": "config",
            },
            {
                "component_category": "gateway",
                "component_id": "gateway",
                "prop_id": "lc",
                "access": "read_write",
                "documented": True,
                "schema_property": False,
                "type": "config",
            },
        ],
        set(),
        runtime_keys=frozenset({("", "li"), ("", "lc")}),
    )

    assert [item["prop_id"] for item in samples] == ["li", "lc"]


def test_runtime_property_keys_reads_flat_rows_subdevices_and_canonical_state() -> None:
    """审计运行态证据应覆盖 params、原始属性、子设备和 canonical state。"""
    keys = runtime_property_keys({
        "params": {"2-p": 1, "o": True},
        "properties": [{"propId": "li"}],
        "subDeviceList": [
            {"index": 3, "properties": [{"propId": "lc"}]},
        ],
        "ha_device_instance": {
            "components": [
                {
                    "component_id": "gateway",
                    "state": {"cpt": 3},
                }
            ]
        },
    })

    assert ("2", "p") in keys
    assert ("", "p") in keys
    assert ("", "o") in keys
    assert ("", "li") in keys
    assert ("3", "lc") in keys
    assert ("gateway", "cpt") in keys


def test_property_inventory_marks_schema_and_documented_boundaries() -> None:
    """inventory 需标记属性来源，供审计区分真实缺口和兼容噪声。"""
    inventory = property_inventory({
        "product_schema": {
            "components": [
                {
                    "component_id": "vendor_component",
                    "properties": [{"prop_id": "vendor_only"}],
                }
            ]
        },
        "ha_product_model": {
            "components": [
                {
                    "component_id": "music_control_1",
                    "category": "music control",
                    "properties": [{"prop_id": "mppm", "access": "read_write"}],
                },
                {
                    "component_id": "vendor_component",
                    "category": "other",
                    "properties": [{"prop_id": "vendor_only", "access": "read"}],
                },
                {
                    "component_id": "compat_fan",
                    "category": "fan",
                    "properties": [{"prop_id": "lv", "access": "read_write"}],
                },
            ]
        },
    })

    by_prop = {
        item["prop_id"]: item for item in inventory["readable_properties"]
    }

    assert by_prop["mppm"]["documented"] is True
    assert by_prop["mppm"]["schema_property"] is False
    assert by_prop["vendor_only"]["documented"] is False
    assert by_prop["vendor_only"]["schema_property"] is True
    assert by_prop["lv"]["documented"] is False
    assert by_prop["lv"]["schema_property"] is False


def test_build_report_does_not_shadow_property_inventory_function() -> None:
    """审计报告构造不应因 property_inventory 局部变量遮蔽函数而中断。"""
    report = build_report(
        entry={"entry_id": "entry-1", "title": "Private"},
        entry_data={"connection_mode": "private", "house_id": 1},
        runtime_data={
            1001: {
                "id": 1001,
                "name": "Test Light",
                "category": "light",
                "type": "light",
                "params": {"p": 1},
                "ha_product_model": {
                    "components": [
                        {
                            "component_id": "light",
                            "category": "light",
                            "properties": [
                                {"prop_id": "p", "access": "read_write"}
                            ],
                        }
                    ]
                },
            }
        },
        registry_entries={},
        hydration={},
        endpoint_errors={},
    )

    assert report["summary"]["device_count"] == 1
    assert report["devices"][0]["model_properties_count"] == 1


def test_build_report_includes_redacted_source_evidence() -> None:
    """审计报告应保留源侧属性证据，但不输出属性值。"""
    report = build_report(
        entry={"entry_id": "entry-1", "title": "Private"},
        entry_data={"connection_mode": "private", "house_id": 1},
        runtime_data={
            1001: {
                "id": 1001,
                "name": "Unknown Lamp",
                "category": "unknown",
                "properties": [
                    {"propId": "o", "value": True},
                    {"propId": "secret_prop", "value": "secret-value"},
                ],
                "subDeviceList": [
                    {
                        "index": 2,
                        "properties": [{"propId": "p", "value": 1}],
                    }
                ],
                "params": {"o": True, "secret_prop": "secret-value", "2-p": 1},
            }
        },
        registry_entries={},
        hydration={},
        endpoint_errors={},
    )

    evidence = report["devices"][0]["source_evidence"]

    assert evidence["raw_property_count"] == 2
    assert evidence["raw_property_keys"] == ["o", "secret_prop"]
    assert evidence["subdevice_count"] == 1
    assert evidence["subdevice_property_keys"] == ["2-p"]
    assert "secret-value" not in str(evidence)


def test_schema_gap_reason_accepts_runtime_inferred_product_model() -> None:
    """已有运行时/目录推断模型时，不应把缺官方 schema 误报为 missing_pid."""
    assert (
        schema_gap_reason({
            "ha_product_model": {
                "components": [
                    {
                        "component_id": "switch_1",
                        "category": "relay_switch",
                    }
                ]
            }
        })
        is None
    )
    assert schema_gap_reason({}) == "missing_pid"
