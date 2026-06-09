"""P0 控制链路、鉴权语义和测试门禁回归测试."""
from __future__ import annotations

import traceback
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

from aiohttp import ClientSession
import pytest

from custom_components.yeelight_pro.core.commands import (
    async_control_device as execute_control_device_command,
)
from custom_components.yeelight_pro.core.client import YeelightProClient
from custom_components.yeelight_pro.core.exceptions import (
    AuthenticationError,
    CommandError,
    TokenExpiredError,
)

from .p0_client_helpers import FakeSession


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "expected_error"),
    [
        pytest.param(401, TokenExpiredError, id="401-token-expired"),
        pytest.param(403, AuthenticationError, id="403-forbidden"),
    ],
)
async def test_client_request_preserves_auth_error_classification(
    status: int,
    expected_error: type[AuthenticationError],
) -> None:
    """HTTP 401/403 必须保留鉴权语义，不能退化为普通连接失败."""
    client = YeelightProClient(
        domain="https://api.yeelight.com/apis/iot",
        access_token="test-token",
        session=cast(ClientSession, FakeSession(status)),
    )

    with pytest.raises(expected_error):
        await client._request("GET", "/v1/house/r/all")


@pytest.mark.asyncio
async def test_client_request_redacts_http_error_response_body() -> None:
    """4xx 响应正文可能含 token/URL/device，不能进入异常字符串."""
    sensitive_body = (
        "token=secret-token "
        "https://api.yeelight.com/apis/iot/v1/open/node/house/12345 "
        "device_id=67890"
    )
    client = YeelightProClient(
        domain="https://api.yeelight.com/apis/iot",
        access_token="test-token",
        session=cast(ClientSession, FakeSession(400, sensitive_body)),
    )

    with pytest.raises(CommandError) as exc_info:
        await client._request("GET", "/v1/private")

    message = str(exc_info.value)
    assert message == "HTTP 400 request failed"
    assert "secret-token" not in message
    assert "api.yeelight.com" not in message
    assert "12345" not in message
    assert "67890" not in message


@pytest.mark.asyncio
async def test_command_wrapper_redacts_identifiers_and_nested_error_details() -> None:
    """命令包装异常不应携带设备 ID、URL、token 或服务端正文."""
    client = AsyncMock(spec=YeelightProClient)
    client.control_device.side_effect = RuntimeError(
        "device 67890 failed at https://api.yeelight.com/apis/iot token=secret"
    )

    with pytest.raises(CommandError) as exc_info:
        await execute_control_device_command(
            client,
            house_id=12345,
            device_id=67890,
            params={"p": True},
            duration=250,
        )

    message = str(exc_info.value)
    assert message == "Failed to control device: RuntimeError"
    assert "67890" not in message
    assert "12345" not in message
    assert "api.yeelight.com" not in message
    assert "secret" not in message


@pytest.mark.asyncio
async def test_command_wrapper_traceback_does_not_keep_sensitive_cause() -> None:
    """脱敏包装后的 traceback 不应保留下游敏感异常链."""
    client = AsyncMock(spec=YeelightProClient)
    client.control_device.side_effect = RuntimeError(
        "device 67890 https://api.yeelight.com token=secret"
    )

    with pytest.raises(CommandError) as exc_info:
        await execute_control_device_command(
            client,
            house_id=12345,
            device_id=67890,
            params={"p": True},
            duration=250,
        )

    assert exc_info.value.__cause__ is None
    formatted = "".join(
        traceback.format_exception(
            type(exc_info.value),
            exc_info.value,
            exc_info.value.__traceback__,
        )
    )
    assert "secret" not in formatted
    assert "api.yeelight.com" not in formatted
    assert "67890" not in formatted
    assert "12345" not in formatted


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "auth_error",
    [
        pytest.param(TokenExpiredError("expired"), id="401-token-expired"),
        pytest.param(AuthenticationError("forbidden"), id="403-forbidden"),
    ],
)
async def test_validate_auth_preserves_authentication_errors(
    auth_error: AuthenticationError,
) -> None:
    """validate_auth 必须原样传播认证异常，供 config_flow 映射 invalid_auth."""
    client = YeelightProClient(
        domain="https://api.yeelight.com/apis/iot",
        access_token="test-token",
        session=MagicMock(),
    )

    with patch.object(client, "get_houses", new_callable=AsyncMock) as mock_get_houses:
        mock_get_houses.side_effect = auth_error
        with pytest.raises(type(auth_error)) as exc_info:
            await client.validate_auth()

    assert exc_info.value is auth_error
    assert client._connected is False
