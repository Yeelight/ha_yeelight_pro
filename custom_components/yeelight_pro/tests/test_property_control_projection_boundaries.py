"""Boundary tests for schema-backed writable property controls."""

from __future__ import annotations

from custom_components.yeelight_pro.projector.property_controls import (
    project_number_controls,
    project_select_controls,
    project_switch_controls,
)

from .projection_helpers import DOMAIN, projection_payload


def test_unknown_schema_writable_metadata_does_not_project_auxiliary_controls() -> None:
    """未知私有 schema 即使声明可写和值域/枚举，也不能生成 HA 控件。"""
    payload = projection_payload(
        device_id="vendor-controls-1",
        category="other",
        component_id="vendor_private_controls",
        component_category="vendor private controls",
        state={
            "vendor_level": 25,
            "vendor_mode": "auto",
            "vendor_flag": True,
        },
        params={
            "vendor_level": 25,
            "vendor_mode": "auto",
            "vendor_flag": True,
        },
    )
    payload["ha_product_model"]["components"][0]["properties"] = [
        {
            "prop_id": "vendor_level",
            "name": "Vendor level",
            "access": "read_write",
            "property_type": "int",
            "value_range": {"min": 0, "max": 100, "step": 1},
        },
        {
            "prop_id": "vendor_mode",
            "name": "Vendor mode",
            "access": "read_write",
            "property_type": "enum",
            "value_list": [
                {"code": "auto", "desc": "Auto"},
                {"code": "manual", "desc": "Manual"},
            ],
        },
        {
            "prop_id": "vendor_flag",
            "name": "Vendor flag",
            "access": "read_write",
            "property_type": "bool",
            "format": "bool",
        },
    ]

    assert project_number_controls(payload, domain=DOMAIN) == []
    assert project_select_controls(payload, domain=DOMAIN) == []
    assert project_switch_controls(payload, domain=DOMAIN) == []


def test_component_labels_do_not_hide_documented_auxiliary_controls() -> None:
    """组件标签像主设备类型时，不能靠名称吞掉非该平台的配置控件。"""
    payload = projection_payload(
        device_id="labelled-air-1",
        category="other",
        component_id="vendor_controls",
        component_category="other",
        state={"blp": True},
        params={"blp": True},
    )
    component = payload["ha_device_instance"]["components"][0]
    component["name"] = "空调新风窗帘"
    component["desc"] = "空调新风窗帘"
    payload["ha_product_model"]["components"][0]["name"] = "空调新风窗帘"
    payload["ha_product_model"]["components"][0]["desc"] = "空调新风窗帘"
    payload["ha_product_model"]["components"][0]["properties"] = [
        {
            "prop_id": "blp",
            "name": "背光",
            "access": "read_write",
            "property_type": "bool",
            "format": "bool",
        }
    ]

    switches = project_switch_controls(payload, domain=DOMAIN)

    assert [item.component_id for item in switches] == ["vendor_controls_blp_switch"]
