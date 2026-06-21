"""Switch-channel projection boundary tests."""

from __future__ import annotations

from custom_components.yeelight_pro.core.device_payload import DevicePayloadBuilder
from custom_components.yeelight_pro.projector.switch import project_switches

from .projection_helpers import DOMAIN, projection_payload


def test_relay_switch_legacy_indexed_keys_still_project_switches() -> None:
    """已知继电器旧载荷仍可用 indexed IoT 控制键生成多路 switch。"""
    device = {
        "device_id": "relay-indexed-1",
        "name": "多路继电器",
        "category": "relay_switch",
        "type": "switch",
        "online": True,
        "params": {"1-p": True, "2-sp": False},
    }

    projections = project_switches(device, domain=DOMAIN)

    assert [item.component_id for item in projections] == ["switch_1", "switch_2"]
    assert [item.control_key for item in projections] == ["1-p", "2-sp"]
    assert [item.name for item in projections] == ["回路 1", "回路 2"]
    assert [item.is_on for item in projections] == [True, False]


def test_raw_sp_switch_channels_use_key_labels_without_changing_ids() -> None:
    """物模型 N-sp 表示无线开关通道，展示为按键但保留旧 switch_N 身份."""
    device = {
        "device_id": "four-key-1",
        "name": "四键",
        "category": "relay_switch",
        "type": "switch",
        "online": True,
        "params": {
            "1-sp": True,
            "2-sp": False,
            "3-sp": True,
            "4-sp": False,
        },
    }

    projections = project_switches(device, domain=DOMAIN)

    assert [item.component_id for item in projections] == [
        "switch_1",
        "switch_2",
        "switch_3",
        "switch_4",
    ]
    assert [item.control_key for item in projections] == [
        "1-sp",
        "2-sp",
        "3-sp",
        "4-sp",
    ]
    assert [item.name for item in projections] == [
        "按键 1",
        "按键 2",
        "按键 3",
        "按键 4",
    ]


def test_schema_backed_sp_switch_channels_use_key_labels_without_changing_ids() -> None:
    """schema-backed 四键也应由 N-sp 控制键证明为按键语义."""
    device = projection_payload(
        device_id="four-key-schema-1",
        category="relay_switch",
        component_id="switch_1",
        state={"sp": True},
        params={
            "1-sp": True,
            "2-sp": False,
            "3-sp": True,
            "4-sp": False,
        },
        component_category="relay_switch",
        properties=("sp",),
    )

    projections = project_switches(device, domain=DOMAIN)

    assert projections[0].component_id == "switch_1"
    assert projections[0].control_key == "1-sp"
    assert projections[0].name == "按键 1"


def test_openapi_wireless_switch_subdevices_use_key_labels_without_pid() -> None:
    """私有部署 OpenAPI 无 pid 时也应按 subDeviceList 组件身份显示按键."""
    raw_device = {
        "id": 40266116,
        "name": "四键",
        "category": "relay_switch",
        "online": True,
        "subDeviceList": [
            {
                "index": index,
                "name": "wireless switch channel",
                "category": "relay_switch",
                "properties": [
                    {"propId": "p", "value": index == 1, "operators": ["set", "toggle"]},
                    {"propId": "sp", "value": index == 1, "operators": ["set", "toggle"]},
                ],
            }
            for index in range(1, 5)
        ],
    }
    devices, _gateways = DevicePayloadBuilder().build_runtime_payloads(
        devices=[raw_device],
        gateways=[],
        product_schemas={},
        apply_runtime_overrides=lambda device: device,
        rooms=[],
        areas=[],
    )
    projections = project_switches(devices[40266116], domain=DOMAIN)

    assert [item.component_id for item in projections] == [
        "switch_1",
        "switch_2",
        "switch_3",
        "switch_4",
    ]
    assert [item.control_key for item in projections] == [
        "1-sp",
        "2-sp",
        "3-sp",
        "4-sp",
    ]
    assert [item.name for item in projections] == [
        "按键 1",
        "按键 2",
        "按键 3",
        "按键 4",
    ]


def test_schema_backed_catalog_wireless_switch_keeps_legacy_switch_identity() -> None:
    """官方 schema 组件名变化时，HA 仍应使用历史稳定的 switch_N 身份."""
    raw_device = {
        "id": 50018395,
        "device_id": 50018395,
        "name": "四键",
        "category": "relay_switch",
        "type": "switch",
        "online": True,
        "pid": 854041,
        "params": {
            "1-sp": True,
            "2-sp": False,
            "3-sp": True,
            "4-sp": False,
        },
    }
    schema = {
        "pid": 854041,
        "name": "四键",
        "category": "relay_switch",
        "components": [
            {
                "index": index,
                "name": "wireless switch channel",
                "type": 0,
                "category": "relay_switch",
                "properties": [{"propId": "sp", "operators": ["set"]}],
            }
            for index in range(1, 5)
        ],
    }
    devices, _gateways = DevicePayloadBuilder().build_runtime_payloads(
        devices=[raw_device],
        gateways=[],
        product_schemas={854041: schema},
        apply_runtime_overrides=lambda device: device,
        rooms=[],
        areas=[],
    )

    device = devices[50018395]
    projections = project_switches(device, domain=DOMAIN)

    assert [
        component["component_id"]
        for component in device["ha_device_instance"]["components"]
    ] == [
        "relay_switch_1",
        "relay_switch_2",
        "relay_switch_3",
        "relay_switch_4",
    ]
    assert [item.component_id for item in projections] == [
        "switch_1",
        "switch_2",
        "switch_3",
        "switch_4",
    ]
    assert [item.unique_id for item in projections] == [
        "yeelight_pro_50018395_switch_1",
        "yeelight_pro_50018395_switch_2",
        "yeelight_pro_50018395_switch_3",
        "yeelight_pro_50018395_switch_4",
    ]
    assert [item.control_key for item in projections] == [
        "1-sp",
        "2-sp",
        "3-sp",
        "4-sp",
    ]
    assert [item.is_on for item in projections] == [True, False, True, False]


