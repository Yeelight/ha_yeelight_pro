"""Device trigger 共享测试 helper."""

from __future__ import annotations

from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.yeelight_pro.const import DOMAIN


def event_device_payload(*, switch_component: bool = False) -> dict:
    """返回带 canonical event metadata 的最小设备载荷."""
    if switch_component:
        return {
            "id": 228215,
            "device_id": 228215,
            "category": "relay_switch",
            "type": "switch",
            "ha_product_model": {
                "product": {
                    "model_id": "switch-model",
                    "category": "relay_switch",
                    "name": "Switch Input",
                    "manufacturer": "Yeelight",
                },
                "components": [
                    {
                        "component_id": "relay_switch_1",
                        "cid": 20,
                        "name": "switch control",
                        "category": "relay_switch",
                        "component_type": "normal",
                        "events": [
                            {"event_id": 1, "name": "panel.click"},
                            {"event_id": 2, "name": "panel.hold"},
                        ],
                    }
                ],
            },
        }
    return {
        "id": 228215,
        "device_id": 228215,
        "category": "scene_panel",
        "type": "event",
        "ha_product_model": {
            "product": {
                "model_id": "scene-panel-model",
                "category": "scene_panel",
                "name": "Scene Panel",
                "manufacturer": "Yeelight",
            },
            "components": [
                {
                    "component_id": "scene_panel",
                    "name": "Scene Panel",
                    "category": "scene_panel",
                    "component_type": "normal",
                    "events": [
                        {"event_id": 1, "name": "click"},
                        {"event_id": 2, "name": "hold"},
                        {"event_id": 10, "name": "knob spin"},
                        {"name": "multi spin"},
                        {"name": "absolut spin"},
                    ],
                }
            ],
        },
    }


def register_event_device(hass: HomeAssistant) -> str:
    """注册 Yeelight Pro 事件源设备和 fake runtime coordinator."""
    return _register_device(hass, event_device_payload(), name="Scene Panel")


def register_switch_event_device(hass: HomeAssistant) -> str:
    """注册声明 panel 事件的 relay switch 设备."""
    return _register_device(
        hass,
        event_device_payload(switch_component=True),
        name="Switch Input",
    )


def _register_device(
    hass: HomeAssistant,
    payload: dict,
    *,
    name: str,
) -> str:
    """注册 HA device registry 设备并安装 coordinator double."""
    MockConfigEntry(domain=DOMAIN, entry_id="entry-1").add_to_hass(hass)
    device_registry = dr.async_get(hass)
    device_entry = device_registry.async_get_or_create(
        config_entry_id="entry-1",
        identifiers={(DOMAIN, "device:228215")},
        name=name,
    )
    coordinator = MagicMock()
    coordinator.get_device.return_value = payload
    hass.data[DOMAIN] = {"entry-1": {"coordinator": coordinator}}
    return device_entry.id
