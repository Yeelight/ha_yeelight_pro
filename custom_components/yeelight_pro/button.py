"""Yeelight Pro button 平台.

提供自动化触发按钮和场景执行按钮，支持手动触发自动化和快速执行场景。
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .core.coordinator import YeelightProCoordinator
from .core.exceptions import YeelightProError

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """设置 Yeelight Pro button 平台."""
    coordinator: YeelightProCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    buttons: list[ButtonEntity] = []

    # 从 coordinator 缓存数据创建自动化按钮
    for automation in coordinator.automations:
        if automation.get("id"):
            buttons.append(YeelightProAutomationButton(coordinator, automation))

    # 从 coordinator 缓存数据创建场景按钮
    for scene in coordinator.scenes:
        if scene.get("id"):
            buttons.append(YeelightProSceneButton(coordinator, scene))

    if buttons:
        async_add_entities(buttons)
        _LOGGER.info("已添加 %s 个 button 实体", len(buttons))


def _build_gateway_device_info(
    coordinator: YeelightProCoordinator,
    fallback_name: str,
) -> dict[str, Any] | None:
    """从第一个网关构建设备关联信息."""
    gateways = coordinator.get_gateway_devices()
    if not gateways:
        return None
    first_gateway = next(iter(gateways.values()))
    ha_device = first_gateway.get("ha_device_instance", {})
    identifiers = ha_device.get("device_info", {}).get("identifiers")
    if not identifiers:
        return None
    return {
        "identifiers": {tuple(i) for i in identifiers} if isinstance(identifiers, list) else identifiers,
        "name": fallback_name,
        "manufacturer": "Yeelight",
    }


# 自动化类型到图标的映射
_AUTOMATION_ICON_MAP = {
    "scene": "mdi:palette",
    "timer": "mdi:clock-outline",
    "schedule": "mdi:clock-outline",
    "sensor": "mdi:eye",
}


class YeelightProAutomationButton(ButtonEntity):
    """Yeelight Pro 自动化触发按钮."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:robot"

    def __init__(
        self,
        coordinator: YeelightProCoordinator,
        automation: dict[str, Any],
    ) -> None:
        """初始化自动化按钮."""
        super().__init__()
        self._coordinator = coordinator
        self._automation_id = str(automation["id"])
        self._attr_unique_id = f"{DOMAIN}_automation_{self._automation_id}"
        self._attr_name = automation.get("name", f"自动化 {self._automation_id}")
        # 根据自动化类型设置图标
        auto_type = automation.get("type", "").lower()
        for keyword, icon in _AUTOMATION_ICON_MAP.items():
            if keyword in auto_type:
                self._attr_icon = icon
                break

    @property
    def device_info(self) -> dict[str, Any] | None:
        """返回关联的家庭设备信息."""
        return _build_gateway_device_info(self._coordinator, "Yeelight Pro 自动化")

    async def async_press(self) -> None:
        """触发自动化."""
        try:
            await self._coordinator.async_trigger_automation(self._automation_id)
            _LOGGER.info("自动化触发成功: %s", self._attr_name)
        except YeelightProError as err:
            raise HomeAssistantError(
                f"自动化触发失败: {self._attr_name}: {err}"
            ) from err


class YeelightProSceneButton(ButtonEntity):
    """Yeelight Pro 场景快速执行按钮."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:palette"

    def __init__(
        self,
        coordinator: YeelightProCoordinator,
        scene: dict[str, Any],
    ) -> None:
        """初始化场景按钮."""
        super().__init__()
        self._coordinator = coordinator
        self._scene_id = str(scene["id"])
        self._attr_unique_id = f"{DOMAIN}_scene_{self._scene_id}"
        self._attr_name = scene.get("name", f"场景 {self._scene_id}")

    @property
    def device_info(self) -> dict[str, Any] | None:
        """返回关联的家庭设备信息."""
        return _build_gateway_device_info(self._coordinator, "Yeelight Pro 场景")

    async def async_press(self) -> None:
        """执行场景."""
        try:
            await self._coordinator.async_execute_scene(self._scene_id)
            _LOGGER.info("场景执行成功: %s", self._attr_name)
        except YeelightProError as err:
            raise HomeAssistantError(
                f"场景执行失败: {self._attr_name}: {err}"
            ) from err
