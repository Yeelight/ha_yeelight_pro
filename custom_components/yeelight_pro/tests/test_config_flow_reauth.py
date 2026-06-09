"""Config-flow reauth and error-redaction tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.data_entry_flow import FlowResultType

from custom_components.yeelight_pro.const import (
    CONF_ACCESS_TOKEN,
    CONF_CONNECTION_MODE,
    CONF_HOUSE_ID,
    CONF_OAUTH_CLIENT_ID,
    CONF_PRIVATE_DOMAIN,
    CONNECTION_MODE_CLOUD,
    CONNECTION_MODE_PRIVATE,
)

from .config_flow_helpers import prepare_cloud_flow


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
