"""Runtime payload tests for devices whose current values are missing."""

from __future__ import annotations

from custom_components.yeelight_pro.core.device_payload import DevicePayloadBuilder
from custom_components.yeelight_pro.entity_candidates import iter_device_entity_candidates


def test_runtime_payloads_keep_empty_control_category_metadata_only() -> None:
    """粗可控品类无属性或组件证据时只保留设备元数据。"""
    builder = DevicePayloadBuilder()

    data, _gateways = builder.build_runtime_payloads(
        devices=[
            {
                "id": 304784336,
                "name": "墙壁开关1",
                "category": "relay_switch",
                "pid": 201,
                "roomId": 397,
                "properties": [],
            }
        ],
        gateways=[],
        product_schemas={},
        apply_runtime_overrides=lambda payload: payload,
        rooms=[{"id": "397", "name": "客厅"}],
    )

    device = data[304784336]
    device_info = device["device_info"]
    candidates = list(iter_device_entity_candidates(device))
    product_model = device["ha_product_model"]
    device_instance = device["ha_device_instance"]

    assert product_model["schema_version"] == "runtime-v1"
    assert product_model["product"]["category"] == "relay_switch"
    assert product_model["product"]["categories"] == ["relay_switch"]
    assert product_model["components"] == []
    assert device_instance["components"] == []
    assert "ha_platform" not in device
    assert "ha_platform_candidates" not in device
    assert device["name"] == "墙壁开关1"
    assert device["model_id"] == "YL-201"
    assert device["room_name"] == "客厅"
    assert device_info["name"] == "墙壁开关1"
    assert device_info["model"] == "继电器开关"
    assert device_info["suggested_area"] == "客厅"
    assert device_info["identifiers"] == [
        ["yeelight_pro", "304784336"],
        ["yeelight_pro", "device:304784336"],
    ]
    assert candidates == []


def test_runtime_payloads_keep_sensor_category_metadata_without_values() -> None:
    """明确传感器品类暂缺值时只保留元数据，不生成假实体能力。"""
    builder = DevicePayloadBuilder()

    data, _gateways = builder.build_runtime_payloads(
        devices=[
            {
                "id": 501,
                "name": "客厅人体传感器",
                "category": "human_sensor",
                "pid": 5010,
                "roomId": 1,
                "properties": [],
            },
            {
                "id": 502,
                "name": "主卧温湿度传感器",
                "category": "sensor",
                "pid": 5020,
                "roomId": 2,
                "properties": [],
            },
        ],
        gateways=[],
        product_schemas={},
        apply_runtime_overrides=lambda payload: payload,
        rooms=[{"id": "1", "name": "客厅"}, {"id": "2", "name": "主卧"}],
    )

    human_candidates = list(iter_device_entity_candidates(data[501]))
    temp_candidates = list(iter_device_entity_candidates(data[502]))

    assert data[501]["iot_category"] == "human_sensor"
    assert "iot_category" not in data[502]
    assert human_candidates == []
    assert temp_candidates == []


def test_runtime_payloads_do_not_project_named_temperature_humidity_without_values() -> None:
    """云端粗 light 且无细分证据时，不凭名称或大类生成实体。"""
    builder = DevicePayloadBuilder()

    data, _gateways = builder.build_runtime_payloads(
        devices=[
            {
                "id": 503,
                "name": "客厅温湿度传感器",
                "category": "light",
                "pid": 5030,
                "roomId": 1,
                "properties": [],
            }
        ],
        gateways=[],
        product_schemas={},
        apply_runtime_overrides=lambda payload: payload,
        rooms=[{"id": "1", "name": "客厅"}],
    )

    device = data[503]
    candidates = list(iter_device_entity_candidates(device))

    assert device["iot_category"] == "light"
    assert "ha_platform" not in device
    assert "ha_platform_candidates" not in device
    assert candidates == []


def test_runtime_payloads_do_not_use_conflicting_switch_schema_for_curtain() -> None:
    """名称和属性已证明是窗帘时，不能继续使用错误开关 schema 生成 switch."""
    builder = DevicePayloadBuilder()

    data, _gateways = builder.build_runtime_payloads(
        devices=[
            {
                "id": 601,
                "name": "客厅窗帘电机",
                "category": "relay_switch",
                "pid": 6001,
                "properties": [
                    {"propId": "cp", "value": 40},
                    {"propId": "tp", "value": 90},
                ],
            }
        ],
        gateways=[],
        product_schemas={6001: _relay_switch_schema(6001)},
        apply_runtime_overrides=lambda payload: payload,
    )

    device = data[601]
    candidates = {(item.platform, item.component_id) for item in iter_device_entity_candidates(device)}

    assert device["iot_category"] == "curtain"
    assert device["ha_product_model"]["schema_version"] == "runtime-v1"
    assert candidates == {("cover", "curtain")}


