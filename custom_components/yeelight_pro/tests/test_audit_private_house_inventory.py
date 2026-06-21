"""Private-house audit inventory and projection boundary tests."""

from __future__ import annotations

from scripts.audit_private_house_coverage import (
    _unprojected_property_samples,
)
from scripts.private_house_audit.inventory import property_inventory
from scripts.private_house_audit.projection import (
    runtime_property_keys,
    schema_gap_reason,
)
from scripts.private_house_audit.report import build_report

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
