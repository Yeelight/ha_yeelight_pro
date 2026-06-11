"""Control routing for Yeelight Pro coordinators."""

from __future__ import annotations

from typing import Any, Mapping, Protocol

from .commands import (
    async_control_device as async_execute_control_device,
    async_control_group as async_execute_control_group,
    async_execute_scene as async_execute_scene_command,
    async_toggle_device as async_execute_toggle_device,
)
from .device_payload import DevicePayloadBuilder
from .exceptions import DeviceNotFoundError
from .lan_control import (
    async_try_lan_control_device,
    async_try_lan_control_group,
    async_try_lan_execute_scene,
    async_try_lan_toggle_device,
)
from .runtime_state import RuntimeStateStore


class _ControlCoordinator(Protocol):
    """Control attributes provided by YeelightProCoordinator."""

    client: Any
    data: Any
    devices: dict[int, dict[str, Any]]
    gateways: dict[int, dict[str, Any]]
    house_id: int
    _device_payload_builder: DevicePayloadBuilder
    _lan_runtime: Any | None
    _runtime_state: RuntimeStateStore

    def get_device(self, device_id: int) -> dict[str, Any] | None:
        """Return a device payload by id."""

    def async_update_listeners(self) -> None:
        """Notify Home Assistant coordinator listeners."""

    async def async_request_refresh(self) -> None:
        """Request a coordinator refresh."""


class CoordinatorControlMixin:
    """Route HA control calls through LAN when possible, otherwise cloud."""

    async def async_control_device(
        self: _ControlCoordinator,
        device_id: int,
        params: dict[str, Any],
        duration: int = 500,
    ) -> None:
        """Control one device and optimistically update runtime state."""
        if not self.get_device(device_id):
            raise DeviceNotFoundError("Device not found")

        if not await async_try_lan_control_device(
            self._lan_runtime,
            device_id=device_id,
            params=params,
            duration=duration,
        ):
            await async_execute_control_device(
                self.client,
                house_id=self.house_id,
                device_id=device_id,
                params=params,
                duration=duration,
            )

        runtime_data = self.data if isinstance(self.data, Mapping) else {}
        self._runtime_state.store_update(
            device_id,
            params,
            devices=self.devices,
            gateways=self.gateways,
            data=runtime_data,
            rebuild_canonical=(
                self._device_payload_builder.attach_canonical_models_if_available
            ),
        )
        self.async_update_listeners()

    async def async_toggle_device(
        self: _ControlCoordinator,
        device_id: int,
        properties: list[str],
    ) -> None:
        """Toggle one or more device properties."""
        if not self.get_device(device_id):
            raise DeviceNotFoundError("Device not found")

        if not await async_try_lan_toggle_device(
            self._lan_runtime,
            device_id=device_id,
            properties=properties,
        ):
            await async_execute_toggle_device(
                self.client,
                house_id=self.house_id,
                device_id=device_id,
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
            await async_execute_control_group(
                self.client,
                house_id=self.house_id,
                group_id=group_id,
                params=params,
                duration=duration,
            )


__all__ = ["CoordinatorControlMixin"]
