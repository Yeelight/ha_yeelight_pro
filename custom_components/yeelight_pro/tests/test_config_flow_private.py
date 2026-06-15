"""Private-domain config-flow network precheck tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.data_entry_flow import FlowResultType

from custom_components.yeelight_pro.const import (
    CONF_ACCESS_TOKEN,
    CONF_HOUSE_ID,
    CONF_PRIVATE_DOMAIN,
    CONNECTION_MODE_PRIVATE,
)
from custom_components.yeelight_pro.core.exceptions import (
    ConnectionError as YeelightConnectionError,
)


@pytest.mark.asyncio
async def test_private_config_runs_house_precheck_before_create_entry(
    config_flow,
) -> None:
    """私有域配置必须验证 token 和当前 house 的 Open API 读端点。"""
    config_flow._connection_mode = CONNECTION_MODE_PRIVATE

    with patch(
        "custom_components.yeelight_pro.config_flow.async_validate_private_auth",
        AsyncMock(),
    ) as validate_auth, patch.object(
        config_flow,
        "_create_entry",
        AsyncMock(return_value={"type": FlowResultType.CREATE_ENTRY}),
    ) as create_entry:
        result = await config_flow.async_step_private_config({
            CONF_PRIVATE_DOMAIN: "https://private.example",
            CONF_ACCESS_TOKEN: "private-token",
            CONF_HOUSE_ID: 1001,
        })

    assert result["type"] == FlowResultType.CREATE_ENTRY
    validate_auth.assert_awaited_once_with(
        config_flow.hass,
        domain="https://private.example",
        access_token="private-token",
        house_id=1001,
    )
    create_entry.assert_awaited_once()


@pytest.mark.asyncio
async def test_private_config_network_failure_stays_on_form(config_flow) -> None:
    """私有域预检网络失败应映射 cannot_connect，且不创建 entry。"""
    config_flow._connection_mode = CONNECTION_MODE_PRIVATE

    with patch(
        "custom_components.yeelight_pro.config_flow.async_validate_private_auth",
        AsyncMock(side_effect=YeelightConnectionError("private-token endpoint")),
    ) as validate_auth, patch.object(
        config_flow,
        "_create_entry",
        AsyncMock(),
    ) as create_entry:
        result = await config_flow.async_step_private_config({
            CONF_PRIVATE_DOMAIN: "https://private.example",
            CONF_ACCESS_TOKEN: "private-token",
            CONF_HOUSE_ID: 1001,
        })

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "private_config"
    assert result["errors"]["base"] == "cannot_connect"
    validate_auth.assert_awaited_once()
    create_entry.assert_not_awaited()
