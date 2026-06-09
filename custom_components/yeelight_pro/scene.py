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
from .core.exceptions import YeelightProError
from .dynamic_entities import async_track_dynamic_entities
from .entity_errors import raise_service_error

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

    async_track_dynamic_entities(
        config_entry,
        coordinator,
        async_add_entities,
        _iter_scene_entities,
        logger=_LOGGER,
        platform_name="scene",
    )


def _iter_scene_entities(coordinator: YeelightProCoordinator) -> list["YeelightProScene"]:
    """按当前拓扑生成 scene 实体候选."""
    return [
        YeelightProScene(
            coordinator=coordinator,
            scene_id=str(scene["id"]),
            name=scene.get("name", f"Scene {scene['id']}"),
            icon=scene.get("icon"),
        )
        for scene in coordinator.scenes
        if scene.get("id")
    ]


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
        try:
            await self._coordinator.async_execute_scene(self._scene_id)
        except YeelightProError as err:
            raise_service_error("scene.activate", err)
