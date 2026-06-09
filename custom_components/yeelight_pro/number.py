"""Yeelight Pro number 平台.

提供灯组亮度和色温的数值控制，以及自动化延时控制。
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .core.coordinator import YeelightProCoordinator
from .core.exceptions import YeelightProError
from .dynamic_entities import async_track_dynamic_entities
from .entity_errors import raise_service_error

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


class YeelightProGroupBrightness(NumberEntity):
    """灯组亮度控制实体."""

    _attr_has_entity_name = True
    _attr_native_min_value = BRIGHTNESS_MIN
    _attr_native_max_value = BRIGHTNESS_MAX
    _attr_native_step = BRIGHTNESS_STEP
    _attr_native_unit_of_measurement = "%"
    _attr_icon = "mdi:brightness-percent"

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
        return {
            "identifiers": {(DOMAIN, str(self._coordinator.house_id))},
            "name": f"Yeelight Pro {self._coordinator.house_id}",
            "manufacturer": "Yeelight",
        }

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
        return {
            "identifiers": {(DOMAIN, str(self._coordinator.house_id))},
            "name": f"Yeelight Pro {self._coordinator.house_id}",
            "manufacturer": "Yeelight",
        }

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
