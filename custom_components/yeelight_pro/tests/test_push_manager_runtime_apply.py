"""PushManager runtime-apply tests with a real coordinator."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.core.coordinator import YeelightProCoordinator
from custom_components.yeelight_pro.core.device_payload import DevicePayloadBuilder
from custom_components.yeelight_pro.light import YeelightProLight
from custom_components.yeelight_pro.push_manager import PushManager

from .push_manager_helpers import FakeTransport, base_health


@pytest.mark.asyncio
async def test_push_manager_applies_business_prop_payload_immediately(
    hass: HomeAssistant,
) -> None:
    """收到业务 prop 帧时应立即更新 coordinator 状态并通知实体监听器."""
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=MagicMock(),
        house_id=12345,
    )
    coordinator.devices = {
        228216: {
            "id": 228216,
            "device_id": 228216,
            "name": "Push Lamp",
            "category": "light",
            "type": "light",
            "online": True,
            "pid": 100,
            "product_schema": _lamp_schema(),
            "params": {"p": True, "l": 20},
        }
    }
    DevicePayloadBuilder().attach_canonical_models_if_available(
        coordinator.devices[228216]
    )
    coordinator.data = coordinator.devices
    light = YeelightProLight(coordinator, 228216)
    updates = 0

    def _listener() -> None:
        nonlocal updates
        updates += 1

    remove_listener = coordinator.async_add_listener(
        _listener,
        ("device", "228216"),
    )
    transport = FakeTransport()
    manager = PushManager(coordinator, transport)

    await manager.async_start()
    try:
        result = await transport.emit({
            "type": "prop",
            "nodes": [
                {
                    "id": 228216,
                    "nt": 2,
                    "params": {"p": False, "l": 80},
                }
            ],
        })

        assert result == []
        assert updates == 1
        assert coordinator._runtime_state.overrides[228216]["params"] == {
            "p": False,
            "l": 80,
        }
        refreshed = coordinator.get_device(228216)
        assert refreshed is not None
        assert refreshed["params"]["p"] is False
        assert refreshed["params"]["l"] == 80
        assert light.is_on is False
        assert light.brightness == 203
        assert manager.health.as_dict() == base_health(
            running=True,
            started_count=1,
            handled_payloads=1,
            changed_payloads=1,
            property_updates=1,
            applied_property_updates=1,
            affected_context_count=1,
            affected_context_samples=[
                {
                    "kind": "device",
                    "node_id_hash": "5fecf32fca76146d",
                }
            ],
            routed_property_updates=1,
            last_applied_node_samples=[
                {
                    "node_id_hash": "5fecf32fca76146d",
                    "node_type": 2,
                    "param_keys": ["l", "p"],
                    "matched_collections": ["devices", "data"],
                }
            ],
            recent_applied_node_samples=[
                {
                    "node_id_hash": "5fecf32fca76146d",
                    "node_type": 2,
                    "param_keys": ["l", "p"],
                    "matched_collections": ["devices", "data"],
                }
            ],
            last_property_update_count=1,
            last_applied_property_update_count=1,
            last_routed_property_update_count=1,
            last_payload_changed=True,
            last_payload_handle_duration_ms=manager.health.last_payload_handle_duration_ms,
            last_listener_notification_count=1,
            last_listener_context_count=1,
            last_payload_type="prop",
            last_payload_at=manager.health.last_payload_at,
        )
        assert manager.health.last_payload_at is not None
        assert manager.health.last_payload_handle_duration_ms is not None
        assert manager.health.last_payload_handle_duration_ms >= 0
    finally:
        remove_listener()


def _lamp_schema() -> dict:
    """构造 PushManager 业务帧测试用灯具 schema."""
    return {
        "pid": 100,
        "name": "Push Lamp Product",
        "category": "light",
        "components": [
            {
                "cid": 4,
                "name": "brightness light",
                "type": 0,
                "category": "light",
                "index": 1,
                "properties": [
                    {"propId": "p", "operators": ["set"]},
                    {"propId": "l", "operators": ["set"]},
                ],
            }
        ],
    }