def test_schema_backed_catalog_dual_relay_keeps_power_control_keys() -> None:
    """双路继电器按文档继续使用 N-p，不能被无线通道规则误改成 N-sp."""
    raw_device = {
        "id": 460800,
        "device_id": 460800,
        "name": "双路继电器",
        "category": "relay_switch",
        "type": "switch",
        "online": True,
        "pid": 460800,
        "params": {"1-p": True, "2-p": False},
    }
    schema = {
        "pid": 460800,
        "name": "双路继电器",
        "category": "relay_switch",
        "components": [
            {
                "index": index,
                "name": "switch control",
                "type": 0,
                "category": "relay_switch",
                "properties": [{"propId": "p", "operators": ["set"]}],
            }
            for index in range(1, 3)
        ],
    }
    devices, _gateways = DevicePayloadBuilder().build_runtime_payloads(
        devices=[raw_device],
        gateways=[],
        product_schemas={460800: schema},
        apply_runtime_overrides=lambda device: device,
        rooms=[],
        areas=[],
    )

    projections = project_switches(devices[460800], domain=DOMAIN)

    assert [item.control_key for item in projections] == ["1-p", "2-p"]
    assert [item.is_on for item in projections] == [True, False]


def test_relay_switch_event_component_with_power_still_projects_primary_switch() -> None:
    """S21 单键墙壁开关有事件也有 p 控制时，不能只投影事件和背光配置."""
    device = projection_payload(
        device_id="s21-single-1",
        category="relay_switch",
        component_id="switch",
        state={"p": True, "sp": False},
        params={"p": True, "sp": False, "o": True},
        component_category="relay_switch",
        product_events=[
            {"event_id": "click", "name": "点击"},
            {"event_id": "hold", "name": "长按"},
        ],
        properties=("p", "sp"),
    )
    product_component = device["ha_product_model"]["components"][0]
    product_component["name"] = "scene panel"
    product_component["component_type"] = "scene_panel"
    product_component["properties"] = [
        {"prop_id": "p", "access": "read_write"},
        {"prop_id": "sp", "access": "read_write"},
    ]

    projections = project_switches(device, domain=DOMAIN)

    assert [(item.component_id, item.control_key, item.is_on) for item in projections] == [
        ("switch", "p", True)
    ]


def test_scene_panel_event_component_with_power_does_not_project_switch() -> None:
    """纯情景面板即使 schema 带 p，也不应被误投影成开关。"""
    device = projection_payload(
        device_id="scene-panel-1",
        category="scene_panel",
        component_id="scene_button_1",
        state={"p": True},
        params={"p": True, "o": True},
        component_category="scene_panel",
        product_events=[{"event_id": "click", "name": "点击"}],
        properties=("p",),
    )

    assert project_switches(device, domain=DOMAIN) == []


def test_repeated_schema_sp_components_map_to_indexed_key_labels() -> None:
    """无索引 schema 组件重复声明 sp 时，应按组件顺序映射到 N-sp 按键."""
    device = projection_payload(
        device_id="four-key-repeated-schema-1",
        category="relay_switch",
        component_id="switch_1",
        state={"sp": True},
        params={
            "1-sp": True,
            "2-sp": False,
            "3-sp": True,
            "4-sp": False,
        },
        component_category="relay_switch",
        properties=("sp",),
    )
    instance_components = device["ha_device_instance"]["components"]
    product_components = device["ha_product_model"]["components"]
    for index in range(2, 5):
        instance_components.append({
            **instance_components[0],
            "component_id": f"switch_{index}",
            "state": {"sp": bool(index % 2)},
        })
        product_components.append({
            **product_components[0],
            "component_id": f"switch_{index}",
        })

    projections = project_switches(device, domain=DOMAIN)

    assert [item.component_id for item in projections] == [
        "switch_1",
        "switch_2",
        "switch_3",
        "switch_4",
    ]
    assert [item.control_key for item in projections] == [
        "1-sp",
        "2-sp",
        "3-sp",
        "4-sp",
    ]
    assert [item.name for item in projections] == [
        "按键 1",
        "按键 2",
        "按键 3",
        "按键 4",
    ]
