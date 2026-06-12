"""Product-catalog-backed device payload metadata tests."""

from __future__ import annotations

from custom_components.yeelight_pro.core.device_payload import DevicePayloadBuilder
from custom_components.yeelight_pro.entity_candidates import iter_device_entity_candidates


def test_runtime_payloads_use_product_catalog_for_pid_only_device_metadata() -> None:
    """只有易来 pid 时，设备详情应显示官方产品型号和组件轮廓."""
    builder = DevicePayloadBuilder()

    data, _gateways = builder.build_runtime_payloads(
        devices=[
            {
                "id": 85401801,
                "name": "双键开关",
                "category": "light",
                "pid": 854018,
                "roomId": 397,
            }
        ],
        gateways=[],
        product_schemas={},
        apply_runtime_overrides=lambda payload: payload,
        rooms=[{"id": "397", "name": "客厅"}],
    )

    device = data[85401801]
    device_info = device["ha_device_instance"]["device_info"]
    assert device["iot_category"] == "relay_switch"
    assert device["model_id"] == "YL-854018"
    assert device_info["name"] == "双键开关"
    assert device_info["model"] == "Yeelight Pro S21 智能墙壁开关-双键"
    assert device_info["model_id"] == "YL-854018"
    assert device_info["suggested_area"] == "客厅"
    components = device["ha_device_instance"]["components"]
    assert components[0]["component_id"] == "backlight_indicator"
    assert [component["component_id"] for component in components if component["category"] == "relay_switch"] == [
        "switch_1",
        "switch_2",
    ]


def test_pid_only_single_channel_products_get_friendly_entity_names() -> None:
    """官方单键/单路产品也必须显示通道语义，不能留空或裸数字。"""
    builder = DevicePayloadBuilder()

    data, _gateways = builder.build_runtime_payloads(
        devices=[
            {
                "id": 85401701,
                "name": "单键开关",
                "category": "light",
                "pid": 854017,
            },
            {
                "id": 839065901,
                "name": "单键情景面板",
                "category": "light",
                "pid": 8390659,
            },
        ],
        gateways=[],
        product_schemas={},
        apply_runtime_overrides=lambda payload: payload,
    )

    switch_candidates = {
        (item.platform, item.component_id): item.name
        for item in iter_device_entity_candidates(data[85401701])
    }
    panel_candidates = {
        (item.platform, item.component_id): item.name
        for item in iter_device_entity_candidates(data[839065901])
    }

    assert switch_candidates[("switch", "switch")] == "回路 1"
    assert panel_candidates[("event", "scene_panel")] == "按键 1 事件"


def test_runtime_payloads_normalize_scientific_product_pid_for_catalog_metadata() -> None:
    """OpenAPI/CSV 风格科学计数法 pid 应命中产品构成目录."""
    builder = DevicePayloadBuilder()

    data, _gateways = builder.build_runtime_payloads(
        devices=[
            {
                "id": 1700000101,
                "name": "DALI网关",
                "category": "light",
                "pid": "1.7000001e+07",
            }
        ],
        gateways=[],
        product_schemas={},
        apply_runtime_overrides=lambda payload: payload,
    )

    device = data[1700000101]
    device_info = device["ha_device_instance"]["device_info"]
    assert device["pid"] == 17000001
    assert device["model_id"] == "YL-17000001"
    assert device_info["model"] == "DALI网关"
    assert device_info["model_id"] == "YL-17000001"


