"""Device trigger runtime event bus matching tests."""

from __future__ import annotations

import pytest

from homeassistant.const import CONF_DEVICE_ID, CONF_DOMAIN, CONF_PLATFORM, CONF_TYPE
from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers.trigger import TriggerInfo

from custom_components.yeelight_pro.const import (
    ATTR_COMPONENT_ID,
    ATTR_EVENT_TYPE,
    ATTR_SOURCE_DEVICE_ID,
    DEVICE_EVENT_TYPE,
    DOMAIN,
)
from custom_components.yeelight_pro.device_trigger import (
    CONF_SUBTYPE,
    async_attach_trigger,
)

from .device_trigger_helpers import register_event_device, register_switch_event_device


@pytest.mark.asyncio
async def test_device_trigger_matches_runtime_event_bus_payload(
    hass: HomeAssistant,
) -> None:
    """device trigger 应匹配 runtime event bus 的稳定 payload 契约."""
    device_id = register_event_device(hass)
    calls: list[dict] = []

    remove = await async_attach_trigger(
        hass,
        {
            CONF_PLATFORM: "device",
            CONF_DEVICE_ID: device_id,
            CONF_DOMAIN: DOMAIN,
            CONF_TYPE: "scene_panel",
            CONF_SUBTYPE: "click",
        },
        lambda variables, context=None: calls.append(variables),
        TriggerInfo(
            domain=DOMAIN,
            name="Scene panel click",
            home_assistant_start=False,
            trigger_data={},
            variables={},
        ),
    )

    hass.bus.async_fire(
        DEVICE_EVENT_TYPE,
        {
            ATTR_SOURCE_DEVICE_ID: "228215",
            ATTR_COMPONENT_ID: "scene_panel",
            ATTR_EVENT_TYPE: "hold",
        },
    )
    hass.bus.async_fire(
        DEVICE_EVENT_TYPE,
        {
            ATTR_SOURCE_DEVICE_ID: "228215",
            ATTR_COMPONENT_ID: "scene_panel",
            ATTR_EVENT_TYPE: "click",
        },
        context=Context(id="trigger-context"),
    )
    await hass.async_block_till_done()

    assert len(calls) == 1
    assert calls[0]["trigger"]["event"].data[ATTR_EVENT_TYPE] == "click"
    remove()


@pytest.mark.asyncio
async def test_switch_device_trigger_matches_runtime_event_bus_payload(
    hass: HomeAssistant,
) -> None:
    """开关组件事件 trigger 应按 source/component/event 精确命中。"""
    device_id = register_switch_event_device(hass)
    calls: list[dict] = []

    remove = await async_attach_trigger(
        hass,
        {
            CONF_PLATFORM: "device",
            CONF_DEVICE_ID: device_id,
            CONF_DOMAIN: DOMAIN,
            CONF_TYPE: "relay_switch_1",
            CONF_SUBTYPE: "hold",
        },
        lambda variables, context=None: calls.append(variables),
        TriggerInfo(
            domain=DOMAIN,
            name="Switch hold",
            home_assistant_start=False,
            trigger_data={},
            variables={},
        ),
    )

    hass.bus.async_fire(
        DEVICE_EVENT_TYPE,
        {
            ATTR_SOURCE_DEVICE_ID: "228215",
            ATTR_COMPONENT_ID: "relay_switch_1",
            ATTR_EVENT_TYPE: "click",
        },
    )
    hass.bus.async_fire(
        DEVICE_EVENT_TYPE,
        {
            ATTR_SOURCE_DEVICE_ID: "228215",
            ATTR_COMPONENT_ID: "relay_switch_1",
            ATTR_EVENT_TYPE: "hold",
        },
    )
    await hass.async_block_till_done()

    assert len(calls) == 1
    assert calls[0]["trigger"]["event"].data[ATTR_EVENT_TYPE] == "hold"
    remove()
