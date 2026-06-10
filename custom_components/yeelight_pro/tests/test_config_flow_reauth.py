"""Config-flow reauth and error-redaction tests."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.data_entry_flow import FlowResultType

from custom_components.yeelight_pro.config_flow_scan_login import ScanLoginFlowState
from custom_components.yeelight_pro.const import (
    CONF_ACCESS_TOKEN,
    CONF_ACCOUNT_USER_ID,
    CONF_ACCOUNT_USERNAME,
    CONF_CLOUD_DOMAIN,
    CONF_CLOUD_REGION,
    CONF_CONNECTION_MODE,
    CONF_HOUSE_ID,
    CONF_OAUTH_CLIENT_ID,
    CONF_PRIVATE_DOMAIN,
    CONF_REFRESH_TOKEN,
    CONF_SCAN_LOGIN_DEVICE,
    CONF_TOKEN_EXPIRES_IN,
    CONF_TOKEN_TYPE,
    CONNECTION_MODE_CLOUD,
    CONNECTION_MODE_PRIVATE,
)
from custom_components.yeelight_pro.scan_login_contract import parse_scan_login_response

from .config_flow_helpers import prepare_cloud_flow
from .p0_client_helpers import scan_login_created_payload, scan_login_login_payload


@pytest.mark.asyncio
async def test_reauth_normalizes_legacy_private_entry_data(config_flow) -> None:
    """reauth 应兼容旧私有部署 entry 字段别名."""
    result = await config_flow.async_step_reauth({
        CONF_CONNECTION_MODE: CONNECTION_MODE_PRIVATE,
        "server": "10.0.0.10:8080",
        CONF_ACCESS_TOKEN: "old-token",
        "home_id": "1001",
    })

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert config_flow._connection_mode == CONNECTION_MODE_PRIVATE
    assert config_flow._domain == "10.0.0.10:8080"


@pytest.mark.asyncio
async def test_cloud_reauth_routes_to_scan_login_qrcode(config_flow) -> None:
    """云端 reauth 应走易来 APP 扫码登录，而不是回退到手动 token."""
    qr_code = parse_scan_login_response(scan_login_created_payload())
    client = MagicMock()
    client.create_scan_login_qrcode = AsyncMock(return_value=qr_code)
    config_flow.hass = MagicMock()

    with patch.object(config_flow, "_scan_login_client", return_value=client):
        result = await config_flow.async_step_reauth({
            CONF_CONNECTION_MODE: CONNECTION_MODE_CLOUD,
            CONF_CLOUD_DOMAIN: "https://api-us.yeelight.com/apis/iot",
            CONF_CLOUD_REGION: "us",
            CONF_ACCESS_TOKEN: "old-token",
            CONF_HOUSE_ID: 7,
            CONF_ACCOUNT_USER_ID: 122349,
            CONF_SCAN_LOGIN_DEVICE: "ha-device-1",
        })

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "cloud_scan_login"
    assert result["description_placeholders"]["qrcode"] == "qr-1&ha-device-1"
    assert config_flow._reauth_in_progress is True
    client.create_scan_login_qrcode.assert_awaited_once_with(
        region="us",
        device="ha-device-1",
    )


@pytest.mark.asyncio
async def test_cloud_reauth_scan_login_updates_token_metadata(config_flow) -> None:
    """云端 reauth 扫码成功后应更新 token、refresh token 和账号元数据."""
    login = parse_scan_login_response(_scan_login_payload_with_token_region("US"))
    config_flow._connection_mode = CONNECTION_MODE_CLOUD
    config_flow._domain = "https://api-us.yeelight.com/apis/iot"
    config_flow._cloud_region = "us"
    config_flow._reauth_in_progress = True
    config_flow._reauth_entry_data = {
        CONF_CONNECTION_MODE: CONNECTION_MODE_CLOUD,
        CONF_CLOUD_DOMAIN: "https://api-us.yeelight.com/apis/iot",
        CONF_CLOUD_REGION: "us",
        CONF_ACCESS_TOKEN: "old-token",
        CONF_HOUSE_ID: 7,
        CONF_ACCOUNT_USER_ID: 122349,
        CONF_ACCOUNT_USERNAME: "old-name",
        CONF_OAUTH_CLIENT_ID: "old-client",
        CONF_SCAN_LOGIN_DEVICE: "ha-device-1",
    }
    config_flow._scan_login_device = "ha-device-1"
    config_flow._scan_login_poll_task_ref = asyncio.Future()
    config_flow._scan_login_poll_task_ref.set_result(login)
    entry = MagicMock()
    entry.data = dict(config_flow._reauth_entry_data)

    with patch.object(
        config_flow,
        "_get_reauth_entry",
        return_value=entry,
        create=True,
    ), patch.object(
        config_flow,
        "async_update_reload_and_abort",
        return_value={"type": FlowResultType.ABORT},
    ) as update_reload:
        result = await config_flow.async_step_cloud_scan_login_wait()

    assert result["type"] == FlowResultType.ABORT
    new_data = update_reload.call_args.kwargs["data"]
    assert new_data[CONF_ACCESS_TOKEN] == "access-1"
    assert new_data[CONF_REFRESH_TOKEN] == "refresh-2"
    assert new_data[CONF_TOKEN_TYPE] == "bearer"
    assert new_data[CONF_TOKEN_EXPIRES_IN] == 7775999
    assert new_data[CONF_ACCOUNT_USER_ID] == 122349
    assert new_data[CONF_ACCOUNT_USERNAME] == "user-1"
    assert new_data[CONF_OAUTH_CLIENT_ID] == "client-1"
    assert new_data[CONF_SCAN_LOGIN_DEVICE] == "ha-device-1"
    assert config_flow._reauth_in_progress is False


@pytest.mark.asyncio
async def test_cloud_reauth_scan_login_rejects_different_account(config_flow) -> None:
    """云端 reauth 不应允许另一个账号的扫码 token 覆盖当前 entry."""
    login = parse_scan_login_response(scan_login_login_payload())
    config_flow._connection_mode = CONNECTION_MODE_CLOUD
    config_flow._domain = "https://api-us.yeelight.com/apis/iot"
    config_flow._cloud_region = "us"
    config_flow._reauth_in_progress = True
    config_flow._reauth_entry_data = {
        CONF_CONNECTION_MODE: CONNECTION_MODE_CLOUD,
        CONF_CLOUD_DOMAIN: "https://api-us.yeelight.com/apis/iot",
        CONF_CLOUD_REGION: "us",
        CONF_ACCESS_TOKEN: "old-token",
        CONF_HOUSE_ID: 7,
        CONF_ACCOUNT_USER_ID: 999999,
        CONF_SCAN_LOGIN_DEVICE: "ha-device-1",
    }
    config_flow._scan_login_state = ScanLoginFlowState(qr_code=login)
    config_flow._scan_login_device = "ha-device-1"
    config_flow._scan_login_poll_task_ref = asyncio.Future()
    config_flow._scan_login_poll_task_ref.set_result(login)

    with patch.object(
        config_flow,
        "async_update_reload_and_abort",
    ) as update_reload:
        result = await config_flow.async_step_cloud_scan_login_wait()

    assert result["type"] == FlowResultType.SHOW_PROGRESS_DONE
    assert result["step_id"] == "cloud_scan_login"
    assert config_flow._scan_login_state.last_error == "invalid_auth"
    assert config_flow._reauth_in_progress is True
    update_reload.assert_not_called()


@pytest.mark.asyncio
async def test_cloud_reauth_scan_login_rejects_different_region(config_flow) -> None:
    """云端 reauth 不应允许其他区域 token 覆盖当前 entry."""
    login = parse_scan_login_response(_scan_login_payload_with_token_region("CN"))
    config_flow._connection_mode = CONNECTION_MODE_CLOUD
    config_flow._domain = "https://api-us.yeelight.com/apis/iot"
    config_flow._cloud_region = "us"
    config_flow._reauth_in_progress = True
    config_flow._reauth_entry_data = {
        CONF_CONNECTION_MODE: CONNECTION_MODE_CLOUD,
        CONF_CLOUD_DOMAIN: "https://api-us.yeelight.com/apis/iot",
        CONF_CLOUD_REGION: "us",
        CONF_ACCESS_TOKEN: "old-token",
        CONF_HOUSE_ID: 7,
        CONF_ACCOUNT_USER_ID: 122349,
        CONF_SCAN_LOGIN_DEVICE: "ha-device-1",
    }
    config_flow._scan_login_state = ScanLoginFlowState(qr_code=login)
    config_flow._scan_login_device = "ha-device-1"
    config_flow._scan_login_poll_task_ref = asyncio.Future()
    config_flow._scan_login_poll_task_ref.set_result(login)

    with patch.object(
        config_flow,
        "async_update_reload_and_abort",
    ) as update_reload:
        result = await config_flow.async_step_cloud_scan_login_wait()

    assert result["type"] == FlowResultType.SHOW_PROGRESS_DONE
    assert result["step_id"] == "cloud_scan_login"
    assert config_flow._scan_login_state.last_error == "invalid_auth"
    update_reload.assert_not_called()


@pytest.mark.asyncio
@patch("custom_components.yeelight_pro.config_flow_helpers.async_get_clientsession")
@patch("custom_components.yeelight_pro.config_flow_helpers.YeelightProClient")
@pytest.mark.parametrize(
    ("entry_data", "expected_client_id"),
    [
        (
            {
                "server": "10.0.0.10:8080",
                "accessToken": "old-token",
                "home_id": "1001",
            },
            "",
        ),
        (
            {
                "server": "10.0.0.10:8080",
                "accessToken": "old-token",
                "home_id": "1001",
                "clientId": "client-from-entry",
            },
            "client-from-entry",
        ),
    ],
)
async def test_reauth_update_normalizes_entry_data_and_preserves_client_id(
    mock_client_class,
    mock_get_session,
    config_flow,
    entry_data: dict,
    expected_client_id: str,
) -> None:
    """reauth 更新 token 时应归一 data，并沿用 Open API clientId 头字段."""
    mock_client = AsyncMock()
    mock_client.validate_auth.return_value = True
    mock_client_class.return_value = mock_client
    mock_get_session.return_value = MagicMock()
    config_flow.hass = MagicMock()
    config_flow._connection_mode = CONNECTION_MODE_PRIVATE
    config_flow._domain = "10.0.0.10:8080"
    config_flow._reauth_entry_data = {
        CONF_CONNECTION_MODE: CONNECTION_MODE_PRIVATE,
        CONF_PRIVATE_DOMAIN: "10.0.0.10:8080",
        CONF_ACCESS_TOKEN: "old-token",
        CONF_HOUSE_ID: 1001,
        CONF_OAUTH_CLIENT_ID: expected_client_id,
    }
    entry = MagicMock()
    entry.data = entry_data

    with patch.object(
        config_flow,
        "_get_reauth_entry",
        return_value=entry,
        create=True,
    ), patch.object(
        config_flow,
        "async_update_reload_and_abort",
        return_value={"type": FlowResultType.ABORT},
    ) as update_reload:
        result = await config_flow.async_step_reauth_confirm(
            {CONF_ACCESS_TOKEN: "new-token"}
        )

    assert result["type"] == FlowResultType.ABORT
    new_data = update_reload.call_args.kwargs["data"]
    assert new_data[CONF_ACCESS_TOKEN] == "new-token"
    assert new_data[CONF_CONNECTION_MODE] == CONNECTION_MODE_PRIVATE
    assert new_data[CONF_PRIVATE_DOMAIN] == "10.0.0.10:8080"
    assert new_data[CONF_HOUSE_ID] == 1001
    assert new_data[CONF_OAUTH_CLIENT_ID] == expected_client_id
    mock_client_class.assert_called_once()
    assert mock_client_class.call_args.kwargs["client_id"] == expected_client_id


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "stage",
    ["cloud_auth", "cloud_houses", "private_config", "reauth"],
)
@patch("custom_components.yeelight_pro.config_flow_helpers.async_get_clientsession")
@patch("custom_components.yeelight_pro.config_flow_helpers.YeelightProClient")
async def test_config_flow_unknown_errors_log_only_exception_type(
    mock_client_class,
    mock_get_session,
    config_flow,
    caplog,
    stage: str,
) -> None:
    """未知异常日志不能泄露 token、URL、house 或 device 细节."""
    sensitive_error = RuntimeError(
        "token secret-token https://api.yeelight.com house 12345 device 67890"
    )
    mock_client = AsyncMock()
    mock_client.validate_auth.side_effect = sensitive_error
    mock_client.get_houses.side_effect = sensitive_error
    mock_client_class.return_value = mock_client
    mock_get_session.return_value = MagicMock()
    config_flow.hass = MagicMock()

    with caplog.at_level("ERROR"):
        if stage == "cloud_auth":
            config_flow._connection_mode = CONNECTION_MODE_CLOUD
            config_flow._domain = "api.yeelight.com"
            result = await config_flow.async_step_cloud_auth(
                {CONF_ACCESS_TOKEN: "secret-token"}
            )
        elif stage == "cloud_houses":
            prepare_cloud_flow(config_flow)
            result = await config_flow.async_step_cloud_houses()
        elif stage == "private_config":
            config_flow._connection_mode = CONNECTION_MODE_PRIVATE
            result = await config_flow.async_step_private_config(
                {
                    CONF_PRIVATE_DOMAIN: "https://private.example",
                    CONF_ACCESS_TOKEN: "secret-token",
                    CONF_HOUSE_ID: 12345,
                }
            )
        else:
            config_flow._connection_mode = CONNECTION_MODE_CLOUD
            config_flow._domain = "api.yeelight.com"
            result = await config_flow.async_step_reauth_confirm(
                {CONF_ACCESS_TOKEN: "secret-token"}
            )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "unknown"
    assert "RuntimeError" in caplog.text
    assert "secret-token" not in caplog.text
    assert "api.yeelight.com" not in caplog.text
    assert "12345" not in caplog.text
    assert "67890" not in caplog.text


def _scan_login_payload_with_token_region(region: str) -> dict[str, object]:
    """Return a scan-login LOGIN payload with an explicit token region."""
    payload = scan_login_login_payload()
    data = payload["data"]
    assert isinstance(data, dict)
    token = data["token"]
    assert isinstance(token, dict)
    token["region"] = region
    return payload