def test_runtime_payloads_keep_empty_cover_and_climate_metadata_only() -> None:
    """明确窗帘/温控品类无当前值时只保留设备元数据，不生成假实体."""
    builder = DevicePayloadBuilder()

    data, _gateways = builder.build_runtime_payloads(
        devices=[
            {
                "id": 602,
                "name": "书房窗帘电机",
                "category": "curtain",
                "pid": 6002,
                "properties": [],
            },
            {
                "id": 603,
                "name": "次卧温控器",
                "category": "temp_control",
                "pid": 6003,
                "properties": [],
            },
        ],
        gateways=[],
        product_schemas={},
        apply_runtime_overrides=lambda payload: payload,
    )

    cover_candidates = list(iter_device_entity_candidates(data[602]))
    climate_candidates = list(iter_device_entity_candidates(data[603]))

    assert data[602]["iot_category"] == "curtain"
    assert data[603]["iot_category"] == "temp_control"
    assert cover_candidates == []
    assert climate_candidates == []


def test_runtime_payloads_project_scene_panels_as_events_not_switches() -> None:
    """仅凭名称不能把泛化开关 schema 改成面板事件设备。"""
    builder = DevicePayloadBuilder()

    data, _gateways = builder.build_runtime_payloads(
        devices=[
            {
                "id": 604,
                "name": "玄关全面屏面板",
                "category": "relay_switch",
                "pid": 6004,
                "properties": [],
            }
        ],
        gateways=[],
        product_schemas={6004: _relay_switch_schema(6004)},
        apply_runtime_overrides=lambda payload: payload,
    )

    device = data[604]
    candidates = list(iter_device_entity_candidates(device))

    assert device["iot_category"] == "relay_switch"
    assert [(item.platform, item.component_id) for item in candidates] == [
        ("switch", "relay_switch_1"),
        ("switch", "relay_switch_2"),
    ]


def test_runtime_payloads_do_not_project_indexed_power_for_non_switch_categories() -> None:
    """非继电器父品类即使带 indexed p，也不能生成 switch_1/2/3."""
    builder = DevicePayloadBuilder()

    data, _gateways = builder.build_runtime_payloads(
        devices=[
            {
                "id": 605,
                "name": "客厅窗帘电机",
                "category": "relay_switch",
                "type": "switch",
                "pid": 6005,
                "params": {"1-p": True, "2-p": True, "cp": 40, "tp": 90},
            },
            {
                "id": 606,
                "name": "卫生间暖风机",
                "category": "relay_switch",
                "type": "switch",
                "pid": 6006,
                "params": {"1-p": True, "2-p": False, "aco": True, "actt": 28},
            },
            {
                "id": 607,
                "name": "玄关全面屏面板",
                "category": "relay_switch",
                "type": "switch",
                "pid": 6007,
                "params": {"1-p": True, "2-p": True, "3-p": False},
            },
        ],
        gateways=[],
        product_schemas={},
        apply_runtime_overrides=lambda payload: payload,
    )

    by_device = {
        device_id: {
            (item.platform, item.component_id)
            for item in iter_device_entity_candidates(device)
        }
        for device_id, device in data.items()
    }

    assert data[605]["iot_category"] == "curtain"
    assert data[606]["iot_category"] == "temp_control"
    assert data[607]["iot_category"] == "relay_switch"
    assert by_device[605] == {("cover", "curtain")}
    assert ("climate", "temp_control") in by_device[606]
    assert by_device[607] == {
        ("switch", "switch_1"),
        ("switch", "switch_2"),
        ("switch", "switch_3"),
    }
    assert all(
        "switch" not in {platform for platform, _component_id in candidates}
        for device_id, candidates in by_device.items()
        if device_id != 607
    )


def _relay_switch_schema(pid: int) -> dict:
    return {
        "pid": pid,
        "name": "泛化开关 schema",
        "category": "relay_switch",
        "components": [
            {
                "index": 1,
                "name": "switch control",
                "category": "relay_switch",
                "properties": [{"propId": "p", "value": True, "operators": ["set"]}],
            },
            {
                "index": 2,
                "name": "switch control",
                "category": "relay_switch",
                "properties": [{"propId": "p", "value": False, "operators": ["set"]}],
            },
        ],
    }
