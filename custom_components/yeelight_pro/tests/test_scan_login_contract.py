"""Yeelight scan-login no-network contract tests."""

from __future__ import annotations

import time

import pytest

from custom_components.yeelight_pro.core.exceptions import CommandError, ProtocolError
from custom_components.yeelight_pro.scan_login_contract import (
    SCAN_LOGIN_QRCODE_TTL_MS,
    ScanLoginStatus,
    account_base_url,
    build_scan_login_qrcode_content,
    build_scan_login_qrcode_path,
    build_scan_login_status_path,
    parse_scan_login_response,
)

from .p0_client_helpers import scan_login_created_payload, scan_login_login_payload


@pytest.mark.parametrize(
    ("region", "expected_url"),
    [
        ("cn", "https://api.yeelight.com/apis/account"),
        ("sg", "https://api-sg.yeelight.com/apis/account"),
        ("us", "https://api-us.yeelight.com/apis/account"),
        ("de", "https://api-de.yeelight.com/apis/account"),
    ],
)
def test_account_base_url_matches_documented_regions(
    region: str,
    expected_url: str,
) -> None:
    """账号扫码登录必须使用区域化账号 API 前缀."""
    assert account_base_url(region) == expected_url


def test_scan_login_paths_and_qrcode_content_match_openapi_contract() -> None:
    """二维码路径和内容应匹配本地 OpenAPI 文档."""
    assert (
        build_scan_login_qrcode_path("AA:BB:CC:DD:EE:FF")
        == "/user/scan-login/query/qrcode/AA%3ABB%3ACC%3ADD%3AEE%3AFF"
    )
    assert (
        build_scan_login_status_path("qr-1")
        == "/user/scan-login/check/qrcode/qr-1"
    )
    assert (
        build_scan_login_qrcode_content("qr-1", "AA:BB:CC:DD:EE:FF")
        == "qr-1&AA:BB:CC:DD:EE:FF"
    )


def test_parse_scan_login_created_response_returns_pollable_qrcode() -> None:
    """CREATED 响应应携带 5 分钟 TTL 和可展示二维码内容."""
    state = parse_scan_login_response(scan_login_created_payload())

    assert state.qr_code_id == "qr-1"
    assert state.device == "ha-device-1"
    assert state.status == ScanLoginStatus.CREATED
    assert state.pollable is True
    assert state.expire_in_ms == SCAN_LOGIN_QRCODE_TTL_MS
    assert state.expires_in_seconds == 300
    assert state.qrcode_content == "qr-1&ha-device-1"
    assert state.token is None


def test_parse_scan_login_created_response_accepts_snake_case_aliases() -> None:
    """二维码响应字段可能按 snake_case 返回，解析器仍应保持同一合同。"""
    now_ms = int(time.time() * 1000)

    state = parse_scan_login_response({
        "success": True,
        "data": {
            "qr_code_id": "qr-2",
            "device": "ha-device-2",
            "create_at": now_ms,
            "expire_in": SCAN_LOGIN_QRCODE_TTL_MS,
            "expire_at": now_ms + SCAN_LOGIN_QRCODE_TTL_MS,
            "status": "CREATED",
        },
    })

    assert state.qr_code_id == "qr-2"
    assert state.device == "ha-device-2"
    assert state.qrcode_content == "qr-2&ha-device-2"
    assert state.expire_in_ms == SCAN_LOGIN_QRCODE_TTL_MS
    assert state.expire_at_ms == now_ms + SCAN_LOGIN_QRCODE_TTL_MS


def test_parse_scan_login_response_derives_expire_at_for_countdown() -> None:
    """缺少 expireAt 时应由 createAt + expireIn 推导绝对过期时间."""
    payload = scan_login_created_payload()
    data = payload["data"]
    assert isinstance(data, dict)
    data.pop("expireAt")

    state = parse_scan_login_response(payload)

    assert state.create_at_ms is not None
    assert state.expire_in_ms == SCAN_LOGIN_QRCODE_TTL_MS
    assert state.expire_at_ms == state.create_at_ms + SCAN_LOGIN_QRCODE_TTL_MS


def test_expired_scan_login_qrcode_is_not_pollable() -> None:
    """绝对过期时间到达后，本地不应继续轮询二维码。"""
    payload = scan_login_created_payload()
    data = payload["data"]
    assert isinstance(data, dict)
    data["expireAt"] = int(time.time() * 1000) - 1

    state = parse_scan_login_response(payload)

    assert state.expires_in_seconds == 0
    assert state.pollable is False


def test_parse_scan_login_login_response_returns_token_model() -> None:
    """LOGIN 响应中的 token 应复用 OAuth token 模型并保留账号元数据."""
    state = parse_scan_login_response(scan_login_login_payload())

    assert state.status == ScanLoginStatus.LOGIN
    assert state.pollable is False
    assert state.token is not None
    assert state.token.access_token == "access-1"
    assert state.token.refresh_token == "refresh-2"
    assert state.token.expires_in == 7775999
    assert state.token.user_id == 122349
    assert state.token.region == "CN"
    assert state.token.client_id == "client-1"
    assert state.token.username == "user-1"


def test_parse_scan_login_login_response_accepts_token_field_aliases() -> None:
    """LOGIN token 字段别名不能破坏多账号隔离元数据保存。"""
    now_ms = int(time.time() * 1000)

    state = parse_scan_login_response({
        "success": True,
        "data": {
            "qrcodeid": "qr-3",
            "device": "ha-device-3",
            "create_at": now_ms,
            "expire_in": SCAN_LOGIN_QRCODE_TTL_MS,
            "status": "LOGIN",
            "token": {
                "access_token": "access-3",
                "token_type": "bearer",
                "refresh_token": "refresh-3",
                "expires_in": 3600,
                "user_id": 445566,
                "region": "US",
                "device": "ha-device-3",
                "client_id": "client-3",
                "username": "user-3",
            },
        },
    })

    assert state.status == ScanLoginStatus.LOGIN
    assert state.qr_code_id == "qr-3"
    assert state.token is not None
    assert state.token.access_token == "access-3"
    assert state.token.refresh_token == "refresh-3"
    assert state.token.user_id == 445566
    assert state.token.region == "US"
    assert state.token.client_id == "client-3"
    assert state.token.username == "user-3"


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"success": True, "data": {"qrCodeId": "qr-secret"}}, id="missing"),
        pytest.param(
            {
                "success": True,
                "data": {
                    "qrCodeId": "qr-secret",
                    "device": "secret-device",
                    "expireIn": 300_000,
                    "status": "LOGIN",
                    "token": None,
                },
            },
            id="login-without-token",
        ),
    ],
)
def test_parse_scan_login_response_rejects_invalid_payload_without_secret_leaks(
    payload: dict[str, object],
) -> None:
    """扫码响应非法时不能把二维码或设备标识带进异常字符串."""
    with pytest.raises(ProtocolError) as exc_info:
        parse_scan_login_response(payload)

    message = str(exc_info.value)
    assert "qr-secret" not in message
    assert "secret-device" not in message


def test_parse_scan_login_failure_envelope_does_not_leak_token() -> None:
    """业务失败体应分类，但不能泄露 APP token 或二维码标识."""
    with pytest.raises(CommandError) as exc_info:
        parse_scan_login_response({
            "success": False,
            "code": "400",
            "msg": "token=secret-scan-token qrcode=qr-secret",
            "data": {},
        })

    message = str(exc_info.value)
    assert "secret-scan-token" not in message
    assert "qr-secret" not in message
