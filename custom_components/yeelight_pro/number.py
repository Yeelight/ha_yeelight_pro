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
    entities: list[NumberEntity] = []

    # 获取灯组列表
    try:
        groups = await coordinator.client.get_groups(coordinator.house_id)
    except Exception as err:
        groups = []
        _LOGGER.warning("获取灯组列表失败: %s", err)

    # 为每个灯组创建亮度和色温控制
    for group in groups:
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

    if entities:
        async_add_entities(entities)
        _LOGGER.info("已添加 %s 个 number 实体", len(entities))


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
        success = await self._coordinator.client.control_group(
            self._group_id,
            {"brightness": brightness},
        )
        if success:
            self._attr_native_value = value
            self.async_write_ha_state()
            _LOGGER.debug("灯组 %s 亮度已设置为 %s%%", self._group_id, brightness)
        else:
            _LOGGER.error("设置灯组 %s 亮度失败: %s", self._group_id, brightness)


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
        success = await self._coordinator.client.control_group(
            self._group_id,
            {"color_temperature": color_temp},
        )
        if success:
            self._attr_native_value = value
            self.async_write_ha_state()
            _LOGGER.debug(
                "灯组 %s 色温已设置为 %sK", self._group_id, color_temp
            )
        else:
            _LOGGER.error(
                "设置灯组 %s 色温失败: %sK", self._group_id, color_temp
            )