def test_runtime_payloads_project_mixed_catalog_components_from_pid() -> None:
    """混合组件产品应按易来产品构成投影，不被云端粗 category=light 污染."""
    builder = DevicePayloadBuilder()

    data, _gateways = builder.build_runtime_payloads(
        devices=[
            {
                "id": 150937801,
                "name": "S系列情景开关",
                "category": "light",
                "pid": 1509378,
                "roomId": 397,
            }
        ],
        gateways=[],
        product_schemas={},
        apply_runtime_overrides=lambda payload: payload,
        rooms=[{"id": "397", "name": "走廊"}],
    )

    device = data[150937801]
    candidates = list(iter_device_entity_candidates(device))
    components = device["ha_device_instance"]["components"]

    assert device["model_id"] == "YL-1509378"
    assert device["ha_product_model"]["product"]["categories"] == [
        "scene_panel",
        "relay_switch",
    ]
    assert components[0]["component_id"] == "backlight_indicator"
    assert [component["component_id"] for component in components if component["category"] == "scene_panel"][:3] == [
        "scene_panel_1",
        "scene_panel_2",
        "scene_panel_3",
    ]
    assert [component["component_id"] for component in components[-4:]] == [
        "switch_1",
        "switch_2",
        "switch_3",
        "switch_4",
    ]
    assert sum(
        candidate.platform == "event"
        and str(candidate.component_id).startswith("scene_panel_")
        for candidate in candidates
    ) == 12
    assert [
        candidate.component_id
        for candidate in candidates
        if candidate.platform == "switch"
        and str(candidate.component_id) in {"switch_1", "switch_2", "switch_3", "switch_4"}
    ] == ["switch_1", "switch_2", "switch_3", "switch_4"]
    assert not any(candidate.platform == "light" for candidate in candidates)


def test_pid_only_contact_sensor_projects_one_official_entity_set() -> None:
    """只有 pid/category 时，应按产品目录生成一组门磁实体，不能重复组件。"""
    builder = DevicePayloadBuilder()

    data, _gateways = builder.build_runtime_payloads(
        devices=[
            {
                "id": 852249601,
                "name": "厨房烟雾传感器",
                "category": "contact_sensor",
                "pid": 8522496,
                "roomId": 1,
            }
        ],
        gateways=[],
        product_schemas={},
        apply_runtime_overrides=lambda payload: payload,
        rooms=[{"id": "1", "name": "厨房"}],
    )

    device = data[852249601]
    candidates = {
        (item.platform, item.component_id)
        for item in iter_device_entity_candidates(device)
    }

    assert device["iot_category"] == "contact_sensor"
    assert device["device_info"]["model"] == "Yeelight Pro S20 门窗传感器"
    assert [
        component["component_id"]
        for component in device["ha_device_instance"]["components"]
    ] == ["battery", "contact_sensor"]
    assert candidates == {
        ("binary_sensor", "battery_chargeable"),
        ("binary_sensor", "battery_charging"),
        ("binary_sensor", "door"),
        ("binary_sensor", "tamper"),
        ("sensor", "battery"),
        ("event", "contact_sensor"),
    }


def test_pid_only_mixed_input_device_projects_component_capabilities() -> None:
    """混合输入产品必须按组件能力生成实体，不能被云端粗 category=light 覆盖."""
    builder = DevicePayloadBuilder()

    data, _gateways = builder.build_runtime_payloads(
        devices=[
            {
                "id": 1700000501,
                "name": "DALI输入设备",
                "category": "light",
                "pid": 17000005,
            }
        ],
        gateways=[],
        product_schemas={},
        apply_runtime_overrides=lambda payload: payload,
    )

    device = data[1700000501]
    candidates = {
        (item.platform, item.component_id)
        for item in iter_device_entity_candidates(device)
    }

    assert device["iot_category"] == "light_sensor"
    assert device["ha_product_model"]["product"]["categories"] == [
        "scene_panel",
        "human_sensor",
        "light_sensor",
    ]
    assert ("event", "scene_panel") in candidates
    assert ("binary_sensor", "motion") in candidates
    assert ("sensor", "illuminance") in candidates
    assert not any(platform == "light" for platform, _component in candidates)


def test_pid_only_metadata_product_does_not_become_gateway_from_global_component() -> None:
    """只有基础全局组件时不能用 cpt/o 等诊断属性猜成网关品类."""
    builder = DevicePayloadBuilder()

    data, _gateways = builder.build_runtime_payloads(
        devices=[
            {
                "id": 904061801,
                "name": "人在传感器吸顶",
                "category": "light",
                "pid": 9040618,
            }
        ],
        gateways=[],
        product_schemas={},
        apply_runtime_overrides=lambda payload: payload,
    )

    device = data[904061801]

    assert device["iot_category"] == "light"
    assert device["ha_product_model"]["product"]["categories"] == []
    assert [
        (item.platform, item.component_id)
        for item in iter_device_entity_candidates(device)
    ] == []
