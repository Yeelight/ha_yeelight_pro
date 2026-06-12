"""Yeelight component-level projection boundary regressions."""

from __future__ import annotations

from custom_components.yeelight_pro.projector.cover import project_cover
from custom_components.yeelight_pro.projector.light import project_light
from custom_components.yeelight_pro.projector.switch import project_switches

from .projection_helpers import DOMAIN, projection_payload


def test_light_component_category_power_only_does_not_project_light() -> None:
    """组件 category=light 也不能单凭 p 生造灯实体。"""
    device = projection_payload(
        device_id="component-light-power-only",
        category="light",
        component_id="vendor_power_component",
        state={"p": True},
        params={"p": True},
        component_category="light",
    )

    assert project_light(device, domain=DOMAIN) is None


def test_relay_component_category_power_only_does_not_project_switch() -> None:
    """组件 category=relay_switch 也必须有开关身份能力才生成 switch。"""
    device = projection_payload(
        device_id="component-relay-power-only",
        category="relay_switch",
        component_id="vendor_power_component",
        state={"p": True},
        params={"p": True},
        component_category="relay_switch",
    )

    assert project_switches(device, domain=DOMAIN) == []


def test_curtain_component_category_without_position_does_not_project_cover() -> None:
    """组件 category=curtain 不能在无位置属性时生造 cover。"""
    device = projection_payload(
        device_id="component-curtain-power-only",
        category="curtain",
        component_id="vendor_curtain_component",
        state={"p": True},
        params={"p": True},
        component_category="curtain",
    )

    assert project_cover(device, domain=DOMAIN) is None
