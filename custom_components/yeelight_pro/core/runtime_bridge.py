"""Runtime push/LAN payload bridge for Yeelight Pro coordinators."""
from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable, Hashable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from hashlib import blake2b
import logging
from typing import Any

from homeassistant.core import HomeAssistant

from ..const import (
    ATTR_COMPONENT_ID,
    ATTR_EVENT_ATTRIBUTES,
    ATTR_EVENT_TYPE,
    ATTR_SOURCE_DEVICE_ID,
    DEVICE_EVENT_TYPE,
)
from ..event_support import (
    YeelightRuntimeEvent,
    infer_event_component_id,
    normalize_runtime_event_payload,
    runtime_event_to_bus_payload,
)
from .lan_topology_specs import (
    NODE_TYPE_AREA,
    NODE_TYPE_GROUP,
    NODE_TYPE_HOUSE,
    NODE_TYPE_ROOM,
)
from .runtime_state import (
    RuntimeStateStore,
    merge_runtime_state_into_group_payloads,
    merge_runtime_state_into_node_payloads,
    online_from_params,
)
from .lan_sensor_values import normalize_lan_device_params

CanonicalRebuilder = Callable[[dict[str, Any]], None]
DeviceLookup = Callable[[int], Mapping[str, Any] | None]
RuntimeEventDedupeKey = str
MAX_RUNTIME_EVENT_DEDUPE_KEYS = 256
_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RuntimePropertyUpdate:
    """已接收推送帧中的属性更新。"""

    node_id: int
    node_type: int | None
    params: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class RuntimePropertyUpdateSummary:
    """Aggregate result for diagnostics after applying property updates."""

    input_updates: int = 0
    applied_device_updates: int = 0
    unknown_device_updates: int = 0
    group_updates: int = 0
    topology_node_updates: int = 0
    changed: bool = False

    def as_dict(self) -> dict[str, Any]:
        """Return diagnostics-safe aggregate counters."""
        return {
            "input_updates": self.input_updates,
            "applied_device_updates": self.applied_device_updates,
            "unknown_device_updates": self.unknown_device_updates,
            "group_updates": self.group_updates,
            "topology_node_updates": self.topology_node_updates,
            "changed": self.changed,
        }


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
        groups: list[dict[str, Any]] | None = None,
        rooms: list[dict[str, Any]] | None = None,
        areas: list[dict[str, Any]] | None = None,
        houses: list[dict[str, Any]] | None = None,
        get_device: DeviceLookup,
        rebuild_canonical: CanonicalRebuilder,
    ) -> None:
        self._hass = hass
        self._runtime_state = runtime_state
        self._devices = devices
        self._gateways = gateways
        self._data = data
        self._groups = groups
        self._rooms = rooms
        self._areas = areas
        self._houses = houses
        self._get_device = get_device
        self._rebuild_canonical = rebuild_canonical
        self.last_apply_summary = RuntimePropertyUpdateSummary()

    def apply_property_updates(
        self,
        updates: Sequence[RuntimePropertyUpdate],
    ) -> bool:
        """合并属性更新，返回是否实际写入过运行时状态。"""
        changed = False
        input_updates = 0
        applied = 0
        unknown = 0
        group_updates = 0
        topology_node_updates = 0
        for update in updates:
            input_updates += 1
            if not update.params:
                continue
            params = self._normalized_params(update)
            if _is_group_update(update):
                group_updates += 1
                changed = (
                    self._groups is not None
                    and merge_runtime_state_into_group_payloads(
                        self._groups,
                        group_id=update.node_id,
                        params=params,
                        online=online_from_params(params),
                    )
                ) or changed
                continue
            collection = self._topology_node_collection(update)
            if collection is not None:
                topology_node_updates += 1
                changed = merge_runtime_state_into_node_payloads(
                    collection,
                    node_id=update.node_id,
                    params=params,
                    online=online_from_params(params),
                ) or changed
                continue
            if self._loaded_payload(update.node_id) is None:
                unknown += 1
                self._runtime_state.store_update(
                    update.node_id,
                    params,
                    devices=self._devices,
                    gateways=self._gateways,
                    data=self._data,
                    rebuild_canonical=self._rebuild_canonical,
                    groups=self._groups,
                )
                changed = True
                continue
            changed = True
            applied += 1
            self._runtime_state.store_update(
                update.node_id,
                params,
                devices=self._devices,
                gateways=self._gateways,
                data=self._data,
                rebuild_canonical=self._rebuild_canonical,
                groups=self._groups,
            )
        self.last_apply_summary = RuntimePropertyUpdateSummary(
            input_updates=input_updates,
            applied_device_updates=applied,
            unknown_device_updates=unknown,
            group_updates=group_updates,
            topology_node_updates=topology_node_updates,
            changed=changed,
        )
        if applied or unknown or group_updates or topology_node_updates:
            _LOGGER.debug(
                "Applied Yeelight Pro runtime property updates: "
                "applied=%s unknown_nodes=%s group_updates=%s topology_node_updates=%s",
                applied,
                unknown,
                group_updates,
                topology_node_updates,
            )
        return changed

    def _normalized_params(self, update: RuntimePropertyUpdate) -> dict[str, Any]:
        """Return params normalized against the loaded device metadata."""
        device = self._loaded_payload(update.node_id)
        lan_type = device.get("lan_type") if isinstance(device, Mapping) else None
        return normalize_lan_device_params(update.params, lan_type=lan_type)

    def _loaded_payload(self, node_id: int) -> Mapping[str, Any] | None:
        """Return the currently loaded payload for a property update."""
        for source in (self._devices, self._gateways, self._data):
            payload = source.get(node_id)
            if isinstance(payload, Mapping):
                return payload
        return None

    def _topology_node_collection(
        self,
        update: RuntimePropertyUpdate,
    ) -> list[dict[str, Any]] | None:
        """Return the topology collection for room/area/house property updates."""
        if update.node_type == NODE_TYPE_ROOM:
            return self._rooms
        if update.node_type == NODE_TYPE_AREA:
            return self._areas
        if update.node_type == NODE_TYPE_HOUSE:
            return self._houses
        return None

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


