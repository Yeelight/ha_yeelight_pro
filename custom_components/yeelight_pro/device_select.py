"""Yeelight Pro device-level select entities."""

from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .core.coordinator import YeelightProCoordinator
from .core.exceptions import YeelightProError
from .device_display import suggested_entity_object_id
from .entity_device_id import source_device_id
from .entity_category import ha_entity_category
from .entity_errors import raise_service_error
from .identity import device_entity_unique_id
from .projector.property_controls import (
    HASelectControlProjection,
    project_select_controls,
)

EMPTY_OPTION = "无可用选项"
ERROR_UNKNOWN_DEVICE_OPTION = "未知设备选项"
ERROR_SELECT_PROJECTION_UNAVAILABLE = "无法解析 select 投影"


def iter_device_select_entities(
    coordinator: YeelightProCoordinator,
) -> list["YeelightProDeviceSelect"]:
    """按当前拓扑生成设备级 select 实体候选."""
    entities: list[YeelightProDeviceSelect] = []
    for device_key, device_data in coordinator.data.items():
        device_id = source_device_id(device_key, device_data)
        for projection in project_select_controls(device_data, domain=DOMAIN):
            entities.append(
                YeelightProDeviceSelect(
                    coordinator,
                    device_id,
                    component_id=projection.component_id,
                )
            )
    return entities


class YeelightProDeviceSelect(CoordinatorEntity, SelectEntity):
    """设备级可写枚举属性选择器."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: YeelightProCoordinator,
        device_id: int | str,
        *,
        component_id: str,
    ) -> None:
        """初始化设备级选择器."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._component_id = component_id
        projection = self._projection
        self._attr_unique_id = (
            projection.unique_id
            if projection is not None
            else device_entity_unique_id(coordinator, device_id, component_id)
        )

    @property
    def _projection(self) -> HASelectControlProjection | None:
        device = self.coordinator.get_device(self._device_id)
        if not device:
            return None
        return next(
            (
                item
                for item in project_select_controls(device, domain=DOMAIN)
                if item.component_id == self._component_id
            ),
            None,
        )

    @property
    def name(self) -> str | None:
        projection = self._projection
        return projection.name if projection is not None else None

    @property
    def suggested_object_id(self) -> str | None:
        """返回 HA 首次注册时使用的友好实体 ID 建议."""
        return suggested_entity_object_id(
            self.coordinator.get_device(self._device_id),
            entity_name=self.name,
            fallback_id=self._device_id,
        )

    @property
    def available(self) -> bool:
        projection = self._projection
        return projection.available if projection is not None else False

    @property
    def icon(self) -> str | None:
        projection = self._projection
        return projection.icon if projection is not None else "mdi:form-dropdown"

    @property
    def device_info(self) -> dict[str, Any]:
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
    def options(self) -> list[str]:
        """返回可选枚举标签."""
        projection = self._projection
        if projection is None:
            return [EMPTY_OPTION]
        return [item.label for item in projection.options] or [EMPTY_OPTION]

    @property
    def current_option(self) -> str | None:
        """返回当前枚举标签."""
        projection = self._projection
        if projection is None:
            return None
        for option in projection.options:
            if str(option.value) == str(projection.value):
                return option.label
        return None

    async def async_select_option(self, option: str) -> None:
        """设置设备级枚举属性."""
        if option == EMPTY_OPTION:
            return
        projection = self._projection
        if projection is None:
            raise HomeAssistantError(ERROR_SELECT_PROJECTION_UNAVAILABLE)

        option_map = {item.label: item.value for item in projection.options}
        if option not in option_map:
            raise HomeAssistantError(ERROR_UNKNOWN_DEVICE_OPTION)
        try:
            await self.coordinator.async_control_device(
                self._device_id,
                {projection.control_key: option_map[option]},
            )
        except YeelightProError as err:
            raise_service_error("select.set_device_property", err)


__all__ = [
    "YeelightProDeviceSelect",
    "iter_device_select_entities",
]
