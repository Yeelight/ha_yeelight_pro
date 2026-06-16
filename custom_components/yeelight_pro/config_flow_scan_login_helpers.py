"""Pure helpers for Yeelight APP scan-login config-flow steps."""
from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from dataclasses import dataclass
import hashlib
from typing import Any, cast

import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.helpers import instance_id
from homeassistant.helpers import selector

from .const import (
    CONF_ACCESS_TOKEN,
    CONF_ACCOUNT_USER_ID,
    CONF_ACCOUNT_USERNAME,
    CONF_OPEN_API_CLIENT_ID,
    CONF_OPEN_API_CLIENT_SECRET,
    CONF_REFRESH_TOKEN,
    CONF_SCAN_LOGIN_DEVICE,
    CONF_SCAN_LOGIN_QRCODE,
    CONF_SCAN_LOGIN_REFRESH,
    CONF_TOKEN_EXPIRES_IN,
    CONF_TOKEN_TYPE,
)
from .config_flow_account import (
    account_identity,
    account_key_from_identity,
)
from .scan_login_contract import (
    ScanLoginStatus,
    YeelightAccountToken,
    YeelightScanLoginQrCode,
)

SCAN_LOGIN_POLL_INTERVAL_SECONDS = 2.0


@dataclass(slots=True)
class ScanLoginFlowState:
    """用户扫码登录流程中的可展示状态。"""

    qr_code: YeelightScanLoginQrCode | None = None
    poll_count: int = 0
    last_error: str | None = None


def cloud_scan_login_schema() -> vol.Schema:
    """返回扫码登录轮询/刷新表单 schema."""
    return cloud_scan_login_schema_for_qrcode("")


def cloud_scan_login_schema_for_qrcode(qrcode_content: str) -> vol.Schema:
    """返回带 HA 原生二维码预览的扫码登录表单 schema."""
    return vol.Schema({
        vol.Optional(CONF_SCAN_LOGIN_QRCODE): selector.QrCodeSelector(
            selector.QrCodeSelectorConfig(
                data=qrcode_content,
                scale=5,
                error_correction_level=selector.QrErrorCorrectionLevel.QUARTILE,
            )
        ),
        vol.Optional(CONF_SCAN_LOGIN_REFRESH, default=False): bool,
    })


async def async_scan_login_device_id(hass: HomeAssistant) -> str:
    """派生当前 HA 实例稳定且不暴露原始 instance id 的扫码 device."""
    raw_id = await instance_id.async_get(hass)
    digest = hashlib.sha256(str(raw_id).encode("utf-8")).hexdigest()[:24]
    return f"ha-{digest}"


def scan_login_description_placeholders(
    state: ScanLoginFlowState,
) -> dict[str, str]:
    """返回配置流可展示的扫码状态占位符。"""
    qr_code = state.qr_code
    if qr_code is None:
        return {
            "qrcode": "",
            "qr_code": "",
            "status": "CREATED",
            "remaining_seconds": "300",
            "poll_count": str(state.poll_count),
        }

    remaining = qr_code.expires_in_seconds
    return {
        "qrcode": qr_code.qrcode_content,
        "qr_code": qr_code.qrcode_content,
        "status": qr_code.status,
        "remaining_seconds": str(remaining if remaining is not None else 300),
        "poll_count": str(state.poll_count),
    }


def scan_login_entry_data(
    token: YeelightAccountToken,
    *,
    device: str,
) -> dict[str, Any]:
    """把扫码登录 token 元数据转为 config-entry data。"""
    data: dict[str, Any] = {
        CONF_ACCESS_TOKEN: token.access_token,
        CONF_REFRESH_TOKEN: token.refresh_token,
        CONF_TOKEN_EXPIRES_IN: token.expires_in,
        CONF_TOKEN_TYPE: token.token_type,
        CONF_SCAN_LOGIN_DEVICE: device,
    }
    if token.client_id:
        data[CONF_OPEN_API_CLIENT_ID] = token.client_id
    if token.client_secret:
        data[CONF_OPEN_API_CLIENT_SECRET] = token.client_secret
    if token.user_id is not None:
        data[CONF_ACCOUNT_USER_ID] = token.user_id
    if token.username:
        data[CONF_ACCOUNT_USERNAME] = token.username
    return data


def scan_login_account_key(token: YeelightAccountToken) -> str:
    """返回用于多账号 unique_id 的稳定账号片段。"""
    return account_key_from_identity(account_identity(
        account_user_id=token.user_id,
        username=token.username,
        client_id=token.client_id,
        access_token=token.access_token,
    ))


def scan_login_needs_refresh(qr_code: YeelightScanLoginQrCode | None) -> bool:
    """返回是否需要首次生成二维码。过期二维码必须由用户手动刷新。"""
    return qr_code is None


async def async_poll_scan_login_until_login(
    client: Any,
    *,
    region: str,
    qr_code: YeelightScanLoginQrCode,
    state: ScanLoginFlowState,
    base_url: str | None = None,
    poll_interval_seconds: float = SCAN_LOGIN_POLL_INTERVAL_SECONDS,
    sleep: Any = asyncio.sleep,
) -> YeelightScanLoginQrCode:
    """Poll a QR code until LOGIN is returned or the five-minute code expires."""
    current = qr_code
    while current.pollable:
        await sleep(poll_interval_seconds)
        state.poll_count += 1
        kwargs = {
            "region": region,
            "qr_code_id": current.qr_code_id,
        }
        if base_url is not None:
            kwargs["base_url"] = base_url
        current = await client.check_scan_login_qrcode(
            **kwargs,
        )
        state.qr_code = current
        if current.status == ScanLoginStatus.LOGIN:
            return current
    if current.status == ScanLoginStatus.EXPIRED or current.expires_in_seconds == 0:
        raise TimeoutError("Yeelight scan-login QR code expired")
    return current


def _async_create_task(
    hass: HomeAssistant,
    coro: Coroutine[Any, Any, YeelightScanLoginQrCode],
) -> asyncio.Task[YeelightScanLoginQrCode]:
    """Create a typed Home Assistant task for scan-login polling."""
    return cast(asyncio.Task[YeelightScanLoginQrCode], hass.async_create_task(coro))


__all__ = [
    "SCAN_LOGIN_POLL_INTERVAL_SECONDS",
    "ScanLoginFlowState",
    "_async_create_task",
    "async_poll_scan_login_until_login",
    "async_scan_login_device_id",
    "cloud_scan_login_schema",
    "cloud_scan_login_schema_for_qrcode",
    "scan_login_account_key",
    "scan_login_description_placeholders",
    "scan_login_entry_data",
    "scan_login_needs_refresh",
]
