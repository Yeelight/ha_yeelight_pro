"""新风平台，Yeelight Pro 集成。

Home Assistant 使用 fan 平台承载新风风量能力。
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.fan import (
    FanEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util.percentage import percentage_to_ranged_value

from .const import DOMAIN
from .core.coordinator import YeelightProCoordinator
from .core.exceptions import YeelightProError
from .device_display import suggested_entity_object_id
from .dynamic_entities import async_track_dynamic_entities
from .entity_device_id import source_device_id
from .entity_errors import raise_service_error
from .identity import device_entity_unique_id
from .projector.fan import HAFanProjection, NumericRange, project_fans

_LOGGER = logging.getLogger(__name__)
ERROR_FAN_PROJECTION_UNAVAILABLE = "无法解析新风投影"
ERROR_FAN_SPEED_PROJECTION_UNAVAILABLE = "无法解析新风风量投影"
ERROR_FAN_MODE_PROJECTION_UNAVAILABLE = "无法解析新风模式投影"
ERROR_FAN_DIRECTION_PROJECTION_UNAVAILABLE = "无法解析新风方向投影"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """初始化 Yeelight Pro 新风平台。"""
    coordinator: YeelightProCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    async_track_dynamic_entities(
        config_entry,
        coordinator,
        async_add_entities,
        _iter_fan_entities,
        logger=_LOGGER,
        platform_name="fan",
    )


def _iter_fan_entities(coordinator: YeelightProCoordinator) -> list["YeelightProFan"]:
    """按当前拓扑生成新风实体候选。"""
    fans: list[YeelightProFan] = []
    for device_key, device_data in coordinator.data.items():
        device_id = source_device_id(device_key, device_data)
        projections = project_fans(device_data, domain=DOMAIN)
        for projection in projections:
            fans.append(
                YeelightProFan(
                    coordinator,
                    device_id,
                    component_id=projection.component_id,
                )
            )
    return fans


class YeelightProFan(CoordinatorEntity, FanEntity):
    """Yeelight Pro 新风实体。"""

    def __init__(
        self,
        coordinator: YeelightProCoordinator,
        device_id: int | str,
        *,
        component_id: str,
    ) -> None:
        """初始化新风实体。"""
        super().__init__(coordinator)
        self._device_id = device_id
        self._component_id = component_id
        projection = self._projection
        self._attr_unique_id = (
            projection.unique_id
            if projection is not None
            else device_entity_unique_id(coordinator, device_id, component_id)
        )
        self._attr_has_entity_name = True

    @property
    def _projection(self) -> HAFanProjection | None:
        """返回最新的新风投影视图。"""
        device = self.coordinator.get_device(self._device_id)
        if not device:
            return None
        projections = project_fans(device, domain=DOMAIN)
        return next(
            (item for item in projections if item.component_id == self._component_id),
            None,
        )

    @property
    def name(self) -> str | None:
        """返回新风名称。"""
        projection = self._projection
        if projection is not None:
            return projection.name
        device_data = self.coordinator.get_device(self._device_id)
        if device_data:
            return device_data.get("name", f"Fan {self._device_id}")
        return f"Fan {self._device_id}"

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
        """返回新风是否可用。"""
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
        return "mdi:fan"

    @property
    def is_on(self) -> bool | None:
        """返回新风是否开启。"""
        projection = self._projection
        if projection is not None:
            return projection.is_on
        return False

    @property
    def percentage(self) -> int | None:
        """返回当前转速百分比。"""
        projection = self._projection
        if projection is not None:
            return projection.percentage
        return None

    @property
    def speed_count(self) -> int:
        """返回支持的转速档位数。"""
        projection = self._projection
        if projection is not None:
            return projection.speed_count
        return 100

    @property
    def preset_mode(self) -> str | None:
        """返回当前预设模式。"""
        projection = self._projection
        if projection is not None:
            return projection.preset_mode
        return None

    @property
    def preset_modes(self) -> list[str] | None:
        """返回支持的预设模式列表。"""
        projection = self._projection
        if projection is not None:
            return projection.preset_modes
        return None

    @property
    def current_direction(self) -> str | None:
        """返回当前新风方向。"""
        projection = self._projection
        if projection is not None:
            return projection.current_direction
        return None

    @property
    def supported_features(self):
        """返回支持的新风功能标志。"""
        projection = self._projection
        if projection is not None:
            return projection.supported_features
        return 0

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """开启新风。"""
        projection = self._projection
        if projection is None:
            raise HomeAssistantError(ERROR_FAN_PROJECTION_UNAVAILABLE)

        params: dict[str, Any] = {}
        if projection.power_key is not None:
            params[projection.power_key] = True

        if percentage is not None and projection.speed_key is not None:
            params[projection.speed_key] = self._percentage_to_source(
                percentage,
                projection.speed_range,
            )
        if preset_mode is not None and projection.mode_key is not None:
            params[projection.mode_key] = preset_mode

        if not params and projection.speed_key is not None:
            params[projection.speed_key] = self._default_on_speed(projection.speed_range)

        if not params:
            return

        try:
            await self.coordinator.async_control_device(self._device_id, params)
        except YeelightProError as err:
            raise_service_error("fan.turn_on", err)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """关闭新风。"""
        projection = self._projection
        if projection is None:
            raise HomeAssistantError(ERROR_FAN_PROJECTION_UNAVAILABLE)

        params: dict[str, Any] = {}
        if projection.power_key is not None:
            params[projection.power_key] = False
        elif projection.speed_key is not None:
            params[projection.speed_key] = 0

        if not params:
            return

        try:
            await self.coordinator.async_control_device(self._device_id, params)
        except YeelightProError as err:
            raise_service_error("fan.turn_off", err)

    async def async_set_percentage(self, percentage: int) -> None:
        """设置新风风量百分比。"""
        projection = self._projection
        if projection is None or projection.speed_key is None:
            raise HomeAssistantError(ERROR_FAN_SPEED_PROJECTION_UNAVAILABLE)

        params: dict[str, Any]
        if percentage <= 0:
            params = (
                {projection.power_key: False}
                if projection.power_key is not None
                else {projection.speed_key: 0}
            )
        else:
            params = {
                projection.speed_key: self._percentage_to_source(
                    percentage,
                    projection.speed_range,
                )
            }
            if projection.power_key is not None:
                params[projection.power_key] = True

        try:
            await self.coordinator.async_control_device(self._device_id, params)
        except YeelightProError as err:
            raise_service_error("fan.set_percentage", err)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """设置新风预设模式。"""
        projection = self._projection
        if projection is None or projection.mode_key is None:
            raise HomeAssistantError(ERROR_FAN_MODE_PROJECTION_UNAVAILABLE)

        params: dict[str, Any] = {projection.mode_key: preset_mode}
        if projection.power_key is not None:
            params[projection.power_key] = True

        try:
            await self.coordinator.async_control_device(self._device_id, params)
        except YeelightProError as err:
            raise_service_error("fan.set_preset_mode", err)

    async def async_set_direction(self, direction: str) -> None:
        """设置新风方向。"""
        projection = self._projection
        if projection is None or projection.direction_key is None:
            raise HomeAssistantError(ERROR_FAN_DIRECTION_PROJECTION_UNAVAILABLE)

        raw_direction = projection.direction_values.get(direction)
        if raw_direction is None:
            raise HomeAssistantError(ERROR_FAN_DIRECTION_PROJECTION_UNAVAILABLE)

        try:
            await self.coordinator.async_control_device(
                self._device_id,
                {projection.direction_key: raw_direction},
            )
        except YeelightProError as err:
            raise_service_error("fan.set_direction", err)

    def _percentage_to_source(
        self,
        percentage: int,
        speed_range: NumericRange | None,
    ) -> int:
        """将 HA 百分比转换为源设备转速值。"""
        if speed_range is None:
            return max(0, min(100, int(percentage)))

        minimum = speed_range.min if speed_range.min is not None else 1
        maximum = speed_range.max if speed_range.max is not None else 100
        if maximum < minimum:
            return max(0, min(100, int(percentage)))
        return int(round(percentage_to_ranged_value((minimum, maximum), percentage)))

    def _default_on_speed(self, speed_range: NumericRange | None) -> int:
        """返回未指定百分比时的默认开启转速。"""
        if speed_range is None:
            return 100
        return speed_range.min if speed_range.min is not None else 1
