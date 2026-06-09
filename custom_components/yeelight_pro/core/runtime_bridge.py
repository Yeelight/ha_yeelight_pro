"""Runtime push/LAN payload bridge for Yeelight Pro coordinators."""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from homeassistant.core import HomeAssistant

from ..const import (
    ATTR_SOURCE_DEVICE_ID,
    DEVICE_EVENT_TYPE,
)
from ..event_support import (
    YeelightRuntimeEvent,
    infer_event_component_id,
    normalize_runtime_event_payload,
    runtime_event_to_bus_payload,
)
from .runtime_state import RuntimeStateStore

CanonicalRebuilder = Callable[[dict[str, Any]], None]
DeviceLookup = Callable[[int], Mapping[str, Any] | None]


@dataclass(frozen=True, slots=True)
class RuntimePropertyUpdate:
    """已接收推送帧中的属性更新。"""

    node_id: int
    params: Mapping[str, Any]


class RuntimePayloadBridge:
    """把已收到的云端/LAN payload 接入运行时状态和 HA 事件总线。"""

    def __init__(
        self,
        *,
        hass: HomeAssistant,
        runtime_state: RuntimeStateStore,
        devices: Mapping[int, dict[str, Any]],
        gateways: Mapping[int, dict[str, Any]],
        data: Mapping[int, Any],
        get_device: DeviceLookup,
        rebuild_canonical: CanonicalRebuilder,
    ) -> None:
        self._hass = hass
        self._runtime_state = runtime_state
        self._devices = devices
        self._gateways = gateways
        self._data = data
        self._get_device = get_device
        self._rebuild_canonical = rebuild_canonical

    def apply_property_updates(
        self,
        updates: Sequence[RuntimePropertyUpdate],
    ) -> bool:
        """合并属性更新，返回是否实际写入过运行时状态。"""
        changed = False
        for update in updates:
            if not update.params:
                continue
            changed = True
            self._runtime_state.store_update(
                update.node_id,
                update.params,
                devices=self._devices,
                gateways=self._gateways,
                data=self._data,
                rebuild_canonical=self._rebuild_canonical,
            )
        return changed

    async def dispatch_event_payloads(
        self,
        payloads: Sequence[Mapping[str, Any]],
    ) -> list[YeelightRuntimeEvent]:
        """推断事件组件并转发到 Home Assistant 事件总线。"""
        events: list[YeelightRuntimeEvent] = []
        for payload in payloads:
            device_id = coerce_device_id(payload.get(ATTR_SOURCE_DEVICE_ID))
            device_payload = self._get_device(device_id) if device_id is not None else None
            events.append(
                self.dispatch_runtime_event(
                    infer_event_component_id(payload, device_payload)
                )
            )
        return events

    def dispatch_runtime_event(
        self,
        payload: Mapping[str, Any],
    ) -> YeelightRuntimeEvent:
        """规范化运行时事件并发射 HA bus 事件。"""
        event = normalize_runtime_event_payload(payload)
        self._hass.bus.async_fire(
            DEVICE_EVENT_TYPE,
            runtime_event_to_bus_payload(event),
        )
        return event


def property_updates_from_adapter(
    updates: Sequence[Any],
) -> list[RuntimePropertyUpdate]:
    """把 push/LAN adapter 的更新对象转换为 bridge 输入。"""
    return [
        RuntimePropertyUpdate(node_id=update.node_id, params=update.params)
        for update in updates
    ]


def coerce_device_id(value: Any) -> int | None:
    """将事件 source_device_id 转换为运行时设备键。"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


__all__ = [
    "RuntimePayloadBridge",
    "RuntimePropertyUpdate",
    "coerce_device_id",
    "property_updates_from_adapter",
]
