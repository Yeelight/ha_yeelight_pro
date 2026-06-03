"""Yeelight Pro 文本平台.

提供设备名称显示/编辑、设备标签显示/编辑和自动化名称显示功能。
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .core.coordinator import YeelightProCoordinator

_LOGGER = logging.getLogger(__name__)

# 文本实体图标
ICON_DEVICE_NAME = "mdi:label-outline"
ICON_DEVICE_LABEL = "mdi:tag-outline"
ICON_AUTOMATION_NAME = "mdi:robot-outline"

# 文本长度限制
MAX_TEXT_LENGTH = 255


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """设置 Yeelight Pro 文本平台."""
    coordinator: YeelightProCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    entities: list[TextEntity] = []

    # 为每个设备创建名称和标签实体
    for device_id, device_data in coordinator.devices.items():
        device_name = device_data.get("name", f"设备 {device_id}")

        # 设备名称实体
        entities.append(
            YeelightProDeviceName(coordinator, device_id, device_name)
        )

        # 设备标签实体（如果设备有标签字段）
        if "label" in device_data or "tags" in device_data:
            entities.append(
                YeelightProDeviceLabel(coordinator, device_id, device_name)
            )

    # 为自动化创建只读名称实体
    try:
        automations = await coordinator.client.get_automations(coordinator.house_id)
        for automation in automations:
            if automation.get("id"):
                entities.append(
                    YeelightProAutomationName(coordinator, automation)
                )
    except Exception as err:
        _LOGGER.warning("获取自动化列表失败: %s", err)

    if entities:
        async_add_entities(entities)
        _LOGGER.info("已添加 %s 个 text 实体", len(entities))


class YeelightProDeviceName(CoordinatorEntity, TextEntity):
    """Yeelight Pro 设备名称实体.

    显示和编辑设备名称，如果 API 不支持编辑则降级为只读。
    """

    _attr_has_entity_name = True
    _attr_icon = ICON_DEVICE_NAME
    _attr_native_max = MAX_TEXT_LENGTH
    _attr_mode = "text"
    _attr_translation_key = "device_name"

    def __init__(
        self,
        coordinator: YeelightProCoordinator,
        device_id: int,
        device_name: str,
    ) -> None:
        """初始化设备名称实体."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"{DOMAIN}_device_{device_id}_name"
        self._attr_native_value = device_name

    @property
    def device_info(self) -> dict[str, Any]:
        """返回关联的家庭设备信息."""
        return {
            "identifiers": {(DOMAIN, str(self._device_id))},
            "name": self._attr_native_value or f"设备 {self._device_id}",
            "manufacturer": "Yeelight",
        }

    @property
    def available(self) -> bool:
        """设备是否可用."""
        return self.coordinator.last_update_success

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """返回额外状态属性."""
        return {
            "device_id": self._device_id,
            "editable": self._is_editable,
        }

    @property
    def _is_editable(self) -> bool:
        """检查是否支持编辑（API 暂不支持，降级为只读）."""
        # TODO: 当 API 支持设备名称修改时，检查客户端方法
        return False

    async def async_set_value(self, value: str) -> None:
        """设置设备名称."""
        if not self._is_editable:
            _LOGGER.warning("设备名称编辑暂不支持: device_id=%s", self._device_id)
            return

        if len(value) > MAX_TEXT_LENGTH:
            _LOGGER.error("设备名称长度超过限制: %s > %s", len(value), MAX_TEXT_LENGTH)
            return

        try:
            # TODO: 调用 API 更新设备名称
            # success = await self.coordinator.client.update_device_name(
            #     self._device_id, value
            # )
            # if success:
            #     self._attr_native_value = value
            #     self.async_write_ha_state()
            #     _LOGGER.debug("设备名称已更新: %s -> %s", self._device_id, value)
            # else:
            #     _LOGGER.error("更新设备名称失败: %s", self._device_id)
            _LOGGER.debug("设备名称编辑功能待实现: %s", self._device_id)
        except Exception as err:
            _LOGGER.error("更新设备名称异常: %s - %s", self._device_id, err)

    def _handle_coordinator_update(self) -> None:
        """处理协调器数据更新."""
        device_data = self.coordinator.get_device(self._device_id)
        if device_data:
            self._attr_native_value = device_data.get("name", self._attr_native_value)
        super()._handle_coordinator_update()


