"""门锁平台，Yeelight Pro 集成。"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .core.coordinator import YeelightProCoordinator
from .core.exceptions import YeelightProError
from .dynamic_entities import async_track_dynamic_entities
from .entity_errors import raise_service_error
from .projector.lock import HALockProjection, project_lock

_LOGGER = logging.getLogger(__name__)
ERROR_LOCK_PROJECTION_UNAVAILABLE = "无法解析 lock 投影"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """初始化 Yeelight Pro 门锁平台。"""
    coordinator: YeelightProCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    async_track_dynamic_entities(
        config_entry,
        coordinator,
        async_add_entities,
        _iter_lock_entities,
        logger=_LOGGER,
        platform_name="lock",
    )


def _iter_lock_entities(coordinator: YeelightProCoordinator) -> list["YeelightProLock"]:
    """按当前拓扑生成 lock 实体候选。"""
    locks: list[YeelightProLock] = []
    for device_id, device_data in coordinator.data.items():
        if project_lock(device_data, domain=DOMAIN) is not None:
            locks.append(YeelightProLock(coordinator, device_id))
    return locks


class YeelightProLock(CoordinatorEntity, LockEntity):
    """Yeelight Pro 门锁实体。"""

    def __init__(self, coordinator: YeelightProCoordinator, device_id: str):
        """初始化门锁实体。"""
        super().__init__(coordinator)
        self._device_id = device_id
        projection = self._projection
        self._attr_unique_id = (
            projection.unique_id if projection is not None else f"{DOMAIN}_{device_id}_lock"
        )
        self._attr_has_entity_name = True

    @property
    def _projection(self) -> HALockProjection | None:
        """返回最新的门锁投影视图。"""
        return project_lock(self.coordinator.get_device(self._device_id), domain=DOMAIN)

    @property
    def name(self) -> str | None:
        """返回门锁名称。"""
        projection = self._projection
        if projection is not None:
            return projection.name
        device_data = self.coordinator.get_device(self._device_id)
        return device_data.get("name", f"Lock {self._device_id}")

    @property
    def available(self) -> bool:
        """返回门锁是否可用。"""
        projection = self._projection
        if projection is not None:
            return projection.available
        return False

    @property
    def device_info(self):
        """返回设备注册信息。"""
        projection = self._projection
        if projection is not None:
            return projection.device_info
        return None

    @property
    def icon(self) -> str | None:
        """返回实体图标。"""
        projection = self._projection
        if projection is not None:
            return projection.icon
        return None

    @property
    def is_locked(self) -> bool:
        """返回门锁是否已锁定。"""
        projection = self._projection
        if projection is not None:
            return projection.is_locked
        return False

    async def async_lock(self, **kwargs: Any) -> None:
        """锁定门锁。"""
        projection = self._projection
        if projection is None:
            raise HomeAssistantError(ERROR_LOCK_PROJECTION_UNAVAILABLE)
        try:
            await self.coordinator.async_control_device(
                self._device_id,
                {projection.control_key: True},
            )
        except YeelightProError as err:
            raise_service_error("lock.lock", err)

    async def async_unlock(self, **kwargs: Any) -> None:
        """解锁门锁。"""
        projection = self._projection
        if projection is None:
            raise HomeAssistantError(ERROR_LOCK_PROJECTION_UNAVAILABLE)
        try:
            await self.coordinator.async_control_device(
                self._device_id,
                {projection.control_key: False},
            )
        except YeelightProError as err:
            raise_service_error("lock.unlock", err)
