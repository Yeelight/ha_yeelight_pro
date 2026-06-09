"""空调平台，Yeelight Pro 集成。"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import ClimateEntity, HVACMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .core.coordinator import YeelightProCoordinator
from .core.exceptions import YeelightProError
from .dynamic_entities import async_track_dynamic_entities
from .entity_errors import raise_service_error
from .projector.climate import HAClimateProjection, project_climate

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """初始化 Yeelight Pro 空调平台。"""
    coordinator: YeelightProCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    async_track_dynamic_entities(
        config_entry,
        coordinator,
        async_add_entities,
        _iter_climate_entities,
        logger=_LOGGER,
        platform_name="climate",
    )


def _iter_climate_entities(coordinator: YeelightProCoordinator) -> list["YeelightProClimate"]:
    """按当前拓扑生成 climate 实体候选。"""
    climates: list[YeelightProClimate] = []
    for device_id, device_data in coordinator.data.items():
        if project_climate(device_data, domain=DOMAIN) is not None:
            climates.append(YeelightProClimate(coordinator, device_id))
    return climates


class YeelightProClimate(CoordinatorEntity, ClimateEntity):
    """Yeelight Pro 空调实体。"""

    def __init__(self, coordinator: YeelightProCoordinator, device_id: str):
        """初始化空调实体。"""
        super().__init__(coordinator)
        self._device_id = device_id
        projection = self._projection
        self._attr_unique_id = (
            projection.unique_id if projection is not None else f"{DOMAIN}_{device_id}_climate"
        )
        self._attr_has_entity_name = True
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS

    @property
    def _projection(self) -> HAClimateProjection | None:
        """返回最新的空调投影视图。"""
        return project_climate(self.coordinator.get_device(self._device_id), domain=DOMAIN)

    @property
    def name(self) -> str | None:
        """返回空调实体名称。"""
        projection = self._projection
        if projection is not None:
            return projection.name
        device_data = self.coordinator.get_device(self._device_id)
        return device_data.get("name", f"Climate {self._device_id}")

    @property
    def available(self) -> bool:
        """返回空调是否可用。"""
        projection = self._projection
        if projection is not None:
            return projection.available
        return False

    @property
    def device_info(self):
        """返回设备注册信息。"""
        projection = self._projection
        if projection is not None:
            return projection.device_info
        return None

    @property
    def icon(self) -> str | None:
        """返回实体图标。"""
        projection = self._projection
        if projection is not None:
            return projection.icon
        return None

    @property
    def supported_features(self):
        """返回支持的空调功能。"""
        projection = self._projection
        if projection is not None:
            return projection.supported_features
        return 0

    @property
    def hvac_modes(self) -> list[HVACMode]:
        """返回可用的 HVAC 模式。"""
        projection = self._projection
        if projection is not None:
            return projection.hvac_modes
        return [HVACMode.OFF]

    @property
    def hvac_mode(self) -> HVACMode:
        """返回当前 HVAC 模式。"""
        projection = self._projection
        if projection is not None:
            return projection.hvac_mode
        return HVACMode.OFF

    @property
    def current_temperature(self) -> float | None:
        """返回当前温度。"""
        projection = self._projection
        if projection is not None:
            return projection.current_temperature
        return None

    @property
    def target_temperature(self) -> float | None:
        """返回目标温度。"""
        projection = self._projection
        if projection is not None:
            return projection.target_temperature
        return None

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """设置目标温度。"""
        temperature = kwargs.get("temperature")
        if temperature is None:
            return
        try:
            await self.coordinator.async_control_device(
                self._device_id,
                {"actt": float(temperature)},
            )
        except YeelightProError as err:
            raise_service_error("climate.set_temperature", err)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """设置 HVAC 模式。"""
        try:
            await self.coordinator.async_control_device(
                self._device_id,
                {"aco": hvac_mode != HVACMode.OFF},
            )
        except YeelightProError as err:
            raise_service_error("climate.set_hvac_mode", err)
