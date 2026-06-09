"""Runtime event normalization and dispatch tests."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.yeelight_pro.const import (
    ATTR_COMPONENT_ID,
    ATTR_EVENT_ATTRIBUTES,
    ATTR_EVENT_TYPE,
    ATTR_SOURCE_DEVICE_ID,
    DEVICE_EVENT_TYPE,
)
from custom_components.yeelight_pro.core.coordinator import YeelightProCoordinator
from custom_components.yeelight_pro.event_support import (
    normalize_runtime_event_payload,
    runtime_event_to_bus_payload,
)


def test_normalize_runtime_event_payload_uses_supported_aliases() -> None:
    """运行时事件入口应复用 IoT 事件别名归一化."""
    event = normalize_runtime_event_payload(
        {
            ATTR_SOURCE_DEVICE_ID: 12345,
            ATTR_COMPONENT_ID: "scene_button",
            ATTR_EVENT_TYPE: "door open",
            ATTR_EVENT_ATTRIBUTES: {"value": 1},
        }
    )

    assert event.source_device_id == "12345"
    assert event.component_id == "scene_button"
    assert event.event_type == "door_open"
    assert event.event_attributes == {"value": 1}
    assert runtime_event_to_bus_payload(event) == {
        ATTR_SOURCE_DEVICE_ID: "12345",
        ATTR_COMPONENT_ID: "scene_button",
        ATTR_EVENT_TYPE: "door_open",
        ATTR_EVENT_ATTRIBUTES: {"value": 1},
    }


def test_normalize_runtime_event_payload_rejects_missing_event_type() -> None:
    """空事件类型不能进入 HA 事件总线."""
    with pytest.raises(HomeAssistantError):
        normalize_runtime_event_payload(
            {
                ATTR_SOURCE_DEVICE_ID: "device_1",
                ATTR_COMPONENT_ID: "button",
                ATTR_EVENT_TYPE: "",
            }
        )


def test_normalize_runtime_event_payload_rejects_missing_source_device_id() -> None:
    """空 source_device_id 不能进入 HA 事件总线."""
    with pytest.raises(HomeAssistantError):
        normalize_runtime_event_payload(
            {
                ATTR_SOURCE_DEVICE_ID: "",
                ATTR_COMPONENT_ID: "button",
                ATTR_EVENT_TYPE: "click",
            }
        )


def test_normalize_runtime_event_payload_allows_unknown_slug_fallback() -> None:
    """未知非空事件名允许稳定 slug 化，以兼容产品 schema 新事件."""
    event = normalize_runtime_event_payload(
        {
            ATTR_SOURCE_DEVICE_ID: "device_1",
            ATTR_COMPONENT_ID: "button",
            ATTR_EVENT_TYPE: "custom vendor event",
        }
    )

    assert event.event_type == "custom_vendor_event"


@pytest.mark.asyncio
async def test_coordinator_dispatches_runtime_event_to_ha_bus(
    hass: HomeAssistant,
) -> None:
    """coordinator 应成为 debug service 和未来订阅入口的统一事件桥."""
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=MagicMock(),
        house_id=12345,
    )
    events: list[dict] = []
    hass.bus.async_listen(DEVICE_EVENT_TYPE, lambda event: events.append(event.data))

    runtime_event = await coordinator.async_handle_runtime_event(
        {
            ATTR_SOURCE_DEVICE_ID: 12345,
            ATTR_COMPONENT_ID: "scene_button",
            ATTR_EVENT_TYPE: "click",
            ATTR_EVENT_ATTRIBUTES: {"press": 1},
        }
    )
    await hass.async_block_till_done()

    assert runtime_event.event_type == "click"
    assert events == [
        {
            ATTR_SOURCE_DEVICE_ID: "12345",
            ATTR_COMPONENT_ID: "scene_button",
            ATTR_EVENT_TYPE: "click",
            ATTR_EVENT_ATTRIBUTES: {"press": 1},
        }
    ]
