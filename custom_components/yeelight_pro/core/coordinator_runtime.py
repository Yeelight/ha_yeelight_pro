"""Runtime payload handling for Yeelight Pro coordinators."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Mapping, Protocol

from homeassistant.core import HomeAssistant

from ..event_support import YeelightRuntimeEvent
from ..identity import apply_identity_scope_to_device_maps
from ..lan_payload import (
    LanSceneStateUpdate,
    lan_event_payloads,
    lan_property_updates,
    lan_scene_updates,
    lan_topology_update,
)
from ..utils import to_int
from ..push import push_event_payloads, push_property_updates
from .runtime_bridge import (
    RuntimeEventDeduper,
    RuntimePayloadBridge,
    RuntimePropertyUpdateSummary,
    property_updates_from_adapter,
)
from .lan_topology_payload import build_lan_topology_payloads
from .runtime_state import RuntimeStateStore

_LOGGER = logging.getLogger(__name__)


class _RuntimeCoordinator(Protocol):
    """Runtime bridge attributes provided by YeelightProCoordinator."""

    hass: HomeAssistant
    data: Any
    devices: Mapping[int, dict[str, Any]]
    gateways: Mapping[int, dict[str, Any]]
    groups: list[dict[str, Any]]
    houses: list[dict[str, Any]]
    rooms: list[dict[str, Any]]
    areas: list[dict[str, Any]]
    scenes: list[dict[str, Any]]
    _runtime_state: RuntimeStateStore
    _push_event_deduper: RuntimeEventDeduper
    last_push_property_summary: RuntimePropertyUpdateSummary
    last_push_event_count: int
    _device_payload_builder: Any

    def get_device(self, device_id: int | str) -> dict[str, Any] | None:
        """Return the current runtime device payload."""

    def async_update_listeners(self, contexts: Any = None) -> None:
        """Notify Home Assistant coordinator listeners."""

    def async_refresh_from_lan_topology(self) -> Any:
        """Schedule or perform a refresh after LAN topology changes."""

    def _update_topology_generation(self) -> None:
        """更新 LAN 拓扑快照后的拓扑代数。"""

    async def _async_refresh_coordinator_data(self) -> None:
        """Refresh coordinator data from the backing API."""


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
        changed = bridge.apply_property_updates(
            property_updates_from_adapter(push_property_updates(payload))
        )
        self.last_push_property_summary = bridge.last_apply_summary
        if changed:
            self.async_update_listeners(bridge.last_apply_summary.affected_contexts)

        event_payloads = bridge.resolve_event_payloads(push_event_payloads(payload))
        events = await bridge.dispatch_event_payloads(
            self._push_event_deduper.filter_new_payloads(event_payloads)
        )
        self.last_push_event_count = len(events)
        return events

    async def async_handle_lan_payload(
        self: _RuntimeCoordinator,
        payload: Mapping[str, Any],
    ) -> list[YeelightRuntimeEvent]:
        """处理已接收的 LAN 网关推送帧，不负责 UDP/TCP 连接。"""
        # 拓扑推送：设备增删、分组变化、改名等
        topology = lan_topology_update(payload)
        if topology is not None:
            _LOGGER.info(
                "LAN topology push received (%d nodes), updating coordinator state",
                topology.node_count,
            )
            # 直接从拓扑消息提取设备和场景数据更新 coordinator
            _apply_lan_topology_to_coordinator(self, payload)
            self.async_update_listeners()
            return []

        bridge = _runtime_bridge(self)
        changed = bridge.apply_property_updates(
            property_updates_from_adapter(lan_property_updates(payload))
        )

        # 场景状态同步；同一帧内的设备/场景变化合并成一次 HA 状态通知。
        scene_updates = lan_scene_updates(payload)
        scene_changed = False
        if scene_updates:
            scene_changed = _apply_lan_scene_updates_to_coordinator(self, scene_updates)
            changed = scene_changed or changed
            for update in scene_updates:
                _LOGGER.debug(
                    "LAN scene state: id=%d state=%s",
                    update.scene_id,
                    update.state,
                )

        if changed:
            contexts = bridge.last_apply_summary.affected_contexts
            self.async_update_listeners(None if scene_changed else contexts)

        return await bridge.dispatch_event_payloads(lan_event_payloads(payload))

    async def async_refresh_from_lan_topology(
        self: _RuntimeCoordinator,
    ) -> None:
        """由 LAN 拓扑推送触发的延迟刷新，避免频繁请求。"""
        await asyncio.sleep(2)  # 合并连续拓扑变更
        await self._async_refresh_coordinator_data()

    async def _async_refresh_coordinator_data(self: _RuntimeCoordinator) -> None:
        """触发 coordinator 数据刷新（由子类实现）。"""
        # 默认实现：请求一次完整的 coordinator 刷新
        # 子类可以覆盖此方法提供更精确的拓扑增量更新
        pass


def _apply_lan_topology_to_coordinator(
    coordinator: _RuntimeCoordinator,
    payload: Mapping[str, Any],
) -> None:
    """从 LAN 拓扑消息直接更新 coordinator 的设备和场景数据。

    LAN-only 模式下 coordinator 没有云端客户端，设备数据完全来自拓扑推送。
    """
    nodes = payload.get("nodes")
    if not isinstance(nodes, list):
        return

    topology_payloads = build_lan_topology_payloads(
        nodes,
        builder=coordinator._device_payload_builder,
        apply_runtime_overrides=coordinator._runtime_state.apply_to_device,
    )

    apply_identity_scope_to_device_maps(
        entry_data=getattr(coordinator, "entry_data", None),
        house_id=getattr(coordinator, "house_id", None),
        devices=topology_payloads.devices,
    )

    # LAN topology 是网关当前拓扑快照，空集合也要同步以便 registry cleanup 生效。
    coordinator.devices = topology_payloads.devices  # type: ignore[assignment]
    coordinator.data = topology_payloads.devices  # type: ignore[assignment]
    coordinator.scenes = topology_payloads.scenes  # type: ignore[assignment]
    coordinator.groups = topology_payloads.groups  # type: ignore[assignment]
    coordinator.houses = topology_payloads.houses  # type: ignore[assignment]
    coordinator.rooms = topology_payloads.rooms  # type: ignore[assignment]
    coordinator.areas = topology_payloads.areas  # type: ignore[assignment]
    coordinator._update_topology_generation()

    _LOGGER.info(
        "LAN topology applied: %d devices, %d groups, %d scenes, %d rooms, %d areas, %d houses",
        len(topology_payloads.devices),
        len(topology_payloads.groups),
        len(topology_payloads.scenes),
        len(topology_payloads.rooms),
        len(topology_payloads.areas),
        len(topology_payloads.houses),
    )


def _apply_lan_scene_updates_to_coordinator(
    coordinator: _RuntimeCoordinator,
    updates: list[LanSceneStateUpdate],
) -> bool:
    """合并 LAN 场景状态到 coordinator 场景缓存。"""
    if not updates:
        return False

    scenes_by_id: dict[int, dict[str, Any]] = {}
    for scene in coordinator.scenes:
        if not isinstance(scene, Mapping):
            continue
        scene_id = to_int(scene.get("id"))
        if scene_id is None:
            continue
        scenes_by_id[scene_id] = dict(scene)

    changed = False
    for update in updates:
        scene = scenes_by_id.get(update.scene_id, {"id": update.scene_id})
        if update.name and scene.get("name") != update.name:
            scene["name"] = update.name
            changed = True
        params = scene.get("params")
        params = dict(params) if isinstance(params, Mapping) else {}
        if scene.get("state") != update.state:
            scene["state"] = update.state
            changed = True
        if params.get("state") != update.state:
            params["state"] = update.state
            scene["params"] = params
            changed = True
        scenes_by_id[update.scene_id] = scene

    if not changed:
        return False
    coordinator.scenes = list(scenes_by_id.values())  # type: ignore[assignment]
    return True


def _runtime_bridge(coordinator: _RuntimeCoordinator) -> RuntimePayloadBridge:
    """构造当前 coordinator 快照对应的运行时 payload bridge."""
    runtime_data = coordinator.data if isinstance(coordinator.data, Mapping) else {}
    return RuntimePayloadBridge(
        hass=coordinator.hass,
        runtime_state=coordinator._runtime_state,
        devices=coordinator.devices,
        gateways=coordinator.gateways,
        data=runtime_data,
        groups=coordinator.groups,
        rooms=coordinator.rooms,
        areas=coordinator.areas,
        houses=coordinator.houses,
        options=getattr(coordinator, "options", {}),
        get_device=coordinator.get_device,
        rebuild_canonical=(
            coordinator._device_payload_builder.attach_canonical_models_if_available
        ),
    )
