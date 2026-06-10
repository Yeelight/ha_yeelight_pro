"""Config-flow reauth account identity fallback tests."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from homeassistant.data_entry_flow import FlowResultType

from custom_components.yeelight_pro.config_flow_account import (
    redacted_token_fingerprint,
)
from custom_components.yeelight_pro.config_flow_scan_login import ScanLoginFlowState
from custom_components.yeelight_pro.const import (
    CONF_ACCESS_TOKEN,
    CONF_CLOUD_DOMAIN,
    CONF_CLOUD_REGION,
    CONF_CONNECTION_MODE,
    CONF_HOUSE_ID,
    CONF_SCAN_LOGIN_DEVICE,
    CONNECTION_MODE_CLOUD,
)
from custom_components.yeelight_pro.scan_login_contract import (
    parse_scan_login_response,
)

from .p0_client_helpers import scan_login_login_payload


@pytest.mark.asyncio
async def test_cloud_reauth_rejects_different_token_without_account_metadata(
    config_flow,
) -> None:
    """账号元数据缺失时，reauth 不允许不同 token 覆盖当前 entry."""
    login = _scan_login_without_account_metadata("new-access-token")
    _prepare_scan_login_reauth(config_flow, login, old_access_token="old-access-token")

    with patch.object(config_flow, "async_update_reload_and_abort") as update_reload:
        result = await config_flow.async_step_cloud_scan_login_wait()

    assert result["type"] == FlowResultType.SHOW_PROGRESS_DONE
    assert result["step_id"] == "cloud_scan_login"
    assert config_flow._scan_login_state.last_error == "invalid_auth"
    assert config_flow._reauth_in_progress is True
    update_reload.assert_not_called()


@pytest.mark.asyncio
async def test_cloud_reauth_ignores_blank_stored_user_id_for_identity(
    config_flow,
) -> None:
    """旧 entry 的空白 user id 不能让不同账号 token 误通过 reauth。"""
    login = _scan_login_without_account_metadata("new-access-token")
    _prepare_scan_login_reauth(config_flow, login, old_access_token="old-access-token")
    config_flow._reauth_entry_data["account_user_id"] = " "

    with patch.object(config_flow, "async_update_reload_and_abort") as update_reload:
        result = await config_flow.async_step_cloud_scan_login_wait()

    assert result["type"] == FlowResultType.SHOW_PROGRESS_DONE
    assert result["step_id"] == "cloud_scan_login"
    assert config_flow._scan_login_state.last_error == "invalid_auth"
    update_reload.assert_not_called()


@pytest.mark.asyncio
async def test_cloud_reauth_accepts_matching_token_fingerprint_without_metadata(
    config_flow,
) -> None:
    """账号元数据缺失时，相同 token 指纹可以完成当前 entry 的 reauth."""
    login = _scan_login_without_account_metadata("same-access-token")
    _prepare_scan_login_reauth(
        config_flow,
        login,
        old_access_token="same-access-token",
    )
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
    assert new_data[CONF_ACCESS_TOKEN] == "same-access-token"
    assert config_flow._scan_login_account_key == redacted_token_fingerprint(
        "same-access-token"
    )
    assert config_flow._reauth_in_progress is False


def _prepare_scan_login_reauth(
    config_flow,
    login,
    *,
    old_access_token: str,
) -> None:
    """Prepare a cloud reauth flow using a completed scan-login future."""
    config_flow._connection_mode = CONNECTION_MODE_CLOUD
    config_flow._domain = "https://api-us.yeelight.com/apis/iot"
    config_flow._cloud_region = "us"
    config_flow._reauth_in_progress = True
    config_flow._reauth_entry_data = {
        CONF_CONNECTION_MODE: CONNECTION_MODE_CLOUD,
        CONF_CLOUD_DOMAIN: "https://api-us.yeelight.com/apis/iot",
        CONF_CLOUD_REGION: "us",
        CONF_ACCESS_TOKEN: old_access_token,
        CONF_HOUSE_ID: 7,
        CONF_SCAN_LOGIN_DEVICE: "ha-device-1",
    }
    config_flow._scan_login_state = ScanLoginFlowState(qr_code=login)
    config_flow._scan_login_device = "ha-device-1"
    config_flow._scan_login_poll_task_ref = asyncio.Future()
    config_flow._scan_login_poll_task_ref.set_result(login)


def _scan_login_without_account_metadata(access_token: str):
    """Return a LOGIN response whose token has no strong account metadata."""
    payload = scan_login_login_payload()
    token_payload = payload["data"]["token"]  # type: ignore[index]
    assert isinstance(token_payload, dict)
    token_payload["accessToken"] = access_token
    token_payload["region"] = "US"
    token_payload.pop("id")
    token_payload.pop("clientId")
    token_payload.pop("username")
    return parse_scan_login_response(payload)
