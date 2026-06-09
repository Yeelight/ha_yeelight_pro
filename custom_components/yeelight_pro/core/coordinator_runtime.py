"""Runtime payload handling for Yeelight Pro coordinators."""

from __future__ import annotations

from typing import Any, Mapping, Protocol

from homeassistant.core import HomeAssistant

from ..event_support import YeelightRuntimeEvent
from ..lan_payload import lan_event_payloads, lan_property_updates
from ..push import push_event_payloads, push_property_updates
from .runtime_bridge import RuntimePayloadBridge, property_updates_from_adapter
from .runtime_state import RuntimeStateStore


class _RuntimeCoordinator(Protocol):
    """Runtime bridge attributes provided by YeelightProCoordinator."""

    hass: HomeAssistant
    data: Any
    devices: Mapping[int, dict[str, Any]]
    gateways: Mapping[int, dict[str, Any]]
    _runtime_state: RuntimeStateStore
    _device_payload_builder: Any

    def get_device(self, device_id: int) -> dict[str, Any] | None:
        """Return the current runtime device payload."""

    def async_update_listeners(self) -> None:
        """Notify Home Assistant coordinator listeners."""


class CoordinatorRuntimeMixin:
    """Handle already received push/LAN/runtime event payloads."""

    async def async_handle_runtime_event(
        self: _RuntimeCoordinator,
        payload: Mapping[str, Any],
    ) -> YeelightRuntimeEvent:
        """规范化运行时事件并转发到 HA 事件总线."""
        return _runtime_bridge(self).dispatch_runtime_event(payload)

    async def async_handle_push_payload(
        self: _RuntimeCoordinator,
        payload: Mapping[str, Any],
    ) -> list[YeelightRuntimeEvent]:
        """处理已接收的 Yeelight 推送消息，不负责建立网络连接."""
        bridge = _runtime_bridge(self)
        if bridge.apply_property_updates(
            property_updates_from_adapter(push_property_updates(payload))
        ):
            self.async_update_listeners()

        return await bridge.dispatch_event_payloads(push_event_payloads(payload))

    async def async_handle_lan_payload(
        self: _RuntimeCoordinator,
        payload: Mapping[str, Any],
    ) -> list[YeelightRuntimeEvent]:
        """处理已接收的 LAN 网关推送帧，不负责 UDP/TCP 连接。"""
        bridge = _runtime_bridge(self)
        if bridge.apply_property_updates(
            property_updates_from_adapter(lan_property_updates(payload))
        ):
            self.async_update_listeners()

        return await bridge.dispatch_event_payloads(lan_event_payloads(payload))


def _runtime_bridge(coordinator: _RuntimeCoordinator) -> RuntimePayloadBridge:
    """构造当前 coordinator 快照对应的运行时 payload bridge."""
    runtime_data = coordinator.data if isinstance(coordinator.data, Mapping) else {}
    return RuntimePayloadBridge(
        hass=coordinator.hass,
        runtime_state=coordinator._runtime_state,
        devices=coordinator.devices,
        gateways=coordinator.gateways,
        data=runtime_data,
        get_device=coordinator.get_device,
        rebuild_canonical=(
            coordinator._device_payload_builder.attach_canonical_models_if_available
        ),
    )
