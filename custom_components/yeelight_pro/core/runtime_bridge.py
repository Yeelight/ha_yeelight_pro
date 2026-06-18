"""Runtime push/LAN payload bridge for Yeelight Pro coordinators."""
from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable, Hashable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from hashlib import blake2b
import logging
from typing import Any

from homeassistant.core import HomeAssistant

from ..const import CONF_DEVICE_IMPORT_FILTER
from ..device_filter import normalize_device_import_filter
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
MAX_RUNTIME_PROPERTY_SAMPLE_ITEMS = 5
MAX_RUNTIME_PROPERTY_PARAM_KEYS = 12
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
    device_import_filter_enabled: bool = False
    unknown_node_samples: tuple[dict[str, Any], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        """Return diagnostics-safe aggregate counters."""
        return {
            "input_updates": self.input_updates,
            "applied_device_updates": self.applied_device_updates,
            "unknown_device_updates": self.unknown_device_updates,
            "group_updates": self.group_updates,
            "topology_node_updates": self.topology_node_updates,
            "changed": self.changed,
            "device_import_filter_enabled": self.device_import_filter_enabled,
            "unknown_node_samples": list(self.unknown_node_samples),
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
        options: Mapping[str, Any] | None = None,
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
        self._device_import_filter_enabled = _device_import_filter_enabled(options)
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
        unknown_node_samples: list[dict[str, Any]] = []
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
                if len(unknown_node_samples) < MAX_RUNTIME_PROPERTY_SAMPLE_ITEMS:
                    unknown_node_samples.append(
                        self._unknown_update_sample(update, params)
                    )
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
            device_import_filter_enabled=self._device_import_filter_enabled,
            unknown_node_samples=tuple(unknown_node_samples),
        )
        if applied or unknown or group_updates or topology_node_updates:
            _LOGGER.debug(
                "Applied Yeelight Pro runtime property updates: "
                "applied=%s unknown_nodes=%s group_updates=%s topology_node_updates=%s "
                "unknown_samples=%s",
                applied,
                unknown,
                group_updates,
                topology_node_updates,
                unknown_node_samples,
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

    def _unknown_update_sample(
        self,
        update: RuntimePropertyUpdate,
        params: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Return a redacted sample explaining why one update was not loaded."""
        matched_collections = self._matching_collections(update.node_id)
        return {
            "node_id_hash": _stable_digest(update.node_id),
            "node_type": update.node_type,
            "param_keys": _safe_param_keys(params),
            "matched_collections": matched_collections,
            "reason": _unknown_update_reason(matched_collections),
            "device_import_filter_enabled": self._device_import_filter_enabled,
        }

    def _matching_collections(self, node_id: int) -> list[str]:
        """Return loaded coordinator collections containing the node id."""
        matches: list[str] = []
        if node_id in self._devices:
            matches.append("devices")
        if node_id in self._gateways:
            matches.append("gateways")
        if node_id in self._data:
            matches.append("data")
        for name, collection in (
            ("groups", self._groups),
            ("rooms", self._rooms),
            ("areas", self._areas),
            ("houses", self._houses),
        ):
            if collection is not None and _collection_contains_node(collection, node_id):
                matches.append(name)
        return matches

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


def _device_import_filter_enabled(options: Mapping[str, Any] | None) -> bool:
    """Return whether the loaded entry has a meaningful import filter."""
    if not isinstance(options, Mapping):
        return False
    normalized = normalize_device_import_filter(options.get(CONF_DEVICE_IMPORT_FILTER))
    return normalized.enabled


def _is_group_update(update: RuntimePropertyUpdate) -> bool:
    """判断属性更新是否来自 LAN 灯组节点。"""
    return update.node_type == NODE_TYPE_GROUP


def _collection_contains_node(collection: Iterable[Mapping[str, Any]], node_id: int) -> bool:
    """Return whether a topology collection contains a node id."""
    for item in collection:
        if isinstance(item, Mapping) and coerce_device_id(item.get("id")) == node_id:
            return True
    return False


def _unknown_update_reason(matched_collections: Sequence[str]) -> str:
    """Classify an unknown update without exposing raw identifiers."""
    if "groups" in matched_collections:
        return "missing_group_node_type"
    if {"rooms", "areas", "houses"} & set(matched_collections):
        return "missing_topology_node_type"
    return "not_loaded"


def _safe_param_keys(params: Mapping[str, Any]) -> list[str]:
    """Return sorted param keys only, never param values."""
    keys = sorted(str(key) for key in params)
    return keys[:MAX_RUNTIME_PROPERTY_PARAM_KEYS]


def _stable_digest(value: Any) -> str:
    """Return a stable non-reversible identifier for diagnostics."""
    digest = blake2b(digest_size=8)
    digest.update(str(value).encode())
    return digest.hexdigest()


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
    "MAX_RUNTIME_PROPERTY_SAMPLE_ITEMS",
    "coerce_device_id",
    "property_updates_from_adapter",
    "runtime_event_dedupe_key",
]
