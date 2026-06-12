"""HA platform mapping contract regressions."""

from __future__ import annotations

from custom_components.yeelight_pro.capabilities.platform_contract import (
    platform_candidates_for_payload,
    platform_contracts,
    primary_platform_for_payload,
)


def test_platform_mapping_contract_covers_supported_and_blocked_platforms() -> None:
    """首版 HA 平台矩阵必须说明支持、诊断或不支持原因."""
    by_platform = {item.platform: item for item in platform_contracts()}

    for platform in (
        "light",
        "binary_sensor",
        "sensor",
        "event",
        "cover",
        "climate",
        "switch",
        "button",
        "select",
        "number",
    ):
        assert by_platform[platform].status == "supported"
        assert by_platform[platform].evidence
    assert by_platform["fan"].status == "supported"
    assert by_platform["lock"].status == "unsupported"
    assert "door-lock" in by_platform["lock"].evidence
    assert by_platform["vacuum"].status == "unsupported"
    assert by_platform["scene"].status == "unsupported"
    assert "scene execution" in by_platform["scene"].evidence
    assert by_platform["text"].status == "unsupported"
    assert "writable text" in by_platform["text"].evidence


def test_platform_mapping_contract_has_evidence_for_every_known_platform() -> None:
    """每个已知 HA 平台都必须有明确证据，不能仅靠默认遗漏."""
    by_platform = {item.platform: item for item in platform_contracts()}

    for platform, contract in by_platform.items():
        assert contract.evidence, platform
    assert by_platform["camera"].status == "unsupported"
    assert by_platform["camera"].evidence
    assert by_platform["remote"].status == "unsupported"
    assert "rmt/acrc" in by_platform["remote"].evidence
    assert by_platform["siren"].status == "unsupported"
    assert "blink" in by_platform["siren"].evidence


def test_broad_cloud_light_sensor_payload_maps_to_sensor_only() -> None:
    """云端粗 light 品类遇到只读传感属性时不能候选 light."""
    payload = {
        "name": "客厅温湿度传感器",
        "category": "other",
        "type": "light",
        "params": {"t": 25, "h": 58, "bl": 87},
    }

    assert primary_platform_for_payload(payload) == "sensor"
    assert platform_candidates_for_payload(payload) == ("sensor",)


def test_registry_safe_read_only_properties_project_sensor_candidates() -> None:
    """平台候选应覆盖 projector 已支持的官方安全只读 sensor 属性."""
    payload = {
        "category": "other",
        "params": {"fv": "1.2.80", "ch_num": 4},
    }

    assert primary_platform_for_payload(payload) == "sensor"
    assert platform_candidates_for_payload(payload) == ("sensor",)


def test_other_category_has_no_default_platform_without_property_evidence() -> None:
    """other 是易来兜底大类，不应默认等同 HA sensor 平台。"""
    assert primary_platform_for_payload({"category": "other"}) is None
    assert platform_candidates_for_payload({"category": "other"}) == ()


def test_category_without_capability_evidence_does_not_project_platform() -> None:
    """category 只能做设备大类兜底，不能在无能力证据时生成实体平台。"""
    for category in (
        "contact_sensor",
        "curtain",
        "human_sensor",
        "knob_switch",
        "light_sensor",
        "scene_panel",
        "temp_control",
    ):
        payload: dict[str, object] = {"category": category, "params": {}}

        assert primary_platform_for_payload(payload) is None
        assert platform_candidates_for_payload(payload) == ()


def test_broad_cloud_light_contact_payload_maps_to_binary_and_sensor() -> None:
    """门磁只读布尔和电量应映射 binary_sensor + sensor，不产生 light."""
    payload = {
        "name": "玄关门磁传感器",
        "category": "contact_sensor",
        "type": "light",
        "params": {"dc": False, "alm": True, "bl": 75},
    }

    assert primary_platform_for_payload(payload) == "binary_sensor"
    assert platform_candidates_for_payload(payload) == (
        "binary_sensor",
        "sensor",
    )


def test_category_is_only_last_resort_when_properties_exist() -> None:
    """有属性证据时不能先按 category 添加缺证据的平台。"""
    payload = {
        "category": "contact_sensor",
        "params": {"bl": 75},
    }

    assert primary_platform_for_payload(payload) == "sensor"
    assert platform_candidates_for_payload(payload) == ("sensor",)


def test_light_category_power_only_does_not_hide_missing_light_capability() -> None:
    """仅 category=light + p 不能生造灯；缺亮度/色温/颜色能力应暴露出来."""
    payload = {
        "category": "light",
        "params": {"p": True},
    }

    assert primary_platform_for_payload(payload) is None
    assert platform_candidates_for_payload(payload) == ()


def test_relay_switch_category_power_only_does_not_hide_missing_switch_identity() -> None:
    """仅 category=relay_switch + p 不能生造开关；需 sp/slisaon 等开关身份能力."""
    payload = {
        "category": "relay_switch",
        "params": {"p": True},
    }

    assert primary_platform_for_payload(payload) is None
    assert platform_candidates_for_payload(payload) == ()


def test_switch_identity_property_projects_switch_without_category_first() -> None:
    """开关身份属性是强证据，不需要先依赖 category 兜底."""
    payload = {
        "category": "other",
        "params": {"sp": True},
    }

    assert primary_platform_for_payload(payload) == "switch"
    assert platform_candidates_for_payload(payload) == ("switch",)


