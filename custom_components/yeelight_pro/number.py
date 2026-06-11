"""Yeelight Pro number 平台.

提供灯组亮度和色温的数值控制。
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .core.coordinator import YeelightProCoordinator
from .core.exceptions import YeelightProError
from .dynamic_entities import async_track_dynamic_entities
from .entity_category import ha_entity_category
from .entity_errors import raise_service_error
from .house_metadata import house_device_info
from .projector.property_controls import (
    HANumberControlProjection,
    project_number_controls,
)

_LOGGER = logging.getLogger(__name__)

# 数值范围常量
BRIGHTNESS_MIN = 0
BRIGHTNESS_MAX = 100
BRIGHTNESS_STEP = 1

COLOR_TEMP_MIN = 2700   # 暖白
COLOR_TEMP_MAX = 6500   # 冷白
COLOR_TEMP_STEP = 100


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """设置 Yeelight Pro number 平台."""
    coordinator: YeelightProCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    async_track_dynamic_entities(
        config_entry,
        coordinator,
        async_add_entities,
        _iter_number_entities,
        logger=_LOGGER,
        platform_name="number",
    )


def _iter_number_entities(coordinator: YeelightProCoordinator) -> list[NumberEntity]:
    """按当前拓扑生成 number 实体候选."""
    entities: list[NumberEntity] = []

    for device_id, device_data in coordinator.data.items():
        for projection in project_number_controls(device_data, domain=DOMAIN):
            entities.append(
                YeelightProDeviceNumber(
                    coordinator,
                    device_id,
                    component_id=projection.component_id,
                )
            )

    for group in coordinator.groups:
        group_id = group.get("id")
        if not group_id:
            continue
        group_name = group.get("name", f"灯组 {group_id}")
        entities.append(
            YeelightProGroupBrightness(coordinator, group_id, group_name)
        )
        entities.append(
            YeelightProGroupColorTemp(coordinator, group_id, group_name)
        )

    return entities


class YeelightProDeviceNumber(NumberEntity):
    """设备级可写数值属性实体."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: YeelightProCoordinator,
        device_id: int,
        *,
        component_id: str,
    ) -> None:
        """初始化设备数值属性实体."""
        super().__init__()
        self._coordinator = coordinator
        self._device_id = device_id
        self._component_id = component_id
        projection = self._projection
        self._attr_unique_id = (
            projection.unique_id
            if projection is not None
            else f"{DOMAIN}_{device_id}_{component_id}"
        )

    @property
    def _projection(self) -> HANumberControlProjection | None:
        """返回最新设备数值投影."""
        device = self._coordinator.get_device(self._device_id)
        if not device:
            return None
        return next(
            (
                item
                for item in project_number_controls(device, domain=DOMAIN)
                if item.component_id == self._component_id
            ),
            None,
        )

    @property
    def name(self) -> str | None:
        """返回数值实体名称."""
        projection = self._projection
        return projection.name if projection is not None else None

    @property
    def available(self) -> bool:
        """返回实体是否可用."""
        projection = self._projection
        return projection.available if projection is not None else False

    @property
    def icon(self) -> str | None:
        """返回前端图标."""
        projection = self._projection
        return projection.icon if projection is not None else "mdi:numeric"

    @property
    def device_info(self) -> dict[str, Any]:
        """返回设备信息."""
        projection = self._projection
        if projection is not None and projection.device_info is not None:
            return projection.device_info
        return {}

    @property
    def entity_category(self):
        """返回实体分类."""
        projection = self._projection
        if projection is None:
            return None
        return ha_entity_category(projection.entity_category)

    @property
    def native_min_value(self) -> float | None:
        """返回最小值."""
        projection = self._projection
        return projection.native_range.min if projection is not None else None

    @property
    def native_max_value(self) -> float | None:
        """返回最大值."""
        projection = self._projection
        return projection.native_range.max if projection is not None else None

    @property
    def native_step(self) -> float | None:
        """返回步进值."""
        projection = self._projection
        return projection.native_range.step if projection is not None else None

    @property
    def native_unit_of_measurement(self) -> str | None:
        """返回单位."""
        projection = self._projection
        return projection.unit if projection is not None else None

    @property
    def native_value(self) -> float | None:
        """返回当前数值."""
        projection = self._projection
        return projection.value if projection is not None else None

    async def async_set_native_value(self, value: float) -> None:
        """设置设备级数值属性."""
        projection = self._projection
        if projection is None:
            raise_service_error("number.set_device_property", YeelightProError("projection unavailable"))
        try:
            await self._coordinator.async_control_device(
                self._device_id,
                {projection.control_key: value},
            )
        except YeelightProError as err:
            raise_service_error("number.set_device_property", err)


class YeelightProGroupBrightness(NumberEntity):
    """灯组亮度控制实体."""

    _attr_has_entity_name = True
    _attr_native_min_value = BRIGHTNESS_MIN
    _attr_native_max_value = BRIGHTNESS_MAX
    _attr_native_step = BRIGHTNESS_STEP
    _attr_native_unit_of_measurement = "%"
    _attr_icon = "mdi:brightness-percent"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: YeelightProCoordinator,
        group_id: str,
        group_name: str,
    ) -> None:
        """初始化灯组亮度控制."""
        super().__init__()
        self._coordinator = coordinator
        self._group_id = group_id
        self._attr_unique_id = f"{DOMAIN}_group_{group_id}_brightness"
        self._attr_name = f"{group_name} 亮度"
        self._attr_native_value: float | None = None

    @property
    def device_info(self) -> dict[str, Any]:
        """返回关联的家庭设备信息."""
        return house_device_info(self._coordinator, name_suffix="灯组")

    async def async_set_native_value(self, value: float) -> None:
        """设置灯组亮度."""
        brightness = int(value)
        try:
            await self._coordinator.async_control_group(
                self._group_id,
                {"l": brightness},
            )
            self._attr_native_value = value
            self.async_write_ha_state()
            _LOGGER.debug("灯组 %s 亮度已设置为 %s%%", self._group_id, brightness)
        except YeelightProError as err:
            raise_service_error("number.set_group_brightness", err)


class YeelightProGroupColorTemp(NumberEntity):
    """灯组色温控制实体."""

    _attr_has_entity_name = True
    _attr_native_min_value = COLOR_TEMP_MIN
    _attr_native_max_value = COLOR_TEMP_MAX
    _attr_native_step = COLOR_TEMP_STEP
    _attr_native_unit_of_measurement = "K"
    _attr_icon = "mdi:thermometer"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: YeelightProCoordinator,
        group_id: str,
        group_name: str,
    ) -> None:
        """初始化灯组色温控制."""
        super().__init__()
        self._coordinator = coordinator
        self._group_id = group_id
        self._attr_unique_id = f"{DOMAIN}_group_{group_id}_color_temp"
        self._attr_name = f"{group_name} 色温"
        self._attr_native_value: float | None = None

    @property
    def device_info(self) -> dict[str, Any]:
        """返回关联的家庭设备信息."""
        return house_device_info(self._coordinator, name_suffix="灯组")

    async def async_set_native_value(self, value: float) -> None:
        """设置灯组色温."""
        color_temp = int(value)
        try:
            await self._coordinator.async_control_group(
                self._group_id,
                {"ct": color_temp},
            )
            self._attr_native_value = value
            self.async_write_ha_state()
            _LOGGER.debug(
                "灯组 %s 色温已设置为 %sK", self._group_id, color_temp
            )
        except YeelightProError as err:
            raise_service_error("number.set_group_color_temp", err)
