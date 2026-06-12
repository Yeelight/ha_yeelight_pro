"""空调平台，Yeelight Pro 集成。"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import ClimateEntity, HVACMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .core.coordinator import YeelightProCoordinator
from .core.exceptions import YeelightProError
from .device_display import suggested_entity_object_id
from .dynamic_entities import async_track_dynamic_entities
from .entity_device_id import source_device_id
from .entity_errors import raise_service_error
from .projector.climate import HAClimateProjection, project_climates
from .projector.climate_helpers import (
    climate_raw_fan_for_mode,
    climate_raw_mode_for_hvac,
)

_LOGGER = logging.getLogger(__name__)
ERROR_CLIMATE_PROJECTION_UNAVAILABLE = "无法解析温控投影"
ERROR_CLIMATE_TARGET_UNAVAILABLE = "设备未声明可写目标温度"
ERROR_CLIMATE_POWER_UNAVAILABLE = "设备未声明可写温控开关"
ERROR_CLIMATE_MODE_UNAVAILABLE = "设备未声明可写空调模式"
ERROR_CLIMATE_FAN_MODE_UNAVAILABLE = "设备未声明可写空调风速"


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
    for device_key, device_data in coordinator.data.items():
        device_id = source_device_id(device_key, device_data)
        projections = project_climates(device_data, domain=DOMAIN)
        _LOGGER.debug(
            "Climate candidates projected: device_id=%s projection_count=%d "
            "component_ids=%s",
            device_id,
            len(projections),
            [item.component_id for item in projections],
        )
        for projection in projections:
            climates.append(
                YeelightProClimate(
                    coordinator,
                    device_id,
                    component_id=projection.component_id,
                )
            )
    return climates


class YeelightProClimate(CoordinatorEntity, ClimateEntity):
    """Yeelight Pro 空调实体。"""

    def __init__(
        self,
        coordinator: YeelightProCoordinator,
        device_id: int | str,
        *,
        component_id: str | None = None,
    ):
        """初始化空调实体。"""
        super().__init__(coordinator)
        self._device_id = device_id
        self._component_id = component_id
        projection = self._projection
        self._attr_unique_id = (
            projection.unique_id
            if projection is not None
            else f"{DOMAIN}_{device_id}_{component_id or 'climate'}"
        )
        self._attr_has_entity_name = True
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS

    @property
    def _projection(self) -> HAClimateProjection | None:
        """返回最新的空调投影视图。"""
        device = self.coordinator.get_device(self._device_id)
        if device is None:
            return None
        projections = project_climates(device, domain=DOMAIN)
        if self._component_id is None:
            return projections[0] if projections else None
        return next(
            (item for item in projections if item.component_id == self._component_id),
            None,
        )

    @property
    def name(self) -> str | None:
        """返回空调实体名称。"""
        projection = self._projection
        if projection is not None:
            return projection.name
        return "温控"

    @property
    def suggested_object_id(self) -> str | None:
        """返回 HA 首次注册时使用的友好实体 ID 建议。"""
        return suggested_entity_object_id(
            self.coordinator.get_device(self._device_id),
            entity_name=self.name,
            fallback_id=self._device_id,
        )

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

    @property
    def fan_mode(self) -> str | None:
        """返回当前空调风速。"""
        projection = self._projection
        if projection is not None:
            return projection.fan_mode
        return None

    @property
    def fan_modes(self) -> list[str] | None:
        """返回可选空调风速。"""
        projection = self._projection
        if projection is not None:
            return projection.fan_modes
        return None

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """设置目标温度。"""
        temperature = kwargs.get("temperature")
        if temperature is None:
            return
        projection = self._projection
        if projection is None:
            _LOGGER.debug(
                "Skipping climate control: device_id=%s component_id=%s action=%s "
                "reason=%s",
                self._device_id,
                self._component_id,
                "climate.set_temperature",
                "projection_unavailable",
            )
            raise HomeAssistantError(ERROR_CLIMATE_PROJECTION_UNAVAILABLE)
        if projection.target_temperature_key is None:
            _LOGGER.debug(
                "Skipping climate control: device_id=%s component_id=%s action=%s "
                "reason=%s",
                self._device_id,
                projection.component_id,
                "climate.set_temperature",
                "target_temperature_key_unavailable",
            )
            raise HomeAssistantError(ERROR_CLIMATE_TARGET_UNAVAILABLE)
        _LOGGER.debug(
            "Climate control request: device_id=%s component_id=%s action=%s "
            "control_key=%s target_temperature=%s",
            self._device_id,
            projection.component_id,
            "climate.set_temperature",
            projection.target_temperature_key,
            float(temperature),
        )
        try:
            await self.coordinator.async_control_device(
                self._device_id,
                {projection.target_temperature_key: float(temperature)},
            )
        except YeelightProError as err:
            raise_service_error("climate.set_temperature", err)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """设置 HVAC 模式。"""
        projection = self._projection
        if projection is None:
            _LOGGER.debug(
                "Skipping climate control: device_id=%s component_id=%s action=%s "
                "reason=%s",
                self._device_id,
                self._component_id,
                "climate.set_hvac_mode",
                "projection_unavailable",
            )
            raise HomeAssistantError(ERROR_CLIMATE_PROJECTION_UNAVAILABLE)
        if projection.power_key is None:
            _LOGGER.debug(
                "Skipping climate control: device_id=%s component_id=%s action=%s "
                "reason=%s",
                self._device_id,
                projection.component_id,
                "climate.set_hvac_mode",
                "power_key_unavailable",
            )
            raise HomeAssistantError(ERROR_CLIMATE_POWER_UNAVAILABLE)
        raw_mode = climate_raw_mode_for_hvac(hvac_mode)
        if raw_mode is not None and projection.mode_key is None:
            _LOGGER.debug(
                "Skipping climate control: device_id=%s component_id=%s action=%s "
                "reason=%s hvac_mode=%s",
                self._device_id,
                projection.component_id,
                "climate.set_hvac_mode",
                "mode_key_unavailable",
                hvac_mode,
            )
            raise HomeAssistantError(ERROR_CLIMATE_MODE_UNAVAILABLE)
        control_payload = self._hvac_control_payload(projection, hvac_mode, raw_mode)
        _LOGGER.debug(
            "Climate control request: device_id=%s component_id=%s action=%s "
            "control_key=%s hvac_mode=%s",
            self._device_id,
            projection.component_id,
            "climate.set_hvac_mode",
            sorted(control_payload),
            hvac_mode,
        )
        try:
            await self.coordinator.async_control_device(
                self._device_id,
                control_payload,
            )
        except YeelightProError as err:
            raise_service_error("climate.set_hvac_mode", err)

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """设置空调风速。"""
        projection = self._projection
        if projection is None:
            _LOGGER.debug(
                "Skipping climate control: device_id=%s component_id=%s action=%s "
                "reason=%s",
                self._device_id,
                self._component_id,
                "climate.set_fan_mode",
                "projection_unavailable",
            )
            raise HomeAssistantError(ERROR_CLIMATE_PROJECTION_UNAVAILABLE)
        if projection.fan_mode_key is None:
            _LOGGER.debug(
                "Skipping climate control: device_id=%s component_id=%s action=%s "
                "reason=%s",
                self._device_id,
                projection.component_id,
                "climate.set_fan_mode",
                "fan_mode_key_unavailable",
            )
            raise HomeAssistantError(ERROR_CLIMATE_FAN_MODE_UNAVAILABLE)
        raw_fan = climate_raw_fan_for_mode(fan_mode, projection.fan_mode_values)
        if raw_fan is None:
            _LOGGER.debug(
                "Skipping climate control: device_id=%s component_id=%s action=%s "
                "reason=%s fan_mode=%s",
                self._device_id,
                projection.component_id,
                "climate.set_fan_mode",
                "unsupported_fan_mode",
                fan_mode,
            )
            raise HomeAssistantError(ERROR_CLIMATE_FAN_MODE_UNAVAILABLE)
        _LOGGER.debug(
            "Climate control request: device_id=%s component_id=%s action=%s "
            "control_key=%s fan_mode=%s",
            self._device_id,
            projection.component_id,
            "climate.set_fan_mode",
            projection.fan_mode_key,
            fan_mode,
        )
        try:
            await self.coordinator.async_control_device(
                self._device_id,
                {projection.fan_mode_key: raw_fan},
            )
        except YeelightProError as err:
            raise_service_error("climate.set_fan_mode", err)

    def _hvac_control_payload(
        self,
        projection: HAClimateProjection,
        hvac_mode: HVACMode,
        raw_mode: int | None,
    ) -> dict[str, Any]:
        """Build the documented Yeelight AC control payload."""
        if projection.power_key is None:
            raise HomeAssistantError(ERROR_CLIMATE_POWER_UNAVAILABLE)
        if hvac_mode == HVACMode.OFF:
            return {projection.power_key: False}
        payload: dict[str, Any] = {projection.power_key: True}
        if raw_mode is not None and projection.mode_key is not None:
            payload[projection.mode_key] = raw_mode
        return payload
