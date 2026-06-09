"""Yeelight spec correction rule tests."""

from __future__ import annotations

from custom_components.yeelight_pro.capabilities.spec_correction import (
    correct_property_schema,
    derive_component_capabilities,
    normalize_component_type,
    normalize_property_access,
    normalize_property_format,
    normalize_property_operators,
    normalize_source_property_type,
    summarize_product_schema_corrections,
)


def test_correction_normalizes_format_and_access_from_operators() -> None:
    """属性格式和访问级别应按公开 schema 字段规范化."""
    correction = correct_property_schema(
        {"type": 0, "category": "light"},
        {"propId": "p", "format": "bool", "operators": ["set", "toggle"]},
        property_type="apply",
    )

    assert correction.kind == "control"
    assert correction.property_type == "apply"
    assert correction.format == "boolean"
    assert correction.access == "read_write"
    assert correction.runtime_filtered is False


def test_correction_keeps_read_only_access_for_legacy_numeric_access() -> None:
    """旧 access=4 语义应继续表示只读状态属性."""
    correction = correct_property_schema(
        {"type": 0, "category": "sensor"},
        {"propId": "luminance", "format": "uint32", "access": 4},
        property_type="apply",
    )

    assert correction.kind == "state"
    assert correction.access == "read_only"
    assert correction.format == "uint32"


def test_correction_normalizes_documented_numeric_access_bits() -> None:
    """公开 Open API 示例中的 access=7/5 应分别表示可写和只读."""
    writable = correct_property_schema(
        {"type": 0, "category": "light"},
        {"propId": "ct", "format": "uint8", "access": 7},
        property_type="apply",
    )
    readonly = correct_property_schema(
        {"type": 0, "category": "light_sensor"},
        {"propId": "luminance", "format": "uint32", "access": 5},
        property_type="apply",
    )

    assert writable.kind == "control"
    assert writable.access == "read_write"
    assert readonly.kind == "state"
    assert readonly.access == "read_only"


def test_correction_marks_global_and_config_properties_runtime_filtered() -> None:
    """全局/配置/信息类属性不能进入普通实体运行时状态."""
    global_correction = correct_property_schema(
        {"type": 1, "name": "basic"},
        {"propId": "name", "format": "string", "operators": ["set"]},
        property_type="apply",
    )
    config_correction = correct_property_schema(
        {"type": 0, "category": "light"},
        {"propId": "cfg", "format": "uint8", "operators": ["set"]},
        property_type="config",
    )

    assert global_correction.kind == "info"
    assert global_correction.runtime_filtered is True
    assert config_correction.kind == "config"
    assert config_correction.runtime_filtered is True


def test_correction_filters_known_sensitive_properties_without_type_hint() -> None:
    """本地 IoT 资料中的凭据类属性缺少 type hint 时也必须过滤."""
    for prop_id in ("localToken", "hrbk", "deviceKey"):
        correction = correct_property_schema(
            {"type": 0, "category": "gateway"},
            {"propId": prop_id, "format": "string", "operators": ["set"]},
            property_type=None,
        )

        assert correction.kind == "config"
        assert correction.runtime_filtered is True
        assert correction.access == "read_write"


def test_standalone_normalizers_are_conservative() -> None:
    """独立 normalizer 只做确定性修正，不猜测缺失元数据."""
    assert normalize_property_format(None) is None
    assert normalize_property_format("BoOl") == "boolean"
    assert normalize_property_access("read_write", []) == "read_write"
    assert normalize_property_access("读, 写", []) == "read_write"
    assert normalize_property_access("读", []) == "read_only"
    assert normalize_property_access("7", []) == "read_write"
    assert normalize_property_access(5, []) == "read_only"
    assert normalize_property_access(None, []) == "read_only"
    assert normalize_property_operators(" set, toggle / adjust ") == [
        "set",
        "toggle",
        "adjust",
    ]
    assert normalize_property_operators(
        [{"name": "SET"}, {"operator": "toggle"}, {"op": "adjust"}]
    ) == ["set", "toggle", "adjust"]
    assert normalize_component_type(0) == "custom"
    assert normalize_component_type("1") == "global"
    assert normalize_component_type(1) == "global"
    assert normalize_source_property_type(0) == "apply"
    assert normalize_source_property_type("配置类") == "config"
    assert normalize_source_property_type(1) == "config"


def test_capability_derivation_skips_filtered_properties() -> None:
    """能力派生只保留可控制属性和动作."""
    capabilities = derive_component_capabilities(
        {
            "type": 0,
            "category": "light",
            "properties": [
                {"propId": "p", "operators": [{"name": "set"}]},
                {"propId": "name", "operators": ["set"]},
                {"propId": "luminance"},
            ],
            "supportActions": [{"actionName": "toggle"}],
        }
    )

    assert capabilities == ["light", "light.p", "toggle"]


def test_product_schema_correction_summary_is_aggregate_only() -> None:
    """schema correction summary 只返回聚合计数."""
    summary = summarize_product_schema_corrections(
        {
            "components": [
                {
                    "type": 1,
                    "name": "basic",
                    "properties": [
                        {"propId": "name", "format": "string", "operators": ["set"]},
                    ],
                },
                {
                    "type": 0,
                    "category": "light",
                    "properties": [
                        {"propId": "p", "format": "bool", "operators": ["toggle"]},
                        {"propId": "cfg", "type": 1, "operators": ["set"]},
                        {"propId": "luminance", "access": 4},
                    ],
                },
            ],
            "customComponents": [
                {
                    "type": 0,
                    "category": "relay_switch",
                    "properties": [{"propId": "p", "operators": ["set"]}],
                }
            ],
        }
    )

    assert summary == {
        "components_seen": 3,
        "properties_seen": 5,
        "runtime_filtered_properties": 2,
        "normalized_format_properties": 1,
        "writable_properties": 2,
        "readonly_properties": 1,
    }
