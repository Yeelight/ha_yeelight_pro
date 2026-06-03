"""Yeelight Pro 场景平台."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.scene import Scene
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .core.coordinator import YeelightProCoordinator

_LOGGER = logging.getLogger(__name__)

# 场景图标默认值
DEFAULT_SCENE_ICON = "mdi:palette"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """设置 Yeelight Pro 场景平台."""
    coordinator: YeelightProCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    try:
        scenes = await coordinator.client.get_scenes(coordinator.house_id)
    except Exception as err:
        _LOGGER.warning("获取场景列表失败: %s", err)
        return

    if not scenes:
        _LOGGER.debug("家庭 %s 下无场景数据", coordinator.house_id)
        return

    entities = [
        YeelightProScene(
            coordinator=coordinator,
            scene_id=str(scene["id"]),
            name=scene.get("name", f"Scene {scene['id']}"),
            icon=scene.get("icon"),
        )
        for scene in scenes
        if scene.get("id")
    ]

    if entities:
        async_add_entities(entities)
        _LOGGER.info("已添加 %s 个 scene 实体", len(entities))


class YeelightProScene(Scene):
    """Yeelight Pro 场景实体."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: YeelightProCoordinator,
        scene_id: str,
        *,
        name: str,
        icon: str | None = None,
    ) -> None:
        """初始化场景实体."""
        self._coordinator = coordinator
        self._scene_id = scene_id
        self._attr_unique_id = f"{DOMAIN}_scene_{scene_id}"
        self._attr_name = name
        self._attr_icon = icon or DEFAULT_SCENE_ICON

    @property
    def device_info(self) -> dict[str, Any]:
        """关联到家庭设备."""
        return {
            "identifiers": {(DOMAIN, str(self._coordinator.house_id))},
            "name": f"Yeelight Pro {self._coordinator.house_id}",
            "manufacturer": "Yeelight",
        }

    async def async_activate(self, **kwargs: Any) -> None:
        """激活场景."""
        success = await self._coordinator.async_execute_scene(self._scene_id)
        if not success:
            _LOGGER.error("激活场景失败: %s (%s)", self._attr_name, self._scene_id)
