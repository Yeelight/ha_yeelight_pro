"""风扇平台，Yeelight Pro 集成。"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.fan import (
    DIRECTION_FORWARD,
    DIRECTION_REVERSE,
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
from .projector.fan import HAFanProjection, NumericRange, project_fans

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """初始化 Yeelight Pro 风扇平台。"""
    coordinator: YeelightProCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    fans = []
    for device_id, device_data in coordinator.data.items():
        projections = project_fans(device_data, domain=DOMAIN)
        for projection in projections:
            fans.append(
                YeelightProFan(
                    coordinator,
                    device_id,
                    component_id=projection.component_id,
                )
            )

    if fans:
        async_add_entities(fans)
        _LOGGER.info("Added %s fan entities", len(fans))


class YeelightProFan(CoordinatorEntity, FanEntity):
    """Yeelight Pro 风扇实体。"""

    def __init__(
        self,
        coordinator: YeelightProCoordinator,
        device_id: str,
        *,
        component_id: str,
    ) -> None:
        """初始化风扇实体。"""
        super().__init__(coordinator)
        self._device_id = device_id
        self._component_id = component_id
        projection = self._projection
        self._attr_unique_id = (
            projection.unique_id
            if projection is not None
            else f"{DOMAIN}_{device_id}_{component_id}"
        )
        self._attr_has_entity_name = True

    @property
    def _projection(self) -> HAFanProjection | None:
        """返回最新的风扇投影视图。"""
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
        """返回风扇名称。"""
        projection = self._projection
        if projection is not None:
            return projection.name
        device_data = self.coordinator.get_device(self._device_id)
        if device_data:
            return device_data.get("name", f"Fan {self._device_id}")
        return f"Fan {self._device_id}"

    @property
    def available(self) -> bool:
        """返回风扇是否可用。"""
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
        """返回风扇是否开启。"""
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
        """返回当前风扇方向。"""
        projection = self._projection
        if projection is not None:
            return projection.current_direction
        return None

    @property
    def supported_features(self):
        """返回支持的风扇功能标志。"""
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
        """开启风扇。"""
        projection = self._projection
        if projection is None:
            raise HomeAssistantError(
                f"无法解析风扇投影: {self._component_id}"
            )

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
            raise HomeAssistantError(
                f"开启风扇失败: {self._component_id}: {err}"
            ) from err

    async def async_turn_off(self, **kwargs: Any) -> None:
        """关闭风扇。"""
        projection = self._projection
        if projection is None:
            raise HomeAssistantError(
                f"无法解析风扇投影: {self._component_id}"
            )

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
            raise HomeAssistantError(
                f"关闭风扇失败: {self._component_id}: {err}"
            ) from err

    async def async_set_percentage(self, percentage: int) -> None:
        """设置风扇转速百分比。"""
        projection = self._projection
        if projection is None or projection.speed_key is None:
            raise HomeAssistantError(
                f"无法解析风扇转速投影: {self._component_id}"
            )

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
            raise HomeAssistantError(
                f"设置风扇转速失败: {self._component_id}: {err}"
            ) from err

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """设置风扇预设模式。"""
        projection = self._projection
        if projection is None or projection.mode_key is None:
            raise HomeAssistantError(
                f"无法解析风扇模式投影: {self._component_id}"
            )

        params: dict[str, Any] = {projection.mode_key: preset_mode}
        if projection.power_key is not None:
            params[projection.power_key] = True

        try:
            await self.coordinator.async_control_device(self._device_id, params)
        except YeelightProError as err:
            raise HomeAssistantError(
                f"设置风扇模式失败: {self._component_id}: {err}"
            ) from err

    async def async_set_direction(self, direction: str) -> None:
        """设置风扇方向。"""
        projection = self._projection
        if projection is None or projection.direction_key is None:
            raise HomeAssistantError(
                f"无法解析风扇方向投影: {self._component_id}"
            )

        raw_direction = projection.direction_values.get(direction)
        if raw_direction is None:
            raw_direction = (
                DIRECTION_FORWARD
                if direction == DIRECTION_FORWARD
                else DIRECTION_REVERSE
            )

        try:
            await self.coordinator.async_control_device(
                self._device_id,
                {projection.direction_key: raw_direction},
            )
        except YeelightProError as err:
            raise HomeAssistantError(
                f"设置风扇方向失败: {self._component_id}: {err}"
            ) from err

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
