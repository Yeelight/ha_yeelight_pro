"""Yeelight Pro switch 平台."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .core.coordinator import YeelightProCoordinator
from .core.exceptions import YeelightProError
from .dynamic_entities import async_track_dynamic_entities
from .entity_errors import raise_service_error
from .projector.switch import HASwitchProjection, project_switches

_LOGGER = logging.getLogger(__name__)
ERROR_SWITCH_PROJECTION_UNAVAILABLE = "无法解析 switch 投影"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """设置 Yeelight Pro switch 平台."""
    coordinator: YeelightProCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    async_track_dynamic_entities(
        config_entry,
        coordinator,
        async_add_entities,
        _iter_switch_entities,
        logger=_LOGGER,
        platform_name="switch",
    )


def _iter_switch_entities(coordinator: YeelightProCoordinator) -> list["YeelightProSwitch"]:
    """按当前拓扑生成 switch 实体候选."""
    switches: list[YeelightProSwitch] = []
    for device_id, device_data in coordinator.data.items():
        projections = project_switches(device_data, domain=DOMAIN)
        for projection in projections:
            switches.append(
                YeelightProSwitch(
                    coordinator,
                    device_id,
                    component_id=projection.component_id,
                )
            )
    return switches


class YeelightProSwitch(CoordinatorEntity, SwitchEntity):
    """Yeelight Pro 开关实体."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: YeelightProCoordinator,
        device_id: int,
        *,
        component_id: str,
    ) -> None:
        """初始化开关实体."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._component_id = component_id
        projection = self._projection
        self._attr_unique_id = (
            projection.unique_id
            if projection is not None
            else f"{DOMAIN}_{device_id}_{component_id}"
        )

    @property
    def _projection(self) -> HASwitchProjection | None:
        """返回最新的开关投影视图."""
        projections = project_switches(
            self.coordinator.get_device(self._device_id),
            domain=DOMAIN,
        )
        return next(
            (item for item in projections if item.component_id == self._component_id),
            None,
        )

    @property
    def icon(self) -> str:
        """返回前端使用的图标."""
        projection = self._projection
        if projection is not None and projection.icon:
            return projection.icon
        return "mdi:light-switch"

    @property
    def device_info(self) -> dict[str, Any]:
        """返回设备信息."""
        projection = self._projection
        if projection is not None and projection.device_info is not None:
            return projection.device_info
        return {}

    @property
    def name(self) -> str | None:
        """返回开关名称."""
        projection = self._projection
        if projection is not None:
            return projection.name
        device_data = self.coordinator.get_device(self._device_id)
        if device_data is not None:
            return device_data.get("name", f"Switch {self._device_id}")
        return f"Switch {self._device_id}"

    @property
    def available(self) -> bool:
        """返回开关是否可用."""
        projection = self._projection
        if projection is not None:
            return projection.available
        return False

    @property
    def is_on(self) -> bool:
        """返回开关是否开启."""
        projection = self._projection
        return projection.is_on if projection is not None else False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """开启开关."""
        projection = self._projection
        if projection is None:
            raise HomeAssistantError(ERROR_SWITCH_PROJECTION_UNAVAILABLE)
        try:
            await self.coordinator.async_control_device(
                self._device_id,
                {projection.control_key: True},
            )
        except YeelightProError as err:
            raise_service_error("switch.turn_on", err)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """关闭开关."""
        projection = self._projection
        if projection is None:
            raise HomeAssistantError(ERROR_SWITCH_PROJECTION_UNAVAILABLE)
        try:
            await self.coordinator.async_control_device(
                self._device_id,
                {projection.control_key: False},
            )
        except YeelightProError as err:
            raise_service_error("switch.turn_off", err)