class YeelightProDeviceLabel(CoordinatorEntity, TextEntity):
    """Yeelight Pro 设备标签实体.

    显示和编辑设备标签/备注，如果 API 不支持编辑则降级为只读。
    """

    _attr_has_entity_name = True
    _attr_icon = ICON_DEVICE_LABEL
    _attr_native_max = MAX_TEXT_LENGTH
    _attr_mode = "text"
    _attr_translation_key = "device_label"

    def __init__(
        self,
        coordinator: YeelightProCoordinator,
        device_id: int,
        device_name: str,
    ) -> None:
        """初始化设备标签实体."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._device_name = device_name
        self._attr_unique_id = f"{DOMAIN}_device_{device_id}_label"
        self._attr_native_value = self._get_device_label()

    @property
    def device_info(self) -> dict[str, Any]:
        """返回关联的家庭设备信息."""
        return {
            "identifiers": {(DOMAIN, str(self._device_id))},
            "name": self._device_name,
            "manufacturer": "Yeelight",
        }

    @property
    def available(self) -> bool:
        """设备是否可用."""
        return self.coordinator.last_update_success

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """返回额外状态属性."""
        return {
            "device_id": self._device_id,
            "editable": self._is_editable,
        }

    @property
    def _is_editable(self) -> bool:
        """检查是否支持编辑（API 暂不支持，降级为只读）."""
        # TODO: 当 API 支持设备标签修改时，检查客户端方法
        return False

    def _get_device_label(self) -> str:
        """获取设备标签."""
        device_data = self.coordinator.get_device(self._device_id)
        if device_data:
            # 优先使用 label，其次使用 tags
            label = device_data.get("label", "")
            if label:
                return label
            tags = device_data.get("tags", [])
            if tags:
                return ", ".join(str(tag) for tag in tags)
        return ""

    async def async_set_value(self, value: str) -> None:
        """设置设备标签."""
        if not self._is_editable:
            _LOGGER.warning("设备标签编辑暂不支持: device_id=%s", self._device_id)
            return

        if len(value) > MAX_TEXT_LENGTH:
            _LOGGER.error("设备标签长度超过限制: %s > %s", len(value), MAX_TEXT_LENGTH)
            return

        try:
            # TODO: 调用 API 更新设备标签
            # success = await self.coordinator.client.update_device_label(
            #     self._device_id, value
            # )
            # if success:
            #     self._attr_native_value = value
            #     self.async_write_ha_state()
            #     _LOGGER.debug("设备标签已更新: %s -> %s", self._device_id, value)
            # else:
            #     _LOGGER.error("更新设备标签失败: %s", self._device_id)
            _LOGGER.debug("设备标签编辑功能待实现: %s", self._device_id)
        except Exception as err:
            _LOGGER.error("更新设备标签异常: %s - %s", self._device_id, err)

    def _handle_coordinator_update(self) -> None:
        """处理协调器数据更新."""
        self._attr_native_value = self._get_device_label()
        super()._handle_coordinator_update()


class YeelightProAutomationName(CoordinatorEntity, TextEntity):
    """Yeelight Pro 自动化名称实体.

    只读显示自动化名称，不支持编辑。
    """

    _attr_has_entity_name = True
    _attr_icon = ICON_AUTOMATION_NAME
    _attr_mode = "text"
    _attr_native_max = MAX_TEXT_LENGTH
    _attr_translation_key = "automation_name"

    def __init__(
        self,
        coordinator: YeelightProCoordinator,
        automation: dict[str, Any],
    ) -> None:
        """初始化自动化名称实体."""
        super().__init__(coordinator)
        self._automation_id = str(automation["id"])
        self._attr_unique_id = f"{DOMAIN}_automation_{self._automation_id}_name"
        self._attr_native_value = automation.get("name", f"自动化 {self._automation_id}")
        self._automation_type = automation.get("type", "")

    @property
    def device_info(self) -> dict[str, Any] | None:
        """返回关联的家庭设备信息（关联到第一个网关）."""
        gateways = self.coordinator.get_gateway_devices()
        if not gateways:
            return None
        first_gateway = next(iter(gateways.values()))
        ha_device = first_gateway.get("ha_device_instance", {})
        identifiers = ha_device.get("device_info", {}).get("identifiers")
        if not identifiers:
            return None
        return {
            "identifiers": {tuple(i) for i in identifiers} if isinstance(identifiers, list) else identifiers,
            "name": "Yeelight Pro 自动化",
            "manufacturer": "Yeelight",
        }

    @property
    def available(self) -> bool:
        """设备是否可用."""
        return self.coordinator.last_update_success

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """返回额外状态属性."""
        return {
            "automation_id": self._automation_id,
            "automation_type": self._automation_type,
            "editable": False,
        }

    async def async_set_value(self, value: str) -> None:
        """设置自动化名称（不支持）."""
        _LOGGER.warning("自动化名称不支持编辑: automation_id=%s", self._automation_id)
