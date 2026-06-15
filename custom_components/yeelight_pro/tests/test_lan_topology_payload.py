"""LAN topology normalization tests based on Yeelight IoT documents."""

from __future__ import annotations

from homeassistant.components.climate import ClimateEntityFeature, HVACMode

from custom_components.yeelight_pro.const import (
    DOMAIN,
)
from custom_components.yeelight_pro.core.device_payload import DevicePayloadBuilder
from custom_components.yeelight_pro.core.lan_topology_payload import (
    build_lan_topology_payloads,
)
from custom_components.yeelight_pro.entity_candidates import iter_device_entity_candidates
from custom_components.yeelight_pro.projector.climate import project_climates
from custom_components.yeelight_pro.projector.sensor import project_sensors
from custom_components.yeelight_pro.projector.event import project_events
from custom_components.yeelight_pro.projector.property_controls import project_select_controls


def _build(nodes: list[dict]) -> dict[int, dict]:
    return build_lan_topology_payloads(
        nodes,
        builder=DevicePayloadBuilder(),
        apply_runtime_overrides=lambda payload: payload,
    ).devices


def test_lan_topology_builds_canonical_light_with_room_metadata() -> None:
    """LAN type=3 应按易来色温灯能力入模，并带入房间和设备 registry 元数据."""
    result = build_lan_topology_payloads(
        [
            {"id": 201, "nt": 1, "n": "客厅"},
            {"id": 1001, "nt": 2, "type": 3, "n": "客厅灯", "roomid": 201},
        ],
        builder=DevicePayloadBuilder(),
        apply_runtime_overrides=lambda payload: payload,
    )

    device = result.devices[1001]
    device_info = device["ha_device_instance"]["device_info"]

    assert device["iot_category"] == "light"
    assert device["ha_platform_candidates"] == ["light"]
    assert device["model"] == "色温灯"
    assert device["model_id"] == "YL-LAN-3"
    assert device["room_name"] == "客厅"
    assert device_info["suggested_area"] == "客厅"
    assert device_info["identifiers"] == [
        ["yeelight_pro", "1001"],
        ["yeelight_pro", "device:1001"],
    ]


def test_lan_topology_ignores_misleading_user_device_names() -> None:
    """用户名称不能覆盖 LAN type 和属性能力给出的真实设备类型。"""
    devices = _build([
        {"id": 1002, "nt": 2, "type": 3, "n": "厨房烟雾传感器"},
        {"id": 1003, "nt": 2, "type": 130, "n": "客厅灯"},
    ])

    light = devices[1002]
    contact = devices[1003]

    assert light["iot_category"] == "light"
    assert light["ha_platform"] == "light"
    assert light["device_info"]["model"] == "色温灯"
    assert contact["iot_category"] == "contact_sensor"
    assert contact["ha_platform_candidates"] == ["binary_sensor", "event"]
    assert contact["device_info"]["model"] == "门磁传感器"


def test_lan_temperature_humidity_sensor_stays_sensor_not_climate() -> None:
    """LAN type=136 是温湿度传感器，不应被温控类 climate 抢占。"""
    device = _build([
        {"id": 1004, "nt": 2, "type": 136, "n": "主卧环境"},
    ])[1004]
    candidates = list(iter_device_entity_candidates(device))

    assert device["iot_category"] == "other"
    assert device["ha_platform_candidates"] == ["sensor"]
    assert device["device_info"]["model"] == "温湿度传感器"
    assert {(item.platform, item.name) for item in candidates} == {
        ("sensor", "温度"),
        ("sensor", "湿度"),
    }


def test_lan_temperature_humidity_sensor_scales_documented_raw_temperature() -> None:
    """LAN type=136 的 t 是摄氏度放大 100 倍，入站时应转成真实摄氏值。"""
    device = _build([
        {
            "id": 1006,
            "nt": 2,
            "type": 136,
            "n": "主卧环境",
            "params": {"t": 2534, "h": 58},
        },
    ])[1006]

    sensors = project_sensors(device, domain=DOMAIN)
    by_component = {item.component_id: item for item in sensors}

    assert device["params"]["t"] == 25.34
    assert device["ha_device_instance"]["components"][0]["state"]["t"] == 25.34
    assert by_component["temperature"].native_value == 25.34
    assert by_component["humidity"].native_value == 58


def test_lan_multi_switch_channels_use_friendly_names() -> None:
    """LAN ch_num/cids 应生成索引组件，让多键开关显示左键/中键/右键。"""
    device = _build([
        {
            "id": 1005,
            "nt": 2,
            "type": 13,
            "n": "厨房开关",
            "ch_num": 3,
            "cids": [11, 12, 13],
        },
    ])[1005]
    candidates = [
        item
        for item in iter_device_entity_candidates(device)
        if item.platform == "switch"
    ]

    assert device["iot_category"] == "relay_switch"
    assert device["params"] == {"1-sp": False, "2-sp": False, "3-sp": False}
    assert [item.component_id for item in candidates] == [
        "switch_1",
        "switch_2",
        "switch_3",
    ]
    assert [item.name for item in candidates] == ["左键", "中键", "右键"]


def test_lan_scene_panel_projects_all_documented_panel_events() -> None:
    """LAN type=128 应包含 click/hold/release 三类面板事件。"""
    device = _build([
        {"id": 1007, "nt": 2, "type": 128, "n": "玄关情景面板"},
    ])[1007]

    events = project_events(device, domain=DOMAIN)

    assert device["events"] == [
        {"name": "click"},
        {"name": "hold"},
        {"name": "release_after_hold"},
    ]
    assert len(events) == 1
    assert events[0].event_types == ["click", "hold", "release_after_hold"]


