"""Yeelight switch projection matrix regression tests."""

from __future__ import annotations

from custom_components.yeelight_pro.projector.switch import project_switches

from .projection_helpers import DOMAIN, projection_payload


def test_relay_switch_projects_switch() -> None:
    """继电器开关类应投影为 switch。"""
    device = projection_payload(
        device_id="switch-1",
        category="relay_switch",
        component_id="switch_control",
        state={"p": True},
        component_category="switch control",
    )

    projections = project_switches(device, domain=DOMAIN)

    assert len(projections) == 1
    assert projections[0].component_id == "switch_control"
    assert projections[0].control_key == "p"
    assert projections[0].is_on is True


def test_multi_switch_control_components_use_channel_names_not_generic_names() -> None:
    """多路开关组件不能都显示为泛化“开关组件”."""
    device = projection_payload(
        device_id="panel-switch-1",
        category="relay_switch",
        component_id="switch_1",
        state={"p": True},
        params={"1-p": True, "2-p": False},
        component_category="switch control",
        properties=("p",),
    )
    device["ha_device_instance"]["components"][0]["name"] = "switch control"
    device["ha_device_instance"]["components"].append({
        "component_id": "switch_2",
        "name": "switch control",
        "desc": "开关组件",
        "category": "switch control",
        "available": True,
        "state": {"p": False},
    })
    device["ha_product_model"]["components"][0]["name"] = "switch control"
    device["ha_product_model"]["schema_version"] = "runtime-v1"
    device["ha_product_model"]["components"].append({
        "component_id": "switch_2",
        "name": "switch control",
        "desc": "开关组件",
        "category": "switch control",
        "properties": [{"prop_id": "p", "access": "read_write"}],
        "events": [],
    })
    device["ha_device_instance"]["extensions"] = {
        "component_state_keys": {
            "switch_1": {"p": "1-p"},
            "switch_2": {"p": "2-p"},
        }
    }

    projections = project_switches(device, domain=DOMAIN)

    assert [(item.component_id, item.name, item.control_key) for item in projections] == [
        ("switch_1", "回路 1", "1-p"),
        ("switch_2", "回路 2", "2-p"),
    ]


def test_sparse_subdevice_switch_channels_do_not_share_plain_power_state() -> None:
    """OpenAPI 子设备状态稀疏时，多键开关不能把后续通道串到裸 p."""
    device = projection_payload(
        device_id="private-four-key",
        category="relay_switch",
        component_id="switch_1",
        state={"p": True, "sp": True},
        params={"1-p": True, "1-sp": True, "p": False, "sp": False, "o": True},
        component_category="relay_switch",
        properties=("p", "sp"),
    )
    device["name"] = "relay_switch-智能开关-四键 (rtl8762e版)-854041-01"
    device["ha_device_instance"]["components"][0]["name"] = "wireless switch channel"
    device["ha_product_model"]["components"][0]["index"] = 1
    device["ha_product_model"]["components"][0]["name"] = "wireless switch channel"
    device["subDeviceList"] = [
        {
            "index": index,
            "category": "relay_switch",
            "name": "wireless switch channel",
            "properties": [{"propId": "p"}, {"propId": "sp"}],
        }
        for index in range(1, 5)
    ]
    for index in range(2, 5):
        device["ha_device_instance"]["components"].append({
            "component_id": f"switch_{index}",
            "name": "wireless switch channel",
            "category": "relay_switch",
            "available": True,
            "state": {},
        })
        device["ha_product_model"]["components"].append({
            "component_id": f"switch_{index}",
            "index": index,
            "name": "wireless switch channel",
            "category": "relay_switch",
            "properties": [
                {"prop_id": "p", "access": "read_write"},
                {"prop_id": "sp", "access": "read_write"},
            ],
            "events": [],
        })

    projections = project_switches(device, domain=DOMAIN)

    assert [(item.component_id, item.name, item.control_key, item.is_on) for item in projections] == [
        ("switch_1", "按键 1", "1-sp", True),
        ("switch_2", "按键 2", "2-sp", None),
        ("switch_3", "按键 3", "3-sp", None),
        ("switch_4", "按键 4", "4-sp", None),
    ]
