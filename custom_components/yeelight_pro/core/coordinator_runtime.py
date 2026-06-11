"""Runtime payload handling for Yeelight Pro coordinators."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Mapping, Protocol

from homeassistant.core import HomeAssistant

from ..event_support import YeelightRuntimeEvent
from ..lan_payload import (
    lan_event_payloads,
    lan_property_updates,
    lan_scene_updates,
    lan_topology_update,
)
from ..push import push_event_payloads, push_property_updates
from .runtime_bridge import (
    RuntimeEventDeduper,
    RuntimePayloadBridge,
    property_updates_from_adapter,
)
from .runtime_state import RuntimeStateStore

_LOGGER = logging.getLogger(__name__)


class _RuntimeCoordinator(Protocol):
    """Runtime bridge attributes provided by YeelightProCoordinator."""

    hass: HomeAssistant
    data: Any
    devices: Mapping[int, dict[str, Any]]
    gateways: Mapping[int, dict[str, Any]]
    _runtime_state: RuntimeStateStore
    _push_event_deduper: RuntimeEventDeduper
    _device_payload_builder: Any

    def get_device(self, device_id: int | str) -> dict[str, Any] | None:
        """Return the current runtime device payload."""

    def async_update_listeners(self) -> None:
        """Notify Home Assistant coordinator listeners."""

    def async_refresh_from_lan_topology(self) -> Any:
        """Schedule or perform a refresh after LAN topology changes."""

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
        if bridge.apply_property_updates(
            property_updates_from_adapter(push_property_updates(payload))
        ):
            self.async_update_listeners()

        return await bridge.dispatch_event_payloads(
            self._push_event_deduper.filter_new_payloads(
                push_event_payloads(payload)
            )
        )

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
        if bridge.apply_property_updates(
            property_updates_from_adapter(lan_property_updates(payload))
        ):
            self.async_update_listeners()

        # 场景状态同步
        scene_updates = lan_scene_updates(payload)
        if scene_updates:
            for update in scene_updates:
                _LOGGER.debug(
                    "LAN scene state: id=%d state=%s",
                    update.scene_id,
                    update.state,
                )

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
    from ..utils import to_int

    nodes = payload.get("nodes")
    if not isinstance(nodes, list):
        return

    new_devices: dict[int, dict[str, Any]] = {}
    new_scenes: list[dict[str, Any]] = []
    new_groups: list[dict[str, Any]] = []
    new_rooms: list[dict[str, Any]] = []

    for node in nodes:
        if not isinstance(node, Mapping):
            continue
        node_id = to_int(node.get("id"))
        node_type = to_int(node.get("nt"))
        if node_id is None or node_type is None:
            continue

        name = str(node.get("n", ""))
        device_type = to_int(node.get("type"))

        if node_type == 2:
            # Mesh 子设备 → 设备实体
            device_payload: dict[str, Any] = {
                "id": node_id,
                "name": name,
                "type": device_type,
                "node_type": node_type,
                "online": True,
                "params": {},
            }
            # 保留拓扑扩展字段
            for field in ("ch_num", "cids", "roomid", "pid"):
                if field in node:
                    device_payload[field] = node[field]
            new_devices[node_id] = device_payload

        elif node_type == 4:
            # Mesh 灯组
            new_groups.append({
                "id": node_id,
                "name": name,
                "type": device_type,
                "node_type": node_type,
            })

        elif node_type == 6:
            # 情景
            new_scenes.append({
                "id": node_id,
                "name": name,
            })

        elif node_type == 1:
            # 房间
            new_rooms.append({
                "id": node_id,
                "name": name,
            })

    # 更新 coordinator 状态
    if new_devices:
        coordinator.devices = new_devices  # type: ignore[assignment]
        # 同步 data 属性（DataUpdateCoordinator.data 由 _async_update_data 设置）
        coordinator.data = new_devices  # type: ignore[assignment]
    if new_scenes:
        coordinator.scenes = new_scenes  # type: ignore[assignment]
    if new_groups:
        coordinator.groups = new_groups  # type: ignore[assignment]
    if new_rooms:
        coordinator.rooms = new_rooms  # type: ignore[assignment]

    _LOGGER.info(
        "LAN topology applied: %d devices, %d groups, %d scenes, %d rooms",
        len(new_devices),
        len(new_groups),
        len(new_scenes),
        len(new_rooms),
    )


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
