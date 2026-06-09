"""Config-flow scan-login path tests.

The file name is kept for release guard compatibility; the user-facing OAuth
authorization-code UI is intentionally replaced by Yeelight APP scan login.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.data_entry_flow import FlowResultType

from custom_components.yeelight_pro.config_flow_scan_login import (
    ScanLoginFlowState,
    async_poll_scan_login_until_login,
    scan_login_description_placeholders,
)
from custom_components.yeelight_pro.const import (
    CONF_CLOUD_AUTH_METHOD,
    CONF_SCAN_LOGIN_QRCODE,
    CONF_SCAN_LOGIN_REFRESH,
    CLOUD_AUTH_METHOD_OAUTH_CODE,
    CLOUD_AUTH_METHOD_SCAN_LOGIN,
    CONNECTION_MODE_CLOUD,
)
from custom_components.yeelight_pro.scan_login_contract import (
    ScanLoginStatus,
    parse_scan_login_response,
)

from .p0_client_helpers import (
    scan_login_created_payload,
    scan_login_login_payload,
)


@pytest.mark.asyncio
async def test_cloud_auth_method_no_longer_routes_to_oauth_app(config_flow) -> None:
    """旧授权码认证方式不再作为云端主 UX 暴露。"""
    config_flow._connection_mode = CONNECTION_MODE_CLOUD
    config_flow._domain = "https://api.yeelight.com/apis/iot"

    result = await config_flow.async_step_cloud_auth_method({
        CONF_CLOUD_AUTH_METHOD: CLOUD_AUTH_METHOD_OAUTH_CODE
    })

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "cloud_auth"
    assert not hasattr(config_flow, "async_step_cloud_oauth_app")


@pytest.mark.asyncio
async def test_cloud_scan_login_initial_step_creates_qrcode(config_flow) -> None:
    """进入扫码登录步骤时应立即生成 qrcodeid&device 内容."""
    qr_code = parse_scan_login_response(scan_login_created_payload())
    client = MagicMock()
    client.create_scan_login_qrcode = AsyncMock(return_value=qr_code)
    config_flow._connection_mode = CONNECTION_MODE_CLOUD
    config_flow._domain = "https://api.yeelight.com/apis/iot"
    config_flow._cloud_region = "cn"
    config_flow.hass = MagicMock()

    with patch(
        "custom_components.yeelight_pro.config_flow_scan_login.async_scan_login_device_id",
        AsyncMock(return_value="ha-device-1"),
    ), patch.object(config_flow, "_scan_login_client", return_value=client):
        result = await config_flow.async_step_cloud_scan_login()

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "cloud_scan_login"
    assert result["description_placeholders"]["qrcode"] == "qr-1&ha-device-1"
    assert result["description_placeholders"]["remaining_seconds"] == "300"
    schema = result["data_schema"].schema
    qr_field = next(key for key in schema if key.schema == CONF_SCAN_LOGIN_QRCODE)
    assert schema[qr_field].selector_type == "qr_code"
    assert schema[qr_field].config["data"] == "qr-1&ha-device-1"
    assert schema[qr_field].config["scale"] == 5
    assert schema[qr_field].config["error_correction_level"] == "quartile"
    client.create_scan_login_qrcode.assert_awaited_once_with(
        region="cn",
        device="ha-device-1",
    )


@pytest.mark.asyncio
async def test_cloud_scan_login_submit_starts_continuous_progress_poll(
    config_flow,
) -> None:
    """提交扫码表单后应进入 HA progress 后台持续轮询。"""
    created = parse_scan_login_response(scan_login_created_payload())
    config_flow._connection_mode = CONNECTION_MODE_CLOUD
    config_flow._domain = "https://api-us.yeelight.com/apis/iot"
    config_flow._cloud_region = "us"
    config_flow._scan_login_device = "ha-device-1"
    config_flow._scan_login_state = ScanLoginFlowState(qr_code=created)
    config_flow.hass = MagicMock()
    config_flow.hass.async_create_task = asyncio.create_task
    config_flow._scan_login_poll_interval_seconds = 0

    with patch.object(
        config_flow,
        "_scan_login_client",
        return_value=MagicMock(),
    ):
        result = await config_flow.async_step_cloud_scan_login({})

    assert result["type"] == FlowResultType.SHOW_PROGRESS
    assert result["step_id"] == "cloud_scan_login_wait"
    assert result["progress_action"] == "cloud_scan_login_wait"
    assert result["progress_task"] is config_flow._scan_login_poll_task_ref
    config_flow._scan_login_poll_task_ref.cancel()


@pytest.mark.asyncio
@patch("custom_components.yeelight_pro.config_flow.async_load_house_choices")
async def test_cloud_scan_login_progress_done_loads_houses(
    load_house_choices,
    config_flow,
) -> None:
    """后台轮询 LOGIN 后应保存 token 元数据并进入家庭选择。"""
    login = parse_scan_login_response(scan_login_login_payload())
    load_house_choices.return_value = {1: "Home"}
    config_flow._connection_mode = CONNECTION_MODE_CLOUD
    config_flow._domain = "https://api-us.yeelight.com/apis/iot"
    config_flow._cloud_region = "us"
    config_flow._scan_login_device = "ha-device-1"
    config_flow._scan_login_poll_task_ref = asyncio.Future()
    config_flow._scan_login_poll_task_ref.set_result(login)
    config_flow.hass = MagicMock()

    progress_result = await config_flow.async_step_cloud_scan_login_wait()

    assert progress_result["type"] == FlowResultType.SHOW_PROGRESS_DONE
    assert progress_result["step_id"] == "cloud_houses"
    assert config_flow._access_token == "access-1"
    assert config_flow._refresh_token == "refresh-2"
    assert config_flow._open_api_client_id == "client-1"
    assert config_flow._account_user_id == 122349
    assert config_flow._scan_login_account_key == "122349"

    houses_result = await config_flow.async_step_cloud_houses()
    assert houses_result["type"] == FlowResultType.FORM
    assert houses_result["step_id"] == "cloud_houses"
    load_house_choices.assert_awaited_once_with(
        config_flow.hass,
        domain="https://api-us.yeelight.com/apis/iot",
        access_token="access-1",
        client_id="client-1",
    )


@pytest.mark.asyncio
async def test_cloud_scan_login_refresh_recreates_qrcode(config_flow) -> None:
    """用户勾选刷新时应重新生成 5 分钟动态二维码."""
    old_qr = parse_scan_login_response(scan_login_created_payload())
    refresh_payload = scan_login_created_payload()
    refresh_data = dict(cast(Mapping[str, object], refresh_payload["data"]))
    refresh_data["qrCodeId"] = "qr-2"
    refresh_payload["data"] = refresh_data
    new_qr = parse_scan_login_response({
        **refresh_payload,
        "data": refresh_data,
    })
    client = MagicMock()
    client.create_scan_login_qrcode = AsyncMock(return_value=new_qr)
    config_flow._connection_mode = CONNECTION_MODE_CLOUD
    config_flow._domain = "https://api.yeelight.com/apis/iot"
    config_flow._cloud_region = "cn"
    config_flow._scan_login_device = "ha-device-1"
    config_flow._scan_login_state = ScanLoginFlowState(qr_code=old_qr)
    config_flow.hass = MagicMock()

    with patch.object(config_flow, "_scan_login_client", return_value=client):
        result = await config_flow.async_step_cloud_scan_login({
            CONF_SCAN_LOGIN_REFRESH: True
        })

    assert result["type"] == FlowResultType.FORM
    assert result["description_placeholders"]["qrcode"] == "qr-2&ha-device-1"
    schema = result["data_schema"].schema
    qr_field = next(key for key in schema if key.schema == CONF_SCAN_LOGIN_QRCODE)
    assert schema[qr_field].config["data"] == "qr-2&ha-device-1"
    client.create_scan_login_qrcode.assert_awaited_once_with(
        region="cn",
        device="ha-device-1",
    )


def test_scan_login_description_placeholders_expose_pollable_state() -> None:
    """配置流描述应展示扫码内容、状态、剩余秒数和轮询次数."""
    qr_code = parse_scan_login_response(scan_login_created_payload())
    placeholders = scan_login_description_placeholders(
        ScanLoginFlowState(qr_code=qr_code, poll_count=2)
    )

    assert placeholders == {
        "qrcode": "qr-1&ha-device-1",
        "qr_code": "qr-1&ha-device-1",
        "status": "CREATED",
        "remaining_seconds": "300",
        "poll_count": "2",
    }


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


def test_scan_login_auth_method_constant_is_the_primary_cloud_choice() -> None:
    """release guard token: scan-login is the primary cloud auth choice."""
    assert CLOUD_AUTH_METHOD_SCAN_LOGIN == "scan_login"