class RuntimeEventDeduper:
    """Bounded duplicate guard for already sanitized runtime event payloads."""

    def __init__(self, *, max_keys: int = MAX_RUNTIME_EVENT_DEDUPE_KEYS) -> None:
        """Initialize the deduper without storing raw event payloads."""
        if max_keys <= 0:
            raise ValueError("max_keys must be positive")
        self._max_keys = max_keys
        self._seen: OrderedDict[RuntimeEventDedupeKey, None] = OrderedDict()

    def filter_new_payloads(
        self,
        payloads: Iterable[Mapping[str, Any]],
    ) -> list[Mapping[str, Any]]:
        """Return payloads whose message/event key has not been seen before."""
        return [payload for payload in payloads if not self.is_duplicate(payload)]

    def is_duplicate(self, payload: Mapping[str, Any]) -> bool:
        """Return whether payload repeats a bounded message/event key."""
        key = runtime_event_dedupe_key(payload)
        if key is None:
            return False
        if key in self._seen:
            self._seen.move_to_end(key)
            return True
        self._seen[key] = None
        while len(self._seen) > self._max_keys:
            self._seen.popitem(last=False)
        return False


def runtime_event_dedupe_key(
    payload: Mapping[str, Any],
) -> RuntimeEventDedupeKey | None:
    """Build a non-reversible duplicate key for WebSocket message events."""
    attributes = payload.get(ATTR_EVENT_ATTRIBUTES)
    if not isinstance(attributes, Mapping):
        return None
    message_id = attributes.get("message_id")
    if message_id in (None, ""):
        return None

    parts: tuple[Hashable, ...] = (
        str(message_id),
        str(payload.get(ATTR_SOURCE_DEVICE_ID, "")),
        str(payload.get(ATTR_COMPONENT_ID, "")),
        str(payload.get(ATTR_EVENT_TYPE, "")),
        str(attributes.get("raw_event", "")),
    )
    digest = blake2b(digest_size=16)
    for part in parts:
        digest.update(str(part).encode())
        digest.update(b"\0")
    return digest.hexdigest()


def property_updates_from_adapter(
    updates: Sequence[Any],
) -> list[RuntimePropertyUpdate]:
    """把 push/LAN adapter 的更新对象转换为 bridge 输入。"""
    return [
        RuntimePropertyUpdate(
            node_id=update.node_id,
            node_type=getattr(update, "node_type", None),
            params=update.params,
        )
        for update in updates
    ]


def _is_group_update(update: RuntimePropertyUpdate) -> bool:
    """判断属性更新是否来自 LAN 灯组节点。"""
    return update.node_type == NODE_TYPE_GROUP


def coerce_device_id(value: Any) -> int | None:
    """将事件 source_device_id 转换为运行时设备键。"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


__all__ = [
    "MAX_RUNTIME_EVENT_DEDUPE_KEYS",
    "RuntimeEventDeduper",
    "RuntimeEventDedupeKey",
    "RuntimePayloadBridge",
    "RuntimePropertyUpdate",
    "RuntimePropertyUpdateSummary",
    "coerce_device_id",
    "property_updates_from_adapter",
    "runtime_event_dedupe_key",
]
