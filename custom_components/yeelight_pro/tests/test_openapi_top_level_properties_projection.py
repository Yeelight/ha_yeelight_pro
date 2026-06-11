"""OpenAPI top-level property projection regressions."""

from __future__ import annotations

from custom_components.yeelight_pro.entity_candidates import iter_device_entity_candidates
from custom_components.yeelight_pro.projector.property_controls import (
    project_number_controls,
    project_select_controls,
    project_switch_controls,
)

from .openapi_subdevice_helpers import build_openapi_device, openapi_prop


def test_top_level_light_sensor_config_properties_project_from_openapi_metadata() -> None:
    """顶层 properties 也应按 OpenAPI/CSV 元数据生成传感和配置实体."""
    device = build_openapi_device(
        {
            "id": 9021,
            "name": "厨房烟雾传感器",
            "category": "light",
            "roomId": "room-1",
            "properties": [
                openapi_prop("mv", True, "人体移动", "boolean"),
                openapi_prop("luminance", 188, "照度", "uint16", unit="lx"),
                openapi_prop(
                    "sens_range",
                    3,
                    "感应距离",
                    "uint8",
                    range_={"min": 1, "max": 5, "step": 1},
                    operators=["set"],
                ),
                openapi_prop(
                    "lumi_setting",
                    120,
                    "照度阈值",
                    "uint16",
                    range_={"min": 0, "max": 1000, "step": 1},
                    operators=["set"],
                ),
                openapi_prop(
                    "delay_time",
                    30,
                    "延时时间",
                    "uint16",
                    range_={"min": 0, "max": 3600, "step": 1},
                    operators=["set"],
                ),
                openapi_prop(
                    "blp",
                    True,
                    "背光开关",
                    "boolean",
                    operators=["set"],
                ),
            ],
        }
    )

    candidates = {
        (item.platform, item.component_id, item.entity_category)
        for item in iter_device_entity_candidates(device)
    }
    numbers = {item.prop_id: item for item in project_number_controls(device, domain="yeelight_pro")}
    switches = {item.prop_id: item for item in project_switch_controls(device, domain="yeelight_pro")}

    assert device["iot_category"] == "light_sensor"
    assert ("binary_sensor", "motion", None) in candidates
    assert ("sensor", "illuminance", None) in candidates
    assert {
        ("number", "light_sensor_delay_time_number", "config"),
        ("number", "light_sensor_lumi_setting_number", "config"),
        ("number", "light_sensor_sens_range_number", "config"),
        ("switch", "light_sensor_blp_switch", "config"),
    } <= candidates
    assert numbers["sens_range"].native_range.min == 1
    assert numbers["sens_range"].native_range.max == 5
    assert numbers["lumi_setting"].native_range.max == 1000
    assert numbers["delay_time"].native_range.max == 3600
    assert switches["blp"].is_on is True
    assert device["device_info"]["model"] == "照度传感器"


def test_top_level_registry_value_list_projects_select_without_product_schema() -> None:
    """顶层 properties 没有 valueList 时，也可使用 CSV registry 枚举。"""
    device = build_openapi_device(
        {
            "id": 9022,
            "name": "走廊灯",
            "category": "light",
            "properties": [
                openapi_prop("p", True, "开关", "boolean", operators=["set"]),
                openapi_prop("l", 80, "亮度", "uint8", unit="%", operators=["set"]),
                openapi_prop("bp", "1", "上电状态", "uint8", operators=["set"]),
                openapi_prop("dd", 1000, "默认渐变时间", "uint16", operators=["set"]),
            ],
        }
    )

    selects = {item.prop_id: item for item in project_select_controls(device, domain="yeelight_pro")}
    numbers = {item.prop_id: item for item in project_number_controls(device, domain="yeelight_pro")}
    candidates = {
        (item.platform, item.component_id, item.entity_category)
        for item in iter_device_entity_candidates(device)
    }

    assert ("light", "light", None) in candidates
    assert ("select", "light_bp_select", "config") in candidates
    assert ("number", "light_dd_number", "config") in candidates
    assert [(item.value, item.label) for item in selects["bp"].options] == [
        ("0", "断电前状态"),
        ("1", "开启"),
        ("2", "关闭"),
    ]
    assert numbers["dd"].native_range.min == 0
    assert numbers["dd"].native_range.max == 10000
