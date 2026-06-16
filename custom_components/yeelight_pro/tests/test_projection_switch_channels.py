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
        "1-p",
        "2-p",
        "3-p",
        "4-p",
    ]
    assert [item.name for item in projections] == [
        "按键 1",
        "按键 2",
        "按键 3",
        "按键 4",
    ]


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


def test_product_catalog_double_switch_limits_legacy_indexed_channels() -> None:
    """官方产品构成双键不应因为云端残留第三路 key 而生成三键实体。"""
    device = {
        "device_id": "double-switch-1",
        "name": "厨房开关",
        "pid": 854018,
        "category": "relay_switch",
        "type": "switch",
        "online": True,
        "params": {"1-p": True, "2-p": False, "3-p": True},
    }

    projections = project_switches(device, domain=DOMAIN)

    assert [item.component_id for item in projections] == ["switch_1", "switch_2"]
    assert [item.name for item in projections] == ["左键", "右键"]


def test_user_device_name_does_not_limit_legacy_indexed_channels() -> None:
    """用户把设备命名为双键开关时，不能裁剪实际出现的第三路能力。"""
    device = {
        "device_id": "named-double-switch-1",
        "name": "厨房双键开关",
        "category": "relay_switch",
        "type": "switch",
        "online": True,
        "params": {"1-p": True, "2-p": False, "3-p": True},
    }

    projections = project_switches(device, domain=DOMAIN)

    assert [item.component_id for item in projections] == [
        "switch_1",
        "switch_2",
        "switch_3",
    ]
    assert [item.name for item in projections] == ["回路 1", "回路 2", "回路 3"]


def test_three_gang_switch_projects_positional_channel_names() -> None:
    """官方三键产品在 HA 设备详情中应显示左/中/右键。"""
    device = {
        "device_id": "three-switch-1",
        "name": "玄关开关",
        "pid": 854019,
        "category": "relay_switch",
        "type": "switch",
        "online": True,
        "params": {"1-p": True, "2-p": False, "3-p": True},
    }

    projections = project_switches(device, domain=DOMAIN)

    assert [item.component_id for item in projections] == [
        "switch_1",
        "switch_2",
        "switch_3",
    ]
    assert [item.name for item in projections] == ["左键", "中键", "右键"]
