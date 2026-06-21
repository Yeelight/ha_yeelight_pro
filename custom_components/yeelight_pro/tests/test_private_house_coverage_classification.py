"""Private-house coverage conclusion tests."""

from __future__ import annotations

from scripts.private_house_audit.classification import (
    ACTION_FIX_PROJECTION,
    ACTION_INVESTIGATE_SOURCE_DATA,
    ACTION_NO_CODE_CHANGE,
    ACTION_REGISTRY_REFRESH,
    ACTION_SYNC_RUNTIME,
    STATUS_OK,
    STATUS_PROJECTION_GAP,
    STATUS_REGISTRY_STALE,
    STATUS_RUNTIME_DRIFT,
    STATUS_SOURCE_DATA_LIMITED,
    classify_device,
)
from scripts.private_house_audit.classification_rows import classified_device_row


def test_classify_device_marks_unprojected_capability_as_projection_gap() -> None:
    """物模型能力未投影时，应要求修投影而非刷新 registry."""
    result = classify_device({
        "missing_total": 0,
        "unprojected_readable_properties": [{"prop_id": "foo"}],
    })

    assert result["status"] == STATUS_PROJECTION_GAP
    assert result["action"] == ACTION_FIX_PROJECTION


def test_classify_device_marks_missing_expected_entity_as_registry_stale() -> None:
    """当前投影有实体但 HA registry 缺失时，应归类为待刷新."""
    result = classify_device({
        "missing_total": 3,
        "missing_platforms": {"event": 3},
    })

    assert result["status"] == STATUS_REGISTRY_STALE
    assert result["action"] == ACTION_REGISTRY_REFRESH


def test_classify_device_marks_missing_entities_as_runtime_drift_when_install_stale() -> None:
    """安装态代码与源码不一致时，缺失实体应先要求同步/重载 runtime。"""
    result = classify_device(
        {
            "missing_total": 3,
            "missing_platforms": {"event": 3},
        },
        install_runtime_matches_source=False,
    )

    assert result["status"] == STATUS_RUNTIME_DRIFT
    assert result["action"] == ACTION_SYNC_RUNTIME
    assert result["reason"] == "installed_runtime_differs_from_source"


def test_classify_device_marks_extra_registry_entity_as_registry_stale() -> None:
    """HA registry 多出当前投影不存在的实体时，也需要刷新/清理 registry."""
    result = classify_device({
        "actual_total": 3,
        "expected_total": 2,
        "missing_total": 0,
        "extra_total": 1,
        "missing_platforms": {},
    })

    assert result["status"] == STATUS_REGISTRY_STALE
    assert result["action"] == ACTION_REGISTRY_REFRESH


def test_classify_device_marks_platform_changed_registry_stale_reason() -> None:
    """同一逻辑属性从 switch 迁移为 number 时，应给出更精确原因."""
    result = classify_device({
        "actual_total": 5,
        "expected_total": 5,
        "missing_total": 1,
        "extra_total": 1,
        "missing_platforms": {"number": 1},
        "missing_samples": [
            {
                "platform": "number",
                "component_id": "other_mpml_number",
            }
        ],
        "stale_samples": [
            {
                "platform": "switch",
                "component_id": "other_mpml_switch",
            }
        ],
    })

    assert result["status"] == STATUS_REGISTRY_STALE
    assert result["action"] == ACTION_REGISTRY_REFRESH
    assert result["reason"] == "entity_platform_changed"


def test_classify_device_marks_unknown_online_only_as_source_limited() -> None:
    """只有 online/未知品类证据时不能凭空投影控制能力."""
    result = classify_device({
        "actual_total": 1,
        "expected_total": 1,
        "params_count": 1,
        "model_components_count": 0,
        "low_coverage_reasons": [
            "single_or_no_entity",
            "unknown_category",
            "missing_product_model",
            "low_runtime_property_evidence",
        ],
    })

    assert result["status"] == STATUS_SOURCE_DATA_LIMITED
    assert result["action"] == ACTION_INVESTIGATE_SOURCE_DATA


