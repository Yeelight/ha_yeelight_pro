"""P0 scan-login runtime contract tests."""

from __future__ import annotations

from typing import cast

from aiohttp import ClientSession
import pytest

from custom_components.yeelight_pro.core.client import YeelightProClient
from custom_components.yeelight_pro.core.exceptions import (
    AuthenticationError,
    CommandError,
)
from custom_components.yeelight_pro.scan_login_contract import (
    ScanLoginStatus,
    account_base_url,
)

from .p0_client_helpers import (
    FakeScanLoginSession,
    scan_login_login_payload,
)


@pytest.mark.asyncio
async def test_client_creates_scan_login_qrcode_with_documented_post() -> None:
    """生成二维码应使用账号 API 区域域名、POST 和 x-www-form-urlencoded 头."""
    session = FakeScanLoginSession()
    client = YeelightProClient(
        domain="https://api.yeelight.com/apis/iot",
        access_token="manual-token",
        session=cast(ClientSession, session),
    )

    state = await client.create_scan_login_qrcode(region="sg", device="ha-device-1")

    assert state.status == ScanLoginStatus.CREATED
    assert state.qrcode_content == "cli&ha-device-1&qr-1"
    assert session.calls == [
        {
            "url": (
                f"{account_base_url('sg')}"
                "/user/scan-login/query/qrcode/ha-device-1"
            ),
            "data": {},
            "headers": {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            "timeout": client.timeout,
        }
    ]


@pytest.mark.asyncio
async def test_client_polls_scan_login_qrcode_and_parses_login_token() -> None:
    """轮询 LOGIN 状态时应解析 access/refresh token 和账号元数据."""
    session = FakeScanLoginSession(payload=scan_login_login_payload())
    client = YeelightProClient(
        domain="https://api.yeelight.com/apis/iot",
        access_token="manual-token",
        session=cast(ClientSession, session),
    )

    state = await client.check_scan_login_qrcode(region="us", qr_code_id="qr-1")

    assert state.status == ScanLoginStatus.LOGIN
    assert state.token is not None
    assert state.token.refresh_token == "refresh-2"
    assert session.calls[0]["url"] == (
        f"{account_base_url('us')}/user/scan-login/check/qrcode/qr-1"
    )


@pytest.mark.asyncio
async def test_client_scan_login_can_use_private_account_url() -> None:
    """私有部署扫码登录应使用用户提供的账号 API URL 前缀。"""
    session = FakeScanLoginSession()
    client = YeelightProClient(
        domain="https://private.example/apis/iot",
        access_token="manual-token",
        session=cast(ClientSession, session),
    )

    await client.create_scan_login_qrcode(
        region="cn",
        device="ha-device-1",
        base_url="https://private.example/apis/account",
    )

    assert session.calls[0]["url"] == (
        "https://private.example/apis/account"
        "/user/scan-login/query/qrcode/ha-device-1"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "payload", "expected_error"),
    [
        pytest.param(
            401,
            {"success": False, "msg": "token=secret-scan-token"},
            AuthenticationError,
            id="http-401",
        ),
        pytest.param(
            400,
            {"success": False, "code": "400", "msg": "qrcode=qr-secret"},
            CommandError,
            id="body-failure",
        ),
    ],
)
async def test_client_scan_login_errors_do_not_leak_payload(
    status: int,
    payload: dict[str, object],
    expected_error: type[Exception],
) -> None:
    """扫码登录失败不能把 APP token、二维码或设备标识写入异常."""
    session = FakeScanLoginSession(status=status, payload=payload)
    client = YeelightProClient(
        domain="https://api.yeelight.com/apis/iot",
        access_token="manual-token",
        session=cast(ClientSession, session),
    )

    with pytest.raises(expected_error) as exc_info:
        await client.create_scan_login_qrcode(region="de", device="secret-device")

    message = str(exc_info.value)
    assert "secret-scan-token" not in message
    assert "qr-secret" not in message
    assert "secret-device" not in message
