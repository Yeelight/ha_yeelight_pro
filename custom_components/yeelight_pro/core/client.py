"""Yeelight Pro HTTP 客户端.

支持云端和私有部署两种模式，提供统一的 API 访问接口。
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Mapping
from urllib.parse import urljoin

import aiohttp
from aiohttp import ClientSession, ClientTimeout

from ..const import (
    DEFAULT_PRODUCT_SCHEMA_BATCH_SIZE,
    DEFAULT_REQUEST_TIMEOUT,
    DEFAULT_THING_MANAGE_PAGE_SIZE,
)
from .exceptions import (
    AuthenticationError,
    CommandError,
    ConnectionError,
    DeviceNotFoundError,
    RateLimitError,
    ServerError,
    TokenExpiredError,
)

_LOGGER = logging.getLogger(__name__)


class YeelightProClient:
    """Yeelight Pro HTTP 客户端."""

    def __init__(
        self,
        domain: str,
        access_token: str,
        session: ClientSession,
        timeout: int = DEFAULT_REQUEST_TIMEOUT,
    ):
        """初始化客户端."""
        self.domain = domain.rstrip("/")
        self.access_token = access_token
        self.session = session
        self.timeout = ClientTimeout(total=timeout)
        self._connected = False
        self._request_seq = 0

    @property
    def base_url(self) -> str:
        """返回基础 URL."""
        if not self.domain.startswith(("http://", "https://")):
            return f"https://{self.domain}"
        return self.domain

    def _get_headers(self, *, with_auth: bool = True) -> dict[str, str]:
        """获取请求头."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if with_auth and self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def _next_request_id(self) -> str:
        """生成请求 ID."""
        self._request_seq += 1
        return f"ha-yeelight-{uuid.uuid4().hex[:8]}-{self._request_seq}"

    async def _request(
        self,
        method: str,
        path: str,
        *,
        with_auth: bool = True,
        **kwargs,
    ) -> dict[str, Any]:
        """发送 HTTP 请求."""
        url = urljoin(self.base_url, path)

        try:
            async with self.session.request(
                method,
                url,
                headers=self._get_headers(with_auth=with_auth),
                timeout=self.timeout,
                **kwargs,
            ) as response:
                # 处理认证错误
                if response.status == 401:
                    raise TokenExpiredError("Access token expired or invalid")
                if response.status == 403:
                    raise AuthenticationError("Access denied")

                # 处理频率限制
                if response.status == 429:
                    raise RateLimitError("Rate limit exceeded")

                # 处理服务器错误
                if response.status >= 500:
                    raise ServerError(f"Server error: HTTP {response.status}")

                # 处理客户端错误
                if response.status >= 400:
                    error_text = await response.text()
                    raise CommandError(f"HTTP {response.status}: {error_text}")

                return await response.json()

        except aiohttp.ClientError as err:
            raise ConnectionError(f"Connection error: {err}") from err

    async def validate_connection(self) -> bool:
        """验证连接."""
        try:
            await self._request("GET", "/healthz", with_auth=False)
            self._connected = True
            return True
        except Exception as err:
            self._connected = False
            raise ConnectionError(f"Connection validation failed: {err}") from err

    async def get_houses(self) -> list[dict[str, Any]]:
        """获取家庭列表."""
        response = await self._request("GET", "/v1/ha/houses")
        return response.get("houses", [])

    async def get_devices(self, house_id: int) -> list[dict[str, Any]]:
        """获取设备列表."""
        all_devices = []
        page = 1
        page_size = DEFAULT_THING_MANAGE_PAGE_SIZE

        while True:
            response = await self._request(
                "POST",
                f"/apis/iot/v2/thing/manage/house/{house_id}/device/r/info/{page}/{page_size}",
            )

            data = response.get("data", {})
            rows = data.get("rows", [])
            total = data.get("total", 0)

            all_devices.extend(rows)

            if len(all_devices) >= total or not rows:
                break

            page += 1

        return all_devices

    async def get_gateways(self, house_id: int) -> list[dict[str, Any]]:
        """获取网关列表."""
        all_gateways = []
        page = 1
        page_size = DEFAULT_THING_MANAGE_PAGE_SIZE

        while True:
            response = await self._request(
                "GET",
                f"/apis/iot/v2/thing/manage/house/{house_id}/gateway/r/info/{page}/{page_size}",
            )

            data = response.get("data", {})
            rows = data.get("rows", [])
            total = data.get("total", 0)

            all_gateways.extend(rows)

            if len(all_gateways) >= total or not rows:
                break

            page += 1

        return all_gateways

    async def get_product_schemas(
        self,
        product_ids: list[int],
    ) -> dict[int, dict[str, Any]]:
        """获取产品规格."""
        schemas = {}

        # 分批处理
        for i in range(0, len(product_ids), DEFAULT_PRODUCT_SCHEMA_BATCH_SIZE):
            batch = product_ids[i:i + DEFAULT_PRODUCT_SCHEMA_BATCH_SIZE]
            pids_param = "&".join(f"pids={pid}" for pid in batch)

            response = await self._request(
                "GET",
                f"/apis/iot/v2/thing/schema/product/r/info?{pids_param}",
                with_auth=False,
            )

            data = response.get("data", {})
            for schema in data.get("schemas", []):
                pid = schema.get("pid")
                if pid:
                    schemas[pid] = schema

        return schemas

    async def control_device(
        self,
        device_id: int,
        gateway_id: int,
        params: dict[str, Any],
        duration: int = 500,
    ) -> bool:
        """控制设备."""
        request_id = self._next_request_id()

        payload = {
            "slot_type": "device",
            "gateway_ids": [gateway_id],
            "message": {
                "id": 1,
                "method": "gateway_set.prop",
                "nodes": [
                    {
                        "id": device_id,
                        "nt": 2,
                        "duration": duration,
                        "delay": 0,
                        "set": params,
                    }
                ],
            },
            "request_id": request_id,
        }

        await self._request("POST", "/v1/control/device", json=payload)
        return True

    async def toggle_device(
        self,
        device_id: int,
        gateway_id: int,
        properties: list[str],
    ) -> bool:
        """切换设备属性."""
        request_id = self._next_request_id()

        payload = {
            "slot_type": "device",
            "gateway_ids": [gateway_id],
            "message": {
                "id": 1,
                "method": "gateway_set.prop",
                "nodes": [
                    {
                        "id": device_id,
                        "nt": 2,
                        "toggle": properties,
                    }
                ],
            },
            "request_id": request_id,
        }

        await self._request("POST", "/v1/control/device", json=payload)
        return True

    async def execute_scene(self, scene_id: str) -> bool:
        """执行场景."""
        request_id = self._next_request_id()

        payload = {
            "message": {
                "id": 1,
                "method": "gateway_set.prop",
                "scenes": [{"id": scene_id, "duration": 500}],
            },
            "request_id": request_id,
        }

        await self._request("POST", "/v1/control/scene", json=payload)
        return True

    async def get_rooms(self, house_id: int) -> list[dict[str, Any]]:
        """获取房间列表.

        Args:
            house_id: 家庭 ID

        Returns:
            房间列表，每个房间包含 id、name 等信息
        """
        response = await self._request("GET", f"/v1/ha/houses/{house_id}/rooms")
        return response.get("rooms", [])

    async def get_groups(self, house_id: int) -> list[dict[str, Any]]:
        """获取灯组列表.

        Args:
            house_id: 家庭 ID

        Returns:
            灯组列表，每个灯组包含 id、name、设备列表等信息
        """
        response = await self._request("GET", f"/v1/ha/houses/{house_id}/groups")
        return response.get("groups", [])

    async def control_group(
        self,
        group_id: str,
        params: dict[str, Any],
        duration: int = 500,
    ) -> bool:
        """控制灯组.

        Args:
            group_id: 灯组 ID
            params: 控制参数，如 {"power": "on", "brightness": 100}
            duration: 过渡时间，单位毫秒

        Returns:
            控制命令是否发送成功
        """
        request_id = self._next_request_id()

        payload = {
            "id": group_id,
            "duration": duration,
            "set": params,
            "request_id": request_id,
        }

        await self._request("POST", "/v1/control/group", json=payload)
        return True

    async def get_scenes(self, house_id: int) -> list[dict[str, Any]]:
        """获取场景列表.

        Args:
            house_id: 家庭 ID

        Returns:
            场景列表，每个场景包含 id、name 等信息
        """
        response = await self._request("GET", f"/v1/ha/houses/{house_id}/scenes")
        return response.get("scenes", [])

    async def get_automations(self, house_id: int) -> list[dict[str, Any]]:
        """获取自动化列表.

        Args:
            house_id: 家庭 ID

        Returns:
            自动化列表，每个自动化包含 id、name、状态等信息
        """
        response = await self._request(
            "GET", f"/v1/ha/houses/{house_id}/automations"
        )
        return response.get("automations", [])

    async def enable_automation(self, automation_id: str) -> bool:
        """启用自动化.

        Args:
            automation_id: 自动化 ID

        Returns:
            操作是否成功
        """
        await self._request("POST", f"/v1/automation/{automation_id}/enable")
        return True

    async def disable_automation(self, automation_id: str) -> bool:
        """禁用自动化.

        Args:
            automation_id: 自动化 ID

        Returns:
            操作是否成功
        """
        await self._request("POST", f"/v1/automation/{automation_id}/disable")
        return True

    async def trigger_automation(self, automation_id: str) -> bool:
        """手动触发自动化.

        Args:
            automation_id: 自动化 ID

        Returns:
            操作是否成功
        """
        await self._request("POST", f"/v1/automation/{automation_id}/trigger")
        return True

    async def get_areas(self, house_id: int) -> list[dict[str, Any]]:
        """获取区域列表.

        Args:
            house_id: 家庭 ID

        Returns:
            区域列表，每个区域包含 id、name 等信息
        """
        response = await self._request("GET", f"/v1/ha/houses/{house_id}/areas")
        return response.get("areas", [])

    async def get_house_snapshot(self, house_id: int) -> dict[str, Any]:
        """获取家庭快照."""
        return await self._request("GET", f"/v1/ha/houses/{house_id}/snapshot")

    async def disconnect(self) -> None:
        """断开连接."""
        self._connected = False