def test_lan_bath_heater_projects_documented_auxiliary_controls() -> None:
    """LAN type=2049 浴霸应保留换气/吹风/加热档位和延时关闭控件。"""
    device = _build([
        {"id": 1008, "nt": 2, "type": 2049, "n": "主卫浴霸"},
    ])[1008]
    candidates = {
        (item.platform, item.component_id, item.entity_category)
        for item in iter_device_entity_candidates(device)
    }

    assert device["device_info"]["model"] == "浴霸加热器"
    assert device["params"] == {
        "p": False,
        "bhm": 1,
        "do": 1,
        "ve": 0,
        "fa": 0,
        "he": 0,
        "tgt": 26,
        "t": 26,
    }
    assert ("climate", "temp_control", None) in candidates
    assert ("select", "temp_control_bhm_select", None) in candidates
    assert ("number", "temp_control_do_number", None) in candidates
    assert ("select", "temp_control_ve_select", None) in candidates
    assert ("select", "temp_control_fa_select", None) in candidates
    assert ("select", "temp_control_he_select", None) in candidates
    bath_mode = next(
        item for item in project_select_controls(device, domain=DOMAIN) if item.prop_id == "bhm"
    )
    assert [item.value for item in bath_mode.options] == ["1", "2", "3", "4"]


def test_lan_tof_sensor_projects_only_documented_handwave_event() -> None:
    """LAN type=2052 是 TOF 传感器，只应暴露 handwave 事件。"""
    device = _build([
        {"id": 1009, "nt": 2, "type": 2052, "n": "玄关 TOF"},
    ])[1009]

    events = project_events(device, domain=DOMAIN)

    assert device["iot_category"] == "other"
    assert device["device_info"]["model"] == "TOF传感器"
    assert device["events"] == [{"name": "handwave"}]
    assert len(events) == 1
    assert events[0].event_types == ["handwave"]


def test_lan_meray_human_sensor_projects_documented_approach_events() -> None:
    """LAN type=138 迈睿人体传感器应包含 approach.true/false 事件。"""
    device = _build([
        {"id": 1012, "nt": 2, "type": 138, "n": "玄关迈睿人体"},
    ])[1012]

    events = project_events(device, domain=DOMAIN)

    assert device["events"] == [
        {"name": "motion_detected"},
        {"name": "motion_undetected"},
        {"name": "human_enter"},
        {"name": "human_leave"},
    ]
    assert len(events) == 1
    assert events[0].event_types == [
        "motion_detected",
        "motion_undetected",
        "human_enter",
        "human_leave",
    ]


def test_lan_single_ac_controller_projects_mode_and_fan_controls() -> None:
    """LAN type=15 一对一空调控制器应暴露文档定义的模式和风速控制。"""
    device = _build([
        {"id": 1010, "nt": 2, "type": 15, "n": "主卧空调"},
    ])[1010]

    climates = project_climates(device, domain=DOMAIN)

    assert device["device_info"]["model"] == "空调控制器"
    assert device["params"] == {
        "acp": False,
        "acm": 1,
        "actt": 26,
        "acct": 26,
        "acf": 4,
    }
    assert len(climates) == 1
    climate = climates[0]
    assert climate.component_id == "temp_control"
    assert climate.hvac_mode == HVACMode.OFF
    assert climate.hvac_modes == [
        HVACMode.OFF,
        HVACMode.AUTO,
        HVACMode.COOL,
        HVACMode.FAN_ONLY,
        HVACMode.HEAT,
    ]
    assert climate.mode_key == "acm"
    assert climate.fan_mode_key == "acf"
    assert climate.fan_mode == "低"
    assert climate.fan_modes == ["高", "中", "低"]
    assert climate.supported_features & (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE
    )


def test_lan_multi_ac_gateway_projects_indexed_climate_channels() -> None:
    """LAN type=10 空调网关应按 ch_num 拆成多路 indexed climate。"""
    device = _build([
        {
            "id": 1011,
            "nt": 2,
            "type": 10,
            "n": "VRF 空调网关",
            "ch_num": 2,
            "cids": [101, 102],
        },
    ])[1011]

    climates = project_climates(device, domain=DOMAIN)
    candidates = [
        item
        for item in iter_device_entity_candidates(device)
        if item.platform == "climate"
    ]

    assert device["device_info"]["model"] == "空调网关"
    assert device["params"] == {
        "1-acp": False,
        "1-acm": 1,
        "1-actt": 26,
        "1-acct": 26,
        "1-acf": 4,
        "2-acp": False,
        "2-acm": 1,
        "2-actt": 26,
        "2-acct": 26,
        "2-acf": 4,
    }
    assert [item.component_id for item in climates] == [
        "air_conditioner_1",
        "air_conditioner_2",
    ]
    assert [item.power_key for item in climates] == ["1-acp", "2-acp"]
    assert [item.mode_key for item in climates] == ["1-acm", "2-acm"]
    assert [item.target_temperature_key for item in climates] == [
        "1-actt",
        "2-actt",
    ]
    assert [item.fan_mode_key for item in climates] == ["1-acf", "2-acf"]
    assert [item.fan_mode for item in climates] == ["低", "低"]
    assert [item.component_id for item in candidates] == [
        "air_conditioner_1",
        "air_conditioner_2",
    ]
