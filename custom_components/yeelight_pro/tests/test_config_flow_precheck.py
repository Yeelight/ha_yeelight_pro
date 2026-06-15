"""Config-flow network precheck tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.yeelight_pro.config_flow_precheck import (
    async_precheck_cloud_connection,
    async_precheck_lan_connection,
    async_precheck_private_connection,
    precheck_error_code,
)
from custom_components.yeelight_pro.core.exceptions import (
    AuthenticationError,
    ConnectionError as YeelightConnectionError,
)


@pytest.mark.asyncio
@patch("custom_components.yeelight_pro.config_flow_precheck.async_get_clientsession")
@patch("custom_components.yeelight_pro.config_flow_precheck.YeelightProClient")
async def test_cloud_precheck_success(mock_client_class, mock_get_session) -> None:
    """云端预检成功时返回 ok，不暴露 token。"""
    mock_client = AsyncMock()
    mock_client.validate_auth.return_value = True
    mock_client.get_house_snapshot.return_value = {"code": "200", "data": {}}
    mock_client_class.return_value = mock_client
    mock_get_session.return_value = MagicMock()

    result = await async_precheck_cloud_connection(
        MagicMock(),
        domain="https://api.yeelight.com/apis/iot",
        access_token="secret-token",
        house_id=1,
    )

    assert result.ok is True
    assert result.target == "cloud"
    mock_client.validate_auth.assert_awaited_once()
    mock_client.get_house_snapshot.assert_awaited_once_with(1)


@pytest.mark.asyncio
@patch("custom_components.yeelight_pro.config_flow_precheck.async_get_clientsession")
@patch("custom_components.yeelight_pro.config_flow_precheck.YeelightProClient")
async def test_cloud_precheck_allows_token_only_auth(
    mock_client_class,
    mock_get_session,
) -> None:
    """云端 token 阶段只验证认证和基础 list，不要求已选 house。"""
    mock_client = AsyncMock()
    mock_client.validate_auth.return_value = True
    mock_client_class.return_value = mock_client
    mock_get_session.return_value = MagicMock()

    result = await async_precheck_cloud_connection(
        MagicMock(),
        domain="https://api.yeelight.com/apis/iot",
        access_token="secret-token",
    )

    assert result.ok is True
    mock_client.validate_auth.assert_awaited_once()
    mock_client.get_house_snapshot.assert_not_awaited()


@pytest.mark.asyncio
@patch("custom_components.yeelight_pro.config_flow_precheck.async_get_clientsession")
@patch("custom_components.yeelight_pro.config_flow_precheck.YeelightProClient")
async def test_private_precheck_classifies_auth_failure(
    mock_client_class,
    mock_get_session,
) -> None:
    """私有域预检应把认证错误分类为 invalid_auth。"""
    mock_client = AsyncMock()
    mock_client.validate_auth.side_effect = AuthenticationError(
        "token secret-token https://private.example"
    )
    mock_client_class.return_value = mock_client
    mock_get_session.return_value = MagicMock()

    result = await async_precheck_private_connection(
        MagicMock(),
        domain="https://private.example",
        access_token="secret-token",
    )

    assert result.ok is False
    assert result.target == "private"
    assert result.error_type == "auth"
    assert precheck_error_code(result) == "invalid_auth"
    assert result.error_summary == "AuthenticationError"


@pytest.mark.asyncio
@patch("custom_components.yeelight_pro.config_flow_precheck.async_get_clientsession")
@patch("custom_components.yeelight_pro.config_flow_precheck.YeelightProClient")
async def test_cloud_precheck_classifies_network_failure(
    mock_client_class,
    mock_get_session,
) -> None:
    """云端预检应把连接错误分类为 cannot_connect。"""
    mock_client = AsyncMock()
    mock_client.validate_auth.side_effect = YeelightConnectionError(
        "https://api.yeelight.com token secret-token"
    )
    mock_client_class.return_value = mock_client
    mock_get_session.return_value = MagicMock()

    result = await async_precheck_cloud_connection(
        MagicMock(),
        domain="https://api.yeelight.com/apis/iot",
        access_token="secret-token",
    )

    assert result.ok is False
    assert result.error_type == "network"
    assert precheck_error_code(result) == "cannot_connect"
    assert result.error_summary == "ConnectionError"


@pytest.mark.asyncio
@patch("custom_components.yeelight_pro.config_flow_precheck.async_get_clientsession")
@patch("custom_components.yeelight_pro.config_flow_precheck.YeelightProClient")
async def test_private_precheck_classifies_house_read_network_failure(
    mock_client_class,
    mock_get_session,
) -> None:
    """私有域 house 读端点失败应分类为 network 且不泄露端点。"""
    mock_client = AsyncMock()
    mock_client.validate_auth.return_value = True
    mock_client.get_house_snapshot.side_effect = YeelightConnectionError(
        "https://private.example house 1001 token secret-token"
    )
    mock_client_class.return_value = mock_client
    mock_get_session.return_value = MagicMock()

    result = await async_precheck_private_connection(
        MagicMock(),
        domain="https://private.example",
        access_token="secret-token",
        house_id=1001,
    )

    assert result.ok is False
    assert result.error_type == "network"
    assert precheck_error_code(result) == "cannot_connect"
    assert result.error_summary == "ConnectionError"
    mock_client.validate_auth.assert_awaited_once()
    mock_client.get_house_snapshot.assert_awaited_once_with(1001)


@pytest.mark.asyncio
@patch("custom_components.yeelight_pro.config_flow_precheck.async_get_clientsession")
@patch("custom_components.yeelight_pro.config_flow_precheck.YeelightProClient")
async def test_private_precheck_rejects_invalid_house_without_read(
    mock_client_class,
    mock_get_session,
) -> None:
    """无效 house id 属于配置错误，不应调用 house 读端点。"""
    mock_client = AsyncMock()
    mock_client.validate_auth.return_value = True
    mock_client_class.return_value = mock_client
    mock_get_session.return_value = MagicMock()

    result = await async_precheck_private_connection(
        MagicMock(),
        domain="https://private.example",
        access_token="secret-token",
        house_id=0,
    )

    assert result.ok is False
    assert result.error_type == "invalid_config"
    assert result.error_code == "invalid_house"
    assert precheck_error_code(result) == "cannot_connect"
    mock_client.validate_auth.assert_awaited_once()
    mock_client.get_house_snapshot.assert_not_awaited()


@pytest.mark.asyncio
async def test_lan_precheck_success() -> None:
    """LAN 预检成功时只返回聚合状态。"""
    validator = AsyncMock()

    result = await async_precheck_lan_connection(
        "192.168.1.2",
        65443,
        validator=validator,
    )

    assert result.ok is True
    assert result.target == "lan"
    validator.assert_awaited_once_with("192.168.1.2", 65443)


@pytest.mark.asyncio
async def test_lan_precheck_rejects_invalid_host_without_network() -> None:
    """空 LAN 地址不应尝试网络连接。"""
    validator = AsyncMock()

    result = await async_precheck_lan_connection("", 65443, validator=validator)

    assert result.ok is False
    assert result.error_type == "invalid_config"
    assert result.error_code == "invalid_host"
    assert precheck_error_code(result) == "cannot_connect"
    validator.assert_not_awaited()


@pytest.mark.asyncio
async def test_lan_precheck_classifies_connection_failure() -> None:
    """LAN TCP 失败应映射为 cannot_connect，且错误摘要脱敏。"""
    validator = AsyncMock(
        side_effect=YeelightConnectionError("192.168.1.2:65443 token secret")
    )

    result = await async_precheck_lan_connection(
        "192.168.1.2",
        65443,
        validator=validator,
    )

    assert result.ok is False
    assert result.error_type == "network"
    assert precheck_error_code(result) == "cannot_connect"
    assert result.error_summary == "ConnectionError"
