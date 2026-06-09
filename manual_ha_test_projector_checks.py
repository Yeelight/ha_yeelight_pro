#!/usr/bin/env python3
"""Projector smoke checks for root-level manual Home Assistant scripts."""
from __future__ import annotations

from manual_ha_test_helpers import print_exception, sample_light_device


async def check_projectors(
    *,
    domain: str = "yeelight_pro",
    include_all: bool = False,
    device_name: str = "客厅灯",
) -> bool:
    """检查主要 projector facade 可调用。"""
    print("\n🔍 测试投影层...")
    try:
        from custom_components.yeelight_pro.projector.fan import project_fans
        from custom_components.yeelight_pro.projector.light import project_light
        from custom_components.yeelight_pro.projector.sensor import project_sensors
        from custom_components.yeelight_pro.projector.switch import project_switches

        device = sample_light_device(name=device_name)
        light = project_light(device, domain=domain)
        fans = project_fans(device, domain=domain)
        switches = project_switches(device, domain=domain)
        sensors = project_sensors(device, domain=domain)
        assert isinstance(fans, list)
        assert isinstance(switches, list)
        assert isinstance(sensors, list)

        print(f"  ✅ 灯光投影: {'成功' if light else '返回 None'}")
        print(f"  ✅ 风扇投影: 返回 {len(fans)} 个")
        print(f"  ✅ 开关投影: 返回 {len(switches)} 个")
        print(f"  ✅ 传感器投影: 返回 {len(sensors)} 个")
        if include_all:
            await _check_extra_projectors(device, domain=domain)
        return True
    except Exception as err:
        print_exception("投影层测试失败", err)
        return False


async def _check_extra_projectors(device: dict[str, object], *, domain: str) -> None:
    """检查完整 HA smoke 脚本额外覆盖的平台 projector。"""
    from custom_components.yeelight_pro.projector.binary_sensor import (
        project_binary_sensors,
    )
    from custom_components.yeelight_pro.projector.climate import project_climate
    from custom_components.yeelight_pro.projector.cover import project_cover
    from custom_components.yeelight_pro.projector.event import project_events
    from custom_components.yeelight_pro.projector.lock import project_lock

    binary_sensors = project_binary_sensors(device, domain=domain)
    cover = project_cover(device, domain=domain)
    climate = project_climate(device, domain=domain)
    lock = project_lock(device, domain=domain)
    events = project_events(device, domain=domain)
    assert isinstance(binary_sensors, list)
    assert isinstance(events, list)
    print(f"  ✅ 二值传感器投影: 返回 {len(binary_sensors)} 个")
    print(f"  ✅ 窗帘投影: {'成功' if cover else '返回 None'}")
    print(f"  ✅ 空调投影: {'成功' if climate else '返回 None'}")
    print(f"  ✅ 门锁投影: {'成功' if lock else '返回 None'}")
    print(f"  ✅ 事件投影: 返回 {len(events)} 个")
