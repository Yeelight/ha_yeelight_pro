"""WiFi full-screen LAN topology normalization regressions."""

from __future__ import annotations

from custom_components.yeelight_pro.const import DOMAIN
from custom_components.yeelight_pro.core.device_payload import DevicePayloadBuilder
from custom_components.yeelight_pro.core.lan_topology_payload import (
    build_lan_topology_payloads,
)
from custom_components.yeelight_pro.entity_candidates import iter_device_entity_candidates
from custom_components.yeelight_pro.projector.event import project_events
from custom_components.yeelight_pro.projector.switch import project_switches


def test_wifi_panel_shared_resid_keeps_relay_and_scene_panel_capabilities() -> None:
    """WiFi 全面屏双路控制器和情景按键共用 resid 时不能互相覆盖。"""
    result = build_lan_topology_payloads(
        [
            {"id": 7919, "n": "dual", "nt": 2, "type": 7},
            {"id": 7919, "n": "scenes_panel", "nt": 2, "type": 128},
        ],
        builder=DevicePayloadBuilder(),
        apply_runtime_overrides=lambda payload: payload,
    )

    device = result.devices[7919]
    candidates = {
        (item.platform, item.component_id)
        for item in iter_device_entity_candidates(device)
    }
    switches = project_switches(device, domain=DOMAIN)
    events = project_events(device, domain=DOMAIN)

    assert list(result.devices) == [7919]
    assert device["params"] == {"1-p": False, "2-p": False}
    assert device["events"] == [
        {"name": "click"},
        {"name": "hold"},
        {"name": "release_after_hold"},
    ]
    assert device["ha_platform_candidates"] == ["switch", "event"]
    assert ("switch", "switch_1") in candidates
    assert ("switch", "switch_2") in candidates
    assert ("event", "scene_panel_3") in candidates
    assert [item.control_key for item in switches] == ["1-p", "2-p"]
    assert len(events) == 1
    assert events[0].component_id == "scene_panel_3"
    assert events[0].event_types == ["click", "hold", "release_after_hold"]
