"""Config-flow scan-login polling helper tests."""

from __future__ import annotations

from collections.abc import Mapping
import time
from typing import cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.yeelight_pro.config_flow_scan_login import (
    ScanLoginFlowState,
    async_poll_scan_login_until_login,
    scan_login_description_placeholders,
    scan_login_needs_refresh,
)
from custom_components.yeelight_pro.scan_login_contract import (
    ScanLoginStatus,
    parse_scan_login_response,
)

from .p0_client_helpers import (
    scan_login_created_payload,
    scan_login_login_payload,
)


def test_scan_login_description_placeholders_expose_pollable_state() -> None:
    """配置流描述应展示扫码内容、状态、剩余秒数和轮询次数."""
    qr_code = parse_scan_login_response(scan_login_created_payload())
    placeholders = scan_login_description_placeholders(
        ScanLoginFlowState(qr_code=qr_code, poll_count=2)
    )

    assert placeholders == {
        "qrcode": "cli&ha-device-1&qr-1",
        "qr_code": "cli&ha-device-1&qr-1",
        "status": "CREATED",
        "remaining_seconds": "300",
        "poll_count": "2",
    }


def test_scan_login_needs_refresh_keeps_expired_qrcode_for_manual_refresh() -> None:
    """二维码本地倒计时归零后应保留旧二维码，等待用户手动刷新。"""
    expired_payload = scan_login_created_payload()
    expired_data = dict(cast(Mapping[str, object], expired_payload["data"]))
    expired_data["expireAt"] = int(time.time() * 1000) - 1
    expired_payload["data"] = expired_data
    expired = parse_scan_login_response({
        **expired_payload,
        "data": expired_data,
    })

    assert scan_login_needs_refresh(expired) is False


@pytest.mark.asyncio
async def test_scan_login_poll_task_keeps_polling_until_login() -> None:
    """后台轮询应持续检查二维码，直到 APP 授权 LOGIN。"""
    created = parse_scan_login_response(scan_login_created_payload())
    scanned_payload = scan_login_created_payload()
    scanned_data = dict(cast(Mapping[str, object], scanned_payload["data"]))
    scanned_data["status"] = "SCANNED"
    scanned_payload["data"] = scanned_data
    scanned = parse_scan_login_response({
        **scanned_payload,
        "data": scanned_data,
    })
    login = parse_scan_login_response(scan_login_login_payload())
    client = MagicMock()
    client.check_scan_login_qrcode = AsyncMock(side_effect=[scanned, login])
    state = ScanLoginFlowState(qr_code=created)

    result = await async_poll_scan_login_until_login(
        client,
        region="cn",
        qr_code=created,
        state=state,
        poll_interval_seconds=0,
    )

    assert result.status == ScanLoginStatus.LOGIN
    assert state.poll_count == 2
    assert state.qr_code is login
    assert client.check_scan_login_qrcode.await_count == 2


@pytest.mark.asyncio
async def test_scan_login_poll_task_stops_when_local_qrcode_ttl_expires() -> None:
    """本地倒计时到期后应停止轮询，等待用户手动刷新二维码。"""
    expired_payload = scan_login_created_payload()
    expired_data = dict(cast(Mapping[str, object], expired_payload["data"]))
    expired_data["expireAt"] = int(time.time() * 1000) - 1
    expired_payload["data"] = expired_data
    expired = parse_scan_login_response({
        **expired_payload,
        "data": expired_data,
    })
    client = MagicMock()
    client.check_scan_login_qrcode = AsyncMock()
    state = ScanLoginFlowState(qr_code=expired)

    with pytest.raises(TimeoutError):
        await async_poll_scan_login_until_login(
            client,
            region="cn",
            qr_code=expired,
            state=state,
            poll_interval_seconds=0,
        )

    assert state.poll_count == 0
    client.check_scan_login_qrcode.assert_not_awaited()
