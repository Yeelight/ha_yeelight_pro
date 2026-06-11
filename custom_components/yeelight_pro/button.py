"""Yeelight Pro button 平台.

提供场景执行按钮，支持快速执行云端情景。
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .core.coordinator import YeelightProCoordinator
from .core.exceptions import YeelightProError
from .dynamic_entities import async_track_dynamic_entities
from .entity_errors import raise_service_error
from .house_metadata import house_device_info
from .scene_helpers import scene_row_id, scene_row_name

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """设置 Yeelight Pro button 平台."""
    coordinator: YeelightProCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    async_track_dynamic_entities(
        config_entry,
        coordinator,
        async_add_entities,
        _iter_button_entities,
        logger=_LOGGER,
        platform_name="button",
    )


def _iter_button_entities(coordinator: YeelightProCoordinator) -> list[ButtonEntity]:
    """按当前拓扑生成 button 实体候选."""
    buttons: list[ButtonEntity] = []

    for scene in coordinator.scenes:
        if scene_row_id(scene) is not None:
            buttons.append(YeelightProSceneButton(coordinator, scene))

    return buttons


def _build_gateway_device_info(
    coordinator: YeelightProCoordinator,
    fallback_name: str,
) -> dict[str, Any] | None:
    """从第一个网关构建设备关联信息."""
    gateways = coordinator.get_gateway_devices()
    if not gateways:
        return house_device_info(coordinator, name_suffix=fallback_name)
    first_gateway = next(iter(gateways.values()))
    ha_device = first_gateway.get("ha_device_instance", {})
    device_info = ha_device.get("device_info", {})
    identifiers = device_info.get("identifiers")
    if not identifiers:
        return house_device_info(coordinator, name_suffix=fallback_name)
    normalized = dict(device_info) if isinstance(device_info, dict) else {}
    normalized["identifiers"] = (
        {tuple(i) for i in identifiers} if isinstance(identifiers, list) else identifiers
    )
    return normalized


class YeelightProSceneButton(CoordinatorEntity, ButtonEntity):
    """Yeelight Pro 场景快速执行按钮."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:palette"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: YeelightProCoordinator,
        scene: dict[str, Any],
    ) -> None:
        """初始化场景按钮."""
        super().__init__(coordinator)
        self._coordinator = coordinator
        scene_id = scene_row_id(scene)
        if scene_id is None:
            raise ValueError("scene row missing id")
        self._scene_id = scene_id
        self._attr_unique_id = f"{DOMAIN}_scene_{self._scene_id}"
        self._attr_name = scene_row_name(scene, self._scene_id)

    @property
    def device_info(self) -> dict[str, Any] | None:
        """返回关联的家庭设备信息."""
        return _build_gateway_device_info(self._coordinator, "场景")

    async def async_press(self) -> None:
        """执行场景."""
        try:
            await self._coordinator.async_execute_scene(self._scene_id)
            _LOGGER.info("场景执行成功: %s", self._attr_name)
        except YeelightProError as err:
            raise_service_error("button.execute_scene", err)