def test_classify_device_marks_undocumented_raw_props_as_source_limited() -> None:
    """有未文档化私有属性但无官方模型时，应精确标记为源数据不足."""
    result = classify_device({
        "actual_total": 1,
        "expected_total": 1,
        "params_count": 1,
        "model_components_count": 0,
        "low_coverage_reasons": [
            "single_or_no_entity",
            "unknown_category",
            "missing_product_model",
            "low_runtime_property_evidence",
        ],
        "source_evidence": {
            "raw_property_count": 4,
            "raw_property_keys": ["amicvol", "ams", "o", "p"],
            "raw_property_value_count": 4,
            "product_model_available": False,
            "product_schema_available": False,
        },
    })

    assert result["status"] == STATUS_SOURCE_DATA_LIMITED
    assert result["action"] == ACTION_INVESTIGATE_SOURCE_DATA
    assert (
        result["reason"]
        == "open_api_payload_has_undocumented_raw_properties_without_supported_model"
    )


def test_classify_device_marks_raw_prop_ids_without_values_as_source_limited() -> None:
    """只有未文档化属性 ID、缺少有效值和模型时，不应误判为投影缺口."""
    result = classify_device({
        "actual_total": 1,
        "expected_total": 1,
        "params_count": 1,
        "model_components_count": 0,
        "low_coverage_reasons": [
            "single_or_no_entity",
            "unknown_category",
            "missing_product_model",
            "low_runtime_property_evidence",
        ],
        "source_evidence": {
            "raw_property_count": 4,
            "raw_property_keys": ["amicvol", "ams", "o", "p"],
            "raw_property_value_count": 1,
            "product_model_available": False,
            "product_schema_available": False,
        },
    })

    assert result["status"] == STATUS_SOURCE_DATA_LIMITED
    assert result["action"] == ACTION_INVESTIGATE_SOURCE_DATA
    assert (
        result["reason"]
        == "open_api_payload_lists_undocumented_property_ids_without_values_or_supported_model"
    )


def test_classify_device_marks_matching_device_ok() -> None:
    """无缺失、无未投影能力、非低证据设备应为 OK."""
    result = classify_device({
        "actual_total": 2,
        "expected_total": 2,
        "missing_total": 0,
        "params_count": 4,
        "model_components_count": 1,
    })

    assert result["status"] == STATUS_OK
    assert result["action"] == ACTION_NO_CODE_CHANGE


def test_classify_device_keeps_complete_minimal_known_device_ok() -> None:
    """已知模型且实体完整时，不应仅因运行时只有 online 值标成源数据不足."""
    result = classify_device({
        "actual_total": 2,
        "expected_total": 2,
        "missing_total": 0,
        "params_count": 1,
        "model_components_count": 1,
        "low_coverage_reasons": ["low_runtime_property_evidence"],
    })

    assert result["status"] == STATUS_OK
    assert result["action"] == ACTION_NO_CODE_CHANGE


def test_classify_device_marks_writable_model_without_control_as_source_limited() -> None:
    """物模型有可写属性但无主控制桶时，应显式要求复核源数据/投影。"""
    result = classify_device({
        "category": "light_sensor",
        "actual_total": 3,
        "expected_total": 3,
        "missing_total": 0,
        "params_count": 3,
        "model_components_count": 1,
        "model_writable_properties_count": 3,
        "expected_roles": {"diagnostic": 1, "event": 1, "config": 1},
        "actual_roles": {"diagnostic": 1, "event": 1, "config": 1},
        "expected_platforms": {"binary_sensor": 1, "event": 1, "sensor": 1},
        "actual_platforms": {"binary_sensor": 1, "event": 1, "sensor": 1},
    })

    assert result["status"] == STATUS_SOURCE_DATA_LIMITED
    assert result["action"] == ACTION_INVESTIGATE_SOURCE_DATA
    assert result["reason"] == "writable_model_properties_without_strict_control_projection"


def test_classify_device_keeps_scene_panel_event_inputs_ok_without_primary_control() -> None:
    """情景面板的 p/m 是事件输入语义，不应要求普通主控制实体。"""
    result = classify_device({
        "category": "scene_panel",
        "actual_total": 5,
        "expected_total": 5,
        "missing_total": 0,
        "params_count": 1,
        "model_components_count": 4,
        "model_writable_properties_count": 4,
        "expected_roles": {"diagnostic": 1, "event": 4},
        "actual_roles": {"diagnostic": 1, "event": 4},
        "actual_platforms": {"event": 4, "sensor": 1},
        "expected_platforms": {"event": 4, "sensor": 1},
    })

    assert result["status"] == STATUS_OK
    assert result["action"] == ACTION_NO_CODE_CHANGE


