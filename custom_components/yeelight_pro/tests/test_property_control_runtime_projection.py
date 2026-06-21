"""Runtime auxiliary property control projection tests."""

from __future__ import annotations

from custom_components.yeelight_pro.projector.property_controls import (
    project_number_controls,
    project_switch_controls,
)

from .projection_helpers import DOMAIN, projection_payload


def test_runtime_other_music_controls_use_documented_property_names() -> None:
    """全景屏音乐组件不能把 other/raw 英文描述泄漏到实体名."""
    payload = projection_payload(
        device_id="screen-1",
        category="other",
        component_id="other",
        component_category="other",
        state={"mppm": 1, "mpmp": False},
        params={"mppm": 1, "mpmp": False},
    )
    payload["name"] = "全景屏"
    payload["ha_product_model"]["components"][0]["properties"] = [
        {
            "prop_id": "mppm",
            "name": "music player play mode,音乐播放器播放模式",
            "access": "read_write",
            "property_type": "int",
            "value_range": {"min": 0, "max": 10, "step": 1},
        },
        {
            "prop_id": "mpmp",
            "name": "music player play pause,音乐播放器播放/暂停",
            "access": "read_write",
            "property_type": "bool",
        },
    ]

    numbers = project_number_controls(payload, domain=DOMAIN)
    switches = project_switch_controls(payload, domain=DOMAIN)

    assert numbers[0].name == "音乐播放器播放模式"
    assert switches[0].name == "音乐播放器播放/暂停"


def test_runtime_other_music_bool_controls_preserve_unknown_state() -> None:
    """P20 音乐组件只有属性定义无当前值时，布尔控制应投影为未知状态."""
    payload = projection_payload(
        device_id="screen-unknown-1",
        category="other",
        component_id="other",
        component_category="other",
        state={},
        params={},
    )
    payload["name"] = "P20 全景屏"
    payload["ha_product_model"]["components"][0]["properties"] = [
        {
            "prop_id": "mpmp",
            "name": "music player play pause,音乐播放器播放/暂停",
            "access": "read_write",
            "property_type": "config",
            "format": "bool",
        },
        {
            "prop_id": "mpml",
            "name": "music player music list,音乐播放器歌单ID",
            "access": "read_write",
            "property_type": "config",
            "format": "bool",
        },
    ]

    switches = project_switch_controls(payload, domain=DOMAIN)

    assert [(item.prop_id, item.is_on) for item in switches] == [
        ("mpmp", None),
        ("mpml", None),
    ]


def test_runtime_other_global_music_controls_keep_public_other_identity() -> None:
    """official other_global 组件应投影为旧 other_* helper 身份."""
    payload = projection_payload(
        device_id="screen-global-music-1",
        category="gateway",
        component_id="other_global",
        component_category="other",
        state={},
        params={},
    )
    payload["name"] = "6.9 寸智慧屏"
    payload["ha_device_instance"]["components"][0]["component_type"] = "global"
    payload["ha_product_model"]["components"][0]["component_type"] = "global"
    payload["ha_product_model"]["components"][0]["properties"] = [
        {
            "prop_id": "mpmp",
            "name": "music player play pause,音乐播放器播放/暂停",
            "access": "read_write",
            "property_type": "config",
            "format": "boolean",
        },
        {
            "prop_id": "mppm",
            "name": "music player play mode,音乐播放器播放模式",
            "access": "read_write",
            "property_type": "config",
            "format": "uint16",
            "value_range": {"min": 0, "max": 10, "step": 1},
        },
    ]

    switches = project_switch_controls(payload, domain=DOMAIN)
    numbers = project_number_controls(payload, domain=DOMAIN)

    assert [(item.component_id, item.unique_id, item.control_key) for item in switches] == [
        (
            "other_mpmp_switch",
            "yeelight_pro_screen-global-music-1_other_mpmp_switch",
            "mpmp",
        )
    ]
    assert [(item.component_id, item.unique_id, item.control_key) for item in numbers] == [
        (
            "other_mppm_number",
            "yeelight_pro_screen-global-music-1_other_mppm_number",
            "mppm",
        )
    ]


def test_runtime_other_music_schema_type_overrides_registry_bool() -> None:
    """P20 音乐组件 schema 明确非 bool 时，不应被 registry 旧类型误投影为 switch."""
    payload = projection_payload(
        device_id="screen-music-typed-1",
        category="other",
        component_id="other",
        component_category="other",
        state={},
        params={},
    )
    payload["name"] = "P20 全景屏"
    payload["ha_product_model"]["components"][0]["properties"] = [
        {
            "prop_id": "mpml",
            "name": "music player music list,音乐播放器歌单ID",
            "access": "read_write",
            "property_type": "config",
            "format": "uint16",
            "value_range": {"min": 0, "max": 65535, "step": 1},
        },
        {
            "prop_id": "mpmp",
            "name": "music player play pause,音乐播放器播放/暂停",
            "access": "read_write",
            "property_type": "config",
            "format": "boolean",
            "value_range": {"min": 0, "max": 0, "step": 0},
        },
        {
            "prop_id": "mpmr",
            "name": "music player music rhythm,音乐播放器音乐律动",
            "access": "read_write",
            "property_type": "config",
            "format": "boolean",
            "value_range": {"min": 0, "max": 0, "step": 0},
        },
    ]

    numbers = project_number_controls(payload, domain=DOMAIN)
    switches = project_switch_controls(payload, domain=DOMAIN)

    assert [(item.prop_id, item.native_range.min, item.native_range.max) for item in numbers] == [
        ("mpml", 0, 65535),
    ]
    assert [(item.prop_id, item.is_on) for item in switches] == [
        ("mpmp", None),
        ("mpmr", None),
    ]


def test_structural_component_controls_use_chinese_component_label() -> None:
    """空调等官方组件别名不能把 air_conditioner 泄漏到辅助控制实体名."""
    payload = projection_payload(
        device_id="climate-helper-1",
        category="temp_control",
        component_id="air_conditioner_1",
        component_category="air_conditioner",
        state={"acrc": False},
        params={"1-acrc": False},
    )
    payload["ha_device_instance"]["extensions"] = {
        "component_state_keys": {
            "air_conditioner_1": {"acrc": "1-acrc"},
        }
    }
    payload["ha_product_model"]["components"][0]["name"] = "air conditioner"
    payload["ha_product_model"]["components"][0]["properties"] = [
        {
            "prop_id": "acrc",
            "name": "空调遥控器使能",
            "access": "read_write",
            "property_type": "bool",
        },
    ]

    switches = project_switch_controls(payload, domain=DOMAIN)

    assert switches[0].name == "空调控制器 空调遥控器使能"
