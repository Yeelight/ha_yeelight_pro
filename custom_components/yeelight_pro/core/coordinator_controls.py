"""Control routing for Yeelight Pro coordinators."""

from __future__ import annotations

from typing import Any, Mapping, Protocol

from .commands import (
    async_control_device as async_execute_control_device,
    async_control_group as async_execute_control_group,
    async_control_node as async_execute_control_node,
    async_execute_scene as async_execute_scene_command,
    async_toggle_device as async_execute_toggle_device,
)
from .device_payload import DevicePayloadBuilder
from .exceptions import CommandError, DeviceNotFoundError
from .lan_control import (
    async_try_lan_action_device,
    async_try_lan_control_device,
    async_try_lan_control_group,
    async_try_lan_control_node,
    async_try_lan_execute_scene,
    async_try_lan_toggle_device,
    lan_runtime_connected,
)
from .runtime_state import (
    RuntimeStateStore,
    merge_runtime_state_into_group_payloads,
    merge_runtime_state_into_node_payloads,
)


class _ControlCoordinator(Protocol):
    """Control attributes provided by YeelightProCoordinator."""

    client: Any
    data: Any
    devices: dict[int, dict[str, Any]]
    gateways: dict[int, dict[str, Any]]
    groups: list[dict[str, Any]]
    rooms: list[dict[str, Any]]
    areas: list[dict[str, Any]]
    houses: list[dict[str, Any]]
    house_id: int
    _device_payload_builder: DevicePayloadBuilder
    _lan_runtime: Any | None
    _runtime_state: RuntimeStateStore

    def get_device(self, device_id: int | str) -> dict[str, Any] | None:
        """Return a device payload by id."""

    def async_update_listeners(self) -> None:
        """Notify Home Assistant coordinator listeners."""

    async def async_request_refresh(self) -> None:
        """Request a coordinator refresh."""

    async def async_control_node(
        self,
        node_kind: str,
        resource_id: int | str,
        params: dict[str, Any],
        duration: int = 500,
    ) -> None:
        """Control a topology node."""


