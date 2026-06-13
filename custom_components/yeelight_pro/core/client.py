"""Yeelight Pro HTTP 客户端.

支持云端和私有部署两种模式，提供统一的 API 访问接口。
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiohttp import ClientSession, ClientTimeout

from ..const import DEFAULT_REQUEST_TIMEOUT
from ..scan_login_contract import YeelightScanLoginQrCode
from .client_node_api import YeelightProNodeApiMixin
from .client_request import build_client_headers, request_json
from .exceptions import (
    AuthenticationError,
    ConnectionError,
    TokenExpiredError,
    safe_error_summary,
)
from .scan_login import (
    check_scan_login_qrcode as _check_scan_login_qrcode,
    create_scan_login_qrcode as _create_scan_login_qrcode,
)


class YeelightProClient(YeelightProNodeApiMixin):
    """Yeelight Pro HTTP 客户端."""

    def __init__(
        self,
        domain: str,
        access_token: str,
        session: ClientSession,
        client_id: str | None = None,
        timeout: int = DEFAULT_REQUEST_TIMEOUT,
    ):
        """初始化客户端."""
        self.domain = domain.rstrip("/")
        self.access_token = access_token
        self.client_id = client_id.strip() if isinstance(client_id, str) else ""
        self.session = session
        self.timeout = ClientTimeout(total=timeout)
        self._connected = False
        self._token_refresh_handler: Callable[[], Awaitable[None]] | None = None

    def set_token_refresh_handler(
        self,
        handler: Callable[[], Awaitable[None]] | None,
    ) -> None:
        """Attach a one-shot token refresh hook used after 401 responses."""
        self._token_refresh_handler = handler

    @property
    def base_url(self) -> str:
        """返回基础 URL."""
        if not self.domain.startswith(("http://", "https://")):
            return f"https://{self.domain}"
        return self.domain

    def _get_headers(self, *, with_auth: bool = True) -> dict[str, str]:
        """获取请求头."""
        return build_client_headers(
            access_token=self.access_token,
            client_id=self.client_id,
            with_auth=with_auth,
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        with_auth: bool = True,
        _retry_on_token_refresh: bool = True,
        **kwargs,
    ) -> dict[str, Any]:
        """发送 HTTP 请求。"""
        try:
            return await self._request_once(
                method,
                path,
                with_auth=with_auth,
                **kwargs,
            )
        except TokenExpiredError:
            if not with_auth or not _retry_on_token_refresh:
                raise
            handler = self._token_refresh_handler
            if handler is None:
                raise
            await handler()
            return await self._request_once(
                method,
                path,
                with_auth=with_auth,
                **kwargs,
            )

    async def _request_once(
        self,
        method: str,
        path: str,
        *,
        with_auth: bool = True,
        **kwargs,
    ) -> dict[str, Any]:
        """Send one HTTP request without automatic token refresh."""
        base = self.base_url.rstrip("/")
        url = f"{base}{path}"
        return await request_json(
            self.session,
            self.timeout,
            method,
            url,
            headers=self._get_headers(with_auth=with_auth),
            **kwargs,
        )

    async def create_scan_login_qrcode(
        self,
        *,
        region: str,
        device: str,
    ) -> YeelightScanLoginQrCode:
        """Create a Yeelight APP scan-login QR code state."""
        return await _create_scan_login_qrcode(
            self.session,
            self.timeout,
            region=region,
            device=device,
        )

    async def check_scan_login_qrcode(
        self,
        *,
        region: str,
        qr_code_id: str,
    ) -> YeelightScanLoginQrCode:
        """Poll a Yeelight APP scan-login QR code state."""
        return await _check_scan_login_qrcode(
            self.session,
            self.timeout,
            region=region,
            qr_code_id=qr_code_id,
        )

    async def check_health(self) -> bool:
        """检查服务端健康状态（需要认证）.

        用于启动时验证服务是否可达。
        """
        try:
            # 使用 get_houses 来验证连接和认证
            await self.get_houses()
            self._connected = True
            return True
        except AuthenticationError:
            self._connected = False
            raise
        except Exception as err:
            self._connected = False
            raise ConnectionError(
                f"Health check failed: {safe_error_summary(err)}"
            ) from None

    async def validate_auth(self) -> bool:
        """验证认证凭据有效性（需要 token）.

        通过调用需要认证的 API 端点来验证 token 是否有效。
        config_flow 配置流程应使用此方法而非 check_health。
        """
        try:
            await self.get_houses()
            self._connected = True
            return True
        except AuthenticationError:
            self._connected = False
            raise
        except Exception as err:
            self._connected = False
            raise ConnectionError(
                f"Auth validation failed: {safe_error_summary(err)}"
            ) from None

    async def disconnect(self) -> None:
        """断开连接."""
        self._connected = False
