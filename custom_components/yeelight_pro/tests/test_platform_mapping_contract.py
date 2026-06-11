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


def test_openapi_property_access_projects_select_and_number_candidates() -> None:
    """OpenAPI access/operators/valueRange/valueList 应生成合理 HA 候选."""
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

    assert platform_candidates_for_payload(payload) == ("select", "number")


def test_acrc_config_property_does_not_claim_remote_platform() -> None:
    """空调遥控器使能是配置开关，不代表已有 HA remote 命令集。"""
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
    assert platform_candidates_for_payload(payload) == ("climate",)