def test_classify_device_keeps_event_subdevices_ok_without_strict_control() -> None:
    """含情景按键子设备的复合传感器应以事件覆盖，不要求普通控制。"""
    result = classify_device({
        "category": "human_sensor",
        "actual_total": 8,
        "expected_total": 8,
        "missing_total": 0,
        "params_count": 1,
        "model_components_count": 7,
        "model_writable_properties_count": 6,
        "expected_roles": {"diagnostic": 1, "event": 6, "primary_control_or_state": 1},
        "actual_roles": {"diagnostic": 1, "event": 6, "primary_control_or_state": 1},
        "actual_platforms": {"binary_sensor": 1, "event": 6, "sensor": 1},
        "expected_platforms": {"binary_sensor": 1, "event": 6, "sensor": 1},
        "source_evidence": {
            "subdevice_property_count": 6,
            "subdevice_property_keys": ["1-p", "2-p", "3-p"],
        },
    })

    assert result["status"] == STATUS_OK
    assert result["action"] == ACTION_NO_CODE_CHANGE


def test_classify_device_keeps_gateway_metadata_ok_without_primary_control() -> None:
    """网关是拓扑/注册上下文，配置类可写属性不代表普通主控制缺失。"""
    result = classify_device({
        "category": "gateway",
        "actual_total": 1,
        "expected_total": 1,
        "missing_total": 0,
        "params_count": 1,
        "model_components_count": 3,
        "model_writable_properties_count": 14,
        "expected_roles": {"diagnostic": 1},
        "actual_roles": {"diagnostic": 1},
        "actual_platforms": {"sensor": 1},
        "expected_platforms": {"sensor": 1},
        "low_coverage_reasons": ["single_or_no_entity", "low_runtime_property_evidence"],
    })

    assert result["status"] == STATUS_OK
    assert result["action"] == ACTION_NO_CODE_CHANGE


def test_classify_device_keeps_config_only_controls_ok_without_primary_control() -> None:
    """音乐等配置组件已完整投影为 config 控件时，不应继续要求主控制。"""
    result = classify_device({
        "category": "other",
        "actual_total": 5,
        "expected_total": 5,
        "missing_total": 0,
        "params_count": 0,
        "model_components_count": 1,
        "model_writable_properties_count": 4,
        "expected_roles": {"diagnostic": 1, "config": 4},
        "actual_roles": {"diagnostic": 1, "config": 4},
        "actual_platforms": {"number": 2, "sensor": 1, "switch": 2},
        "expected_platforms": {"number": 2, "sensor": 1, "switch": 2},
    })

    assert result["status"] == STATUS_OK
    assert result["action"] == ACTION_NO_CODE_CHANGE


def test_classified_row_marks_control_bucket_needs_review_for_writable_model() -> None:
    """逐设备 coverage view 应把可写模型但无主控制显式标红。"""
    row = classified_device_row(
        {
            "category": "light_sensor",
            "actual_total": 3,
            "expected_total": 3,
            "missing_total": 0,
            "params_count": 3,
            "model_components_count": 1,
            "model_writable_properties_count": 3,
            "expected_roles": {"diagnostic": 1, "event": 1, "config": 1},
            "actual_roles": {"diagnostic": 1, "event": 1, "config": 1},
            "expected_platforms": {"binary_sensor": 1, "event": 1, "sensor": 1},
            "actual_platforms": {"binary_sensor": 1, "event": 1, "sensor": 1},
        },
        {
            "status": STATUS_SOURCE_DATA_LIMITED,
            "action": ACTION_INVESTIGATE_SOURCE_DATA,
            "reason": "writable_model_properties_without_strict_control_projection",
        },
    )

    assert row["coverage_view"]["control"] == {
        "expected": 0,
        "actual": 0,
        "missing": 0,
        "status": "needs_review",
        "attention": "model_has_writable_properties_but_no_strict_control",
    }
    assert row["strict_control"] == {
        "expected": 0,
        "actual": 0,
        "missing": 0,
        "absence_reason": "writable_model_properties_without_strict_control",
    }