def test_documented_event_payload_adds_event_candidate() -> None:
    """schema/event 数据应进入 event 候选，供 event entity 和 device trigger 消费."""
    payload = {
        "category": "human_sensor",
        "params": {"mv": True, "luminance": 120},
        "events": [{"id": 8, "name": "motion.true"}],
    }

    assert platform_candidates_for_payload(payload) == (
        "binary_sensor",
        "sensor",
        "event",
    )


def test_event_only_payload_does_not_use_broad_light_fallback() -> None:
    """只有事件能力时不能凭云端粗 light 生成 light 候选。"""
    payload = {
        "category": "other",
        "type": "light",
        "events": [
            {"id": 14, "name": "power.alarm"},
            {"id": 15, "name": "power.normal"},
        ],
    }

    assert primary_platform_for_payload(payload) == "event"
    assert platform_candidates_for_payload(payload) == ("event",)


def test_light_sensor_category_does_not_override_motion_capability_order() -> None:
    """mv+luminance 同时生成二元传感和照度传感，不再让 category 抢主平台."""
    payload = {
        "category": "light_sensor",
        "params": {"mv": True, "luminance": 120, "bl": 87},
    }

    assert primary_platform_for_payload(payload) == "binary_sensor"
    assert platform_candidates_for_payload(payload) == (
        "binary_sensor",
        "sensor",
    )


def test_component_category_can_order_capability_candidates() -> None:
    """结构化组件 category 是能力证据，可排序但不额外生造平台."""
    payload = {
        "category": "light",
        "subDeviceList": [
            {
                "index": 1,
                "category": "light_sensor",
                "properties": [
                    {"propId": "mv", "value": True},
                    {"propId": "luminance", "value": 120},
                    {"propId": "bl", "value": 87},
                ],
            }
        ],
    }

    assert primary_platform_for_payload(payload) == "sensor"
    assert platform_candidates_for_payload(payload) == (
        "sensor",
        "binary_sensor",
    )


def test_unknown_openapi_property_metadata_does_not_project_helper_candidates() -> None:
    """未知 OpenAPI 属性不能只凭 valueList/valueRange 泛化成 HA 控件。"""
    payload = {
        "category": "light",
        "properties": [
            {
                "propId": "vendor_mode",
                "format": "uint8",
                "value": 1,
                "valueList": [
                    {"code": 1, "desc": "Auto"},
                    {"code": 2, "desc": "Manual"},
                ],
                "operators": ["set"],
            },
            {
                "propId": "vendor_level",
                "format": "uint8",
                "value": 50,
                "valueRange": {"min": 1, "max": 100, "step": 1},
                "access": 7,
            },
        ],
    }

    assert platform_candidates_for_payload(payload) == ()


def test_registry_backed_openapi_property_metadata_projects_helper_candidates() -> None:
    """官方物模型属性的枚举/数值范围仍应生成 select/number 辅助候选。"""
    payload = {
        "category": "light",
        "properties": [
            {
                "propId": "bp",
                "format": "uint8",
                "value": "1",
                "operators": ["set"],
            },
            {
                "propId": "dd",
                "format": "uint16",
                "value": 2000,
                "access": 7,
            },
        ],
    }

    assert platform_candidates_for_payload(payload) == ("select", "number")


def test_property_evidence_merges_params_and_openapi_property_metadata() -> None:
    """同一属性来自 params 与 properties 时必须合并官方写入元数据。"""
    payload = {
        "category": "light",
        "params": {"1-bp": "1"},
        "properties": [
            {
                "propId": "bp",
                "format": "uint8",
                "value": "1",
                "operators": ["set"],
            },
        ],
    }

    assert platform_candidates_for_payload(payload) == ("select",)


def test_acrc_config_property_does_not_claim_remote_platform() -> None:
    """空调遥控器使能是配置开关，不代表已有 HA remote/climate 命令集。"""
    payload = {
        "category": "temp_control",
        "properties": [
            {
                "propId": "acrc",
                "format": "bool",
                "value": True,
                "access": 7,
            }
        ],
    }

    assert "remote" not in platform_candidates_for_payload(payload)
    assert "climate" not in platform_candidates_for_payload(payload)
    assert platform_candidates_for_payload(payload) == ("switch",)


def test_temp_control_category_keeps_climate_primary_with_telemetry() -> None:
    """温控设备的温湿度/在线等遥测不能把主平台抢成 sensor/binary_sensor."""
    payload = {
        "category": "temp_control",
        "params": {"p": True, "t": 25, "h": 58, "tgt": 28, "o": True},
    }

    assert primary_platform_for_payload(payload) == "climate"
    assert platform_candidates_for_payload(payload) == (
        "climate",
        "sensor",
    )


def test_fresh_air_properties_project_fan_without_climate_or_number() -> None:
    """新风 vmcp/vmcf 属于温控大类下的 fan 能力，不能降级为 climate/number."""
    payload = {
        "category": "temp_control",
        "properties": [
            {"propId": "vmcp", "format": "boolean", "value": True, "operators": ["set"]},
            {
                "propId": "vmcf",
                "format": "uint8",
                "value": 30,
                "valueRange": {"min": 1, "max": 100, "step": 1},
                "operators": ["set"],
            },
        ],
    }

    assert primary_platform_for_payload(payload) == "fan"
    assert platform_candidates_for_payload(payload) == ("fan",)