class CoordinatorControlMixin:
    """Route HA control calls through LAN when possible, otherwise cloud."""

    async def async_control_device(
        self: _ControlCoordinator,
        device_id: int | str,
        params: dict[str, Any],
        duration: int = 500,
    ) -> None:
        """Control one device and optimistically update runtime state."""
        normalized_device_id = _normalized_device_id(device_id)
        if normalized_device_id is None or not self.get_device(normalized_device_id):
            raise DeviceNotFoundError("Device not found")

        lan_ok = await async_try_lan_control_device(
            self._lan_runtime,
            device_id=normalized_device_id,
            params=params,
            duration=duration,
        )
        if not lan_ok:
            _ensure_cloud_client(self)
            await async_execute_control_device(
                self.client,
                house_id=self.house_id,
                device_id=normalized_device_id,
                params=params,
                duration=duration,
            )

        runtime_data = self.data if isinstance(self.data, Mapping) else {}
        self._runtime_state.store_update(
            normalized_device_id,
            params,
            devices=self.devices,
            gateways=self.gateways,
            data=runtime_data,
            rebuild_canonical=(
                self._device_payload_builder.attach_canonical_models_if_available
            ),
        )
        self.async_update_listeners()

    async def async_action_device(
        self: _ControlCoordinator,
        device_id: int | str,
        action: dict[str, Any],
    ) -> None:
        """Send a documented LAN-only device action."""
        normalized_device_id = _normalized_device_id(device_id)
        if normalized_device_id is None or not self.get_device(normalized_device_id):
            raise DeviceNotFoundError("Device not found")

        lan_ok = await async_try_lan_action_device(
            self._lan_runtime,
            device_id=normalized_device_id,
            action=action,
        )
        if not lan_ok:
            raise CommandError(
                "LAN action is unavailable for this Yeelight Pro entry"
            )

        await self.async_request_refresh()

    def can_control_device_action(self: _ControlCoordinator) -> bool:
        """Return whether LAN action commands can be sent right now."""
        return lan_runtime_connected(self._lan_runtime)

    async def async_toggle_device(
        self: _ControlCoordinator,
        device_id: int | str,
        properties: list[str],
    ) -> None:
        """Toggle one or more device properties."""
        normalized_device_id = _normalized_device_id(device_id)
        if normalized_device_id is None or not self.get_device(normalized_device_id):
            raise DeviceNotFoundError("Device not found")

        if not await async_try_lan_toggle_device(
            self._lan_runtime,
            device_id=normalized_device_id,
            properties=properties,
        ):
            _ensure_cloud_client(self)
            await async_execute_toggle_device(
                self.client,
                house_id=self.house_id,
                device_id=normalized_device_id,
                properties=properties,
            )

        await self.async_request_refresh()

    async def async_execute_scene(
        self: _ControlCoordinator,
        scene_id: str,
    ) -> None:
        """Execute a scene."""
        if not await async_try_lan_execute_scene(
            self._lan_runtime,
            scene_id=scene_id,
        ):
            _ensure_cloud_client(self)
            await async_execute_scene_command(
                self.client,
                house_id=self.house_id,
                scene_id=scene_id,
            )

    async def async_control_group(
        self: _ControlCoordinator,
        group_id: str,
        params: dict[str, Any],
        duration: int = 500,
    ) -> None:
        """Control a Mesh group."""
        if not await async_try_lan_control_group(
            self._lan_runtime,
            group_id=group_id,
            params=params,
            duration=duration,
        ):
            _ensure_cloud_client(self)
            await async_execute_control_group(
                self.client,
                house_id=self.house_id,
                group_id=group_id,
                params=params,
                duration=duration,
            )

        normalized_group_id = _normalized_device_id(group_id)
        if normalized_group_id is not None and merge_runtime_state_into_group_payloads(
            self.groups,
            group_id=normalized_group_id,
            params=params,
        ):
            self.async_update_listeners()

    async def async_control_node(
        self: _ControlCoordinator,
        node_kind: str,
        resource_id: int | str,
        params: dict[str, Any],
        duration: int = 500,
    ) -> None:
        """Control a room, area or house topology node."""
        if not await async_try_lan_control_node(
            self._lan_runtime,
            node_kind=node_kind,
            resource_id=resource_id,
            params=params,
            duration=duration,
        ):
            _ensure_cloud_client(self)
            await async_execute_control_node(
                self.client,
                house_id=self.house_id,
                node_kind=node_kind,
                resource_id=resource_id,
                params=params,
                duration=duration,
            )

        collection = _node_collection(self, node_kind)
        normalized_node_id = _normalized_device_id(resource_id)
        if (
            collection is not None
            and normalized_node_id is not None
            and merge_runtime_state_into_node_payloads(
                collection,
                node_id=normalized_node_id,
                params=params,
            )
        ):
            self.async_update_listeners()

    async def async_control_room(
        self: _ControlCoordinator,
        room_id: int | str,
        params: dict[str, Any],
        duration: int = 500,
    ) -> None:
        """Control a room topology node."""
        await self.async_control_node("room", room_id, params, duration)

    async def async_control_area(
        self: _ControlCoordinator,
        area_id: int | str,
        params: dict[str, Any],
        duration: int = 500,
    ) -> None:
        """Control an area topology node."""
        await self.async_control_node("area", area_id, params, duration)

    async def async_control_house(
        self: _ControlCoordinator,
        house_id: int | str,
        params: dict[str, Any],
        duration: int = 500,
    ) -> None:
        """Control a house topology node."""
        await self.async_control_node("house", house_id, params, duration)


__all__ = ["CoordinatorControlMixin"]


def _normalized_device_id(device_id: int | str) -> int | None:
    """Normalize HA entity device ids back to Yeelight numeric node ids."""
    try:
        return int(device_id)
    except (TypeError, ValueError):
        return None


def _node_collection(
    coordinator: _ControlCoordinator,
    node_kind: str,
) -> list[dict[str, Any]] | None:
    """Return the cached topology collection for one node kind."""
    if node_kind == "room":
        return coordinator.rooms
    if node_kind == "area":
        return coordinator.areas
    if node_kind == "house":
        return coordinator.houses
    if node_kind == "group":
        return coordinator.groups
    return None


def _ensure_cloud_client(coordinator: _ControlCoordinator) -> None:
    """LAN-only entry 无云端客户端时，给出明确且脱敏的控制错误。"""
    if coordinator.client is None:
        raise CommandError(
            "Cloud fallback is unavailable for this LAN-only Yeelight Pro entry"
        )
