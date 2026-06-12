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
from .runtime_state import RuntimeStateStore, merge_runtime_state_into_group_payloads


class _ControlCoordinator(Protocol):
    """Control attributes provided by YeelightProCoordinator."""

    client: Any
    data: Any
    devices: dict[int, dict[str, Any]]
    gateways: dict[int, dict[str, Any]]
    groups: list[dict[str, Any]]
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

        normalized_group_id = _normalized_device_id(group_id)
        if normalized_group_id is not None and merge_runtime_state_into_group_payloads(
            self.groups,
            group_id=normalized_group_id,
            params=params,
        ):
            self.async_update_listeners()


__all__ = ["CoordinatorControlMixin"]


def _normalized_device_id(device_id: int | str) -> int | None:
    """Normalize HA entity device ids back to Yeelight numeric node ids."""
    try:
        return int(device_id)
    except (TypeError, ValueError):
        return None
