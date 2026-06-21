"""Switch-channel catalog boundary tests."""

from __future__ import annotations

from custom_components.yeelight_pro.projector.switch import project_switches

from .projection_helpers import DOMAIN


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
