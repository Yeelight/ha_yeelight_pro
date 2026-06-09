"""Yeelight Pro 选择器平台.

提供房间选择器、灯组选择器和场景选择器实体。
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .core.coordinator import YeelightProCoordinator
from .core.exceptions import YeelightProError
from .entity_errors import raise_service_error

_LOGGER = logging.getLogger(__name__)

# 选择器图标
ICON_ROOM = "mdi:floor-plan"
ICON_GROUP = "mdi:lightbulb-group"
ICON_SCENE = "mdi:palette"

# 空选项占位
EMPTY_OPTION = "无可用选项"
ERROR_UNKNOWN_ROOM_OPTION = "未知房间选项"
ERROR_UNKNOWN_GROUP_OPTION = "未知灯组选项"
ERROR_UNKNOWN_SCENE_OPTION = "未知场景选项"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """设置 Yeelight Pro 选择器平台."""
    coordinator: YeelightProCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    entities: list[SelectEntity] = [
        YeelightProRoomSelect(coordinator, coordinator.rooms),
        YeelightProGroupSelect(coordinator, coordinator.groups),
        YeelightProSceneSelect(coordinator, coordinator.scenes),
    ]

    async_add_entities(entities)
    _LOGGER.info("已添加 %s 个 select 实体", len(entities))


def _extract_options(
    items: list[dict[str, Any]],
    *,
    id_key: str = "id",
    name_key: str = "name",
) -> tuple[list[str], dict[str, str]]:
    """从 API 数据中提取选项名称列表和名称到 ID 的映射.

    返回:
        (选项名称列表, {名称: id 映射})
    """
    name_to_id: dict[str, str] = {}
    options: list[str] = []
    for item in items:
        item_id = item.get(id_key)
        name = item.get(name_key)
        if item_id is not None and name:
            name_str = str(name)
            options.append(name_str)
            name_to_id[name_str] = str(item_id)
    return options, name_to_id


class YeelightProRoomSelect(CoordinatorEntity, SelectEntity):
    """Yeelight Pro 房间选择器."""

    _attr_has_entity_name = True
    _attr_icon = ICON_ROOM
    _attr_translation_key = "active_room"

    def __init__(
        self,
        coordinator: YeelightProCoordinator,
        rooms: list[dict[str, Any]],
    ) -> None:
        """初始化房间选择器."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{coordinator.house_id}_select_room"
        self._selected: str | None = None

        # 设置默认选中第一个房间
        options, _ = _extract_options(rooms)
        if options:
            self._selected = options[0]

    @property
    def device_info(self) -> dict[str, Any]:
        """关联到家庭设备."""
        return {
            "identifiers": {(DOMAIN, str(self.coordinator.house_id))},
            "name": f"Yeelight Pro {self.coordinator.house_id}",
            "manufacturer": "Yeelight",
        }

    @property
    def options(self) -> list[str]:
        """返回可选房间列表."""
        options, _ = _extract_options(self.coordinator.rooms)
        return options if options else [EMPTY_OPTION]

    @property
    def current_option(self) -> str | None:
        """返回当前选中的房间."""
        options, _ = _extract_options(self.coordinator.rooms)
        if not options or self._selected not in options:
            return None
        return self._selected

    async def async_select_option(self, option: str) -> None:
        """选择房间."""
        if option == EMPTY_OPTION:
            return
        _, name_to_id = _extract_options(self.coordinator.rooms)
        if option not in name_to_id:
            raise HomeAssistantError(ERROR_UNKNOWN_ROOM_OPTION)
        self._selected = option
        self.async_write_ha_state()
        _LOGGER.debug("已选择房间: %s (ID: %s)", option, name_to_id[option])


class YeelightProGroupSelect(CoordinatorEntity, SelectEntity):
    """Yeelight Pro 灯组选择器."""

    _attr_has_entity_name = True
    _attr_icon = ICON_GROUP
    _attr_translation_key = "active_group"

    def __init__(
        self,
        coordinator: YeelightProCoordinator,
        groups: list[dict[str, Any]],
    ) -> None:
        """初始化灯组选择器."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{coordinator.house_id}_select_group"
        self._selected: str | None = None

        # 设置默认选中第一个灯组
        options, _ = _extract_options(groups)
        if options:
            self._selected = options[0]

    @property
    def device_info(self) -> dict[str, Any]:
        """关联到家庭设备."""
        return {
            "identifiers": {(DOMAIN, str(self.coordinator.house_id))},
            "name": f"Yeelight Pro {self.coordinator.house_id}",
            "manufacturer": "Yeelight",
        }

    @property
    def options(self) -> list[str]:
        """返回可选灯组列表."""
        options, _ = _extract_options(self.coordinator.groups)
        return options if options else [EMPTY_OPTION]

    @property
    def current_option(self) -> str | None:
        """返回当前选中的灯组."""
        options, _ = _extract_options(self.coordinator.groups)
        if not options or self._selected not in options:
            return None
        return self._selected

    async def async_select_option(self, option: str) -> None:
        """选择灯组."""
        if option == EMPTY_OPTION:
            return
        _, name_to_id = _extract_options(self.coordinator.groups)
        if option not in name_to_id:
            raise HomeAssistantError(ERROR_UNKNOWN_GROUP_OPTION)
        self._selected = option
        self.async_write_ha_state()
        _LOGGER.debug("已选择灯组: %s (ID: %s)", option, name_to_id[option])


class YeelightProSceneSelect(CoordinatorEntity, SelectEntity):
    """Yeelight Pro 场景选择器."""

    _attr_has_entity_name = True
    _attr_icon = ICON_SCENE
    _attr_translation_key = "active_scene"

    def __init__(
        self,
        coordinator: YeelightProCoordinator,
        scenes: list[dict[str, Any]],
    ) -> None:
        """初始化场景选择器."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{coordinator.house_id}_select_scene"
        self._last_executed: str | None = None

    @property
    def device_info(self) -> dict[str, Any]:
        """关联到家庭设备."""
        return {
            "identifiers": {(DOMAIN, str(self.coordinator.house_id))},
            "name": f"Yeelight Pro {self.coordinator.house_id}",
            "manufacturer": "Yeelight",
        }

    @property
    def options(self) -> list[str]:
        """返回可选场景列表."""
        options, _ = _extract_options(self.coordinator.scenes)
        return options if options else [EMPTY_OPTION]

    @property
    def current_option(self) -> str | None:
        """返回最后执行的场景."""
        options, _ = _extract_options(self.coordinator.scenes)
        if not options or self._last_executed not in options:
            return None
        return self._last_executed

    async def async_select_option(self, option: str) -> None:
        """选择并执行场景."""
        if option == EMPTY_OPTION:
            return
        _, name_to_id = _extract_options(self.coordinator.scenes)
        scene_id = name_to_id.get(option)
        if scene_id is None:
            raise HomeAssistantError(ERROR_UNKNOWN_SCENE_OPTION)

        try:
            await self.coordinator.async_execute_scene(scene_id)
            self._last_executed = option
            self.async_write_ha_state()
            _LOGGER.debug("已执行场景: %s (ID: %s)", option, scene_id)
        except YeelightProError as err:
            raise_service_error("select.execute_scene", err)
