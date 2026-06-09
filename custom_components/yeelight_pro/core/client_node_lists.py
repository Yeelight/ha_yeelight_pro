"""Yeelight Pro Open API list and snapshot operations."""

from __future__ import annotations

from .client_node_base import YeelightProNodeRequestMixin
from .client_paths import (
    house_areas_path,
    house_automations_path,
    house_devices_path,
    house_gateways_path,
    house_groups_path,
    house_list_path,
    house_rooms_path,
    house_scenes_path,
    house_snapshot_path,
)


class YeelightProNodeListMixin(YeelightProNodeRequestMixin):
    """开放平台节点列表和家庭快照接口."""

    async def get_houses(self) -> list[dict[str, object]]:
        """获取用户的所有家庭列表."""
        return await self._get_paginated_rows(house_list_path())

    async def get_devices(
        self,
        house_id: int,
        *,
        room_id: int | str | None = None,
    ) -> list[dict[str, object]]:
        """获取设备列表."""
        return await self._get_paginated_rows(
            house_devices_path(house_id, room_id=room_id)
        )

    async def get_gateways(self, house_id: int) -> list[dict[str, object]]:
        """获取网关列表."""
        return await self._get_paginated_rows(house_gateways_path(house_id))

    async def get_rooms(self, house_id: int) -> list[dict[str, object]]:
        """获取房间列表."""
        return await self._get_paginated_rows(house_rooms_path(house_id))

    async def get_groups(
        self,
        house_id: int,
        *,
        room_id: int | str | None = None,
    ) -> list[dict[str, object]]:
        """获取灯组列表."""
        return await self._get_paginated_rows(
            house_groups_path(house_id, room_id=room_id)
        )

    async def get_scenes(self, house_id: int) -> list[dict[str, object]]:
        """获取场景列表."""
        return await self._get_paginated_rows(house_scenes_path(house_id))

    async def get_automations(self, house_id: int) -> list[dict[str, object]]:
        """获取自动化列表."""
        return await self._get_paginated_rows(house_automations_path(house_id))

    async def get_areas(self, house_id: int) -> list[dict[str, object]]:
        """获取区域列表."""
        return await self._get_paginated_rows(house_areas_path(house_id))

    async def get_house_snapshot(self, house_id: int) -> dict[str, object]:
        """获取家庭快照."""
        return await self._request("GET", house_snapshot_path(house_id))
