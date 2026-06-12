"""Device trigger listing and validation tests for Yeelight Pro event devices."""

from __future__ import annotations

import pytest

from homeassistant.components.device_automation import InvalidDeviceAutomationConfig
from homeassistant.const import CONF_DEVICE_ID, CONF_DOMAIN, CONF_PLATFORM, CONF_TYPE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.trigger import TriggerInfo

from custom_components.yeelight_pro.const import DOMAIN
from custom_components.yeelight_pro.device_trigger import (
    CONF_SUBTYPE,
    async_attach_trigger,
    async_get_triggers,
    async_validate_trigger_config,
)

from .device_trigger_helpers import register_event_device, register_switch_event_device


@pytest.mark.asyncio
async def test_device_trigger_lists_projected_event_types(hass: HomeAssistant) -> None:
    """事件型设备应向 HA 自动化暴露规范化 device triggers."""
    device_id = register_event_device(hass)

    triggers = await async_get_triggers(hass, device_id)

    assert [
        (trigger[CONF_TYPE], trigger[CONF_SUBTYPE])
        for trigger in triggers
    ] == [
        ("scene_panel", "click"),
        ("scene_panel", "hold"),
        ("scene_panel", "knob_spin"),
    ]
    assert all(trigger[CONF_PLATFORM] == "device" for trigger in triggers)
    assert all(trigger[CONF_DOMAIN] == DOMAIN for trigger in triggers)


@pytest.mark.asyncio
async def test_device_trigger_rejects_unsupported_event_type(
    hass: HomeAssistant,
) -> None:
    """未声明的事件 subtype 不能通过 device trigger 校验."""
    device_id = register_event_device(hass)

    with pytest.raises(InvalidDeviceAutomationConfig):
        await async_validate_trigger_config(
            hass,
            {
                CONF_PLATFORM: "device",
                CONF_DEVICE_ID: device_id,
                CONF_DOMAIN: DOMAIN,
                CONF_TYPE: "scene_panel",
                CONF_SUBTYPE: "double_click",
            },
        )


@pytest.mark.asyncio
async def test_device_trigger_lists_switch_component_panel_events(
    hass: HomeAssistant,
) -> None:
    """声明 panel 事件的开关组件应暴露 HA device trigger。"""
    device_id = register_switch_event_device(hass)

    triggers = await async_get_triggers(hass, device_id)

    assert [
        (trigger[CONF_TYPE], trigger[CONF_SUBTYPE])
        for trigger in triggers
    ] == [
        ("relay_switch_1", "click"),
        ("relay_switch_1", "hold"),
    ]


@pytest.mark.asyncio
async def test_attach_trigger_rejects_unsupported_event_type(
    hass: HomeAssistant,
) -> None:
    """直接 attach 未声明 subtype 时也必须拒绝，避免绕过 validate."""
    device_id = register_event_device(hass)

    with pytest.raises(InvalidDeviceAutomationConfig):
        await async_attach_trigger(
            hass,
            {
                CONF_PLATFORM: "device",
                CONF_DEVICE_ID: device_id,
                CONF_DOMAIN: DOMAIN,
                CONF_TYPE: "scene_panel",
                CONF_SUBTYPE: "double_click",
            },
            lambda variables, context=None: None,
            TriggerInfo(
                domain=DOMAIN,
                name="Unsupported scene panel event",
                home_assistant_start=False,
                trigger_data={},
                variables={},
            ),
        )
