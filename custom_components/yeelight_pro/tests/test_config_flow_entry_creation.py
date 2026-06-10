"""Config-flow entry creation and cloud account identity tests."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.data_entry_flow import FlowResultType

from custom_components.yeelight_pro.config_flow_account import (
    redacted_token_fingerprint,
)
from custom_components.yeelight_pro.config_flow_scan_login_helpers import (
    scan_login_account_key,
)
from custom_components.yeelight_pro.const import (
    CONF_CLOUD_REGION,
    CONF_DEVICE_IMPORT_FILTER,
    CONF_OPEN_API_CLIENT_ID,
    CONF_PRIVATE_DOMAIN,
    CONF_REFRESH_TOKEN,
    CONF_SCAN_LOGIN_DEVICE,
    CONF_TOKEN_TYPE,
    CONNECTION_MODE_CLOUD,
    CONNECTION_MODE_PRIVATE,
)
from custom_components.yeelight_pro.entry_title import config_entry_title
from custom_components.yeelight_pro.scan_login_contract import parse_scan_login_response

from .p0_client_helpers import scan_login_login_payload


@pytest.mark.asyncio
async def test_create_entry_persists_open_api_client_id(config_flow) -> None:
    """创建 entry 时应保留 Open API clientId 头所需字段."""
    config_flow._connection_mode = CONNECTION_MODE_CLOUD
    config_flow._domain = "https://api.yeelight.com/apis/iot"
    config_flow._cloud_region = "cn"
    config_flow._access_token = "scan-access-token"
    config_flow._house_id = 1
    config_flow._open_api_client_id = "client-from-token"
    config_flow._scan_login_account_key = "client-from-token"

    with patch.object(
        config_flow,
        "async_set_unique_id",
        AsyncMock(),
    ) as set_unique_id, patch.object(
        config_flow,
        "_abort_if_unique_id_configured",
    ):
        result = await config_flow._create_entry()

    set_unique_id.assert_awaited_once_with("cloud:cn:client-from-token:1")
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Yeelight Pro Cloud (CN · House 1)"
    assert result["data"][CONF_OPEN_API_CLIENT_ID] == "client-from-token"
    assert result["options"][CONF_DEVICE_IMPORT_FILTER] == {
        "enabled": False,
        "mode": "or",
        "include": {},
        "exclude": {},
    }


@pytest.mark.asyncio
async def test_create_entry_manual_token_unique_id_uses_redacted_token_fingerprint(
    config_flow,
) -> None:
    """手动 token 多账号兜底不应共享 unknown，也不能泄露 token 原文."""
    config_flow._connection_mode = CONNECTION_MODE_CLOUD
    config_flow._domain = "https://api.yeelight.com/apis/iot"
    config_flow._cloud_region = "cn"
    config_flow._access_token = "manual-access-token-account-a"
    config_flow._house_id = 1
    config_flow._scan_login_account_key = "unknown"

    with patch.object(
        config_flow,
        "async_set_unique_id",
        AsyncMock(),
    ) as set_unique_id, patch.object(
        config_flow,
        "_abort_if_unique_id_configured",
    ):
        result = await config_flow._create_entry()

    set_unique_id.assert_awaited_once()
    unique_id = set_unique_id.call_args.args[0]
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Yeelight Pro Cloud (CN · House 1)"
    assert unique_id.startswith("cloud:cn:token-")
    assert unique_id.endswith(":1")
    assert "manual-access-token-account-a" not in unique_id


@pytest.mark.asyncio
async def test_create_entry_manual_token_unique_id_separates_accounts(
    config_flow,
) -> None:
    """同区域同家庭的不同手动 token 应能作为不同账号 entry 共存."""
    config_flow._connection_mode = CONNECTION_MODE_CLOUD
    config_flow._cloud_region = "cn"
    config_flow._house_id = 1
    config_flow._scan_login_account_key = "unknown"
    config_flow._access_token = "manual-access-token-account-a"
    first = config_flow._cloud_account_key()

    config_flow._access_token = "manual-access-token-account-b"
    second = config_flow._cloud_account_key()

    assert first.startswith("token-")
    assert second.startswith("token-")
    assert first != second


def test_scan_login_account_key_uses_redacted_token_fingerprint_without_metadata() -> None:
    """扫码 token 缺少账号元数据时也必须隔离多账号，且不泄露 token."""
    payload = scan_login_login_payload()
    token_payload = payload["data"]["token"]  # type: ignore[index]
    assert isinstance(token_payload, dict)
    token_payload.pop("id")
    token_payload.pop("clientId")
    token_payload.pop("username")
    token_payload["accessToken"] = "scan-access-token-without-metadata"
    login = parse_scan_login_response(payload)
    assert login.token is not None

    account_key = scan_login_account_key(login.token)

    assert account_key == redacted_token_fingerprint(
        "scan-access-token-without-metadata"
    )
    assert account_key.startswith("token-")
    assert "scan-access-token-without-metadata" not in account_key


def test_scan_login_account_key_ignores_blank_user_id_alias() -> None:
    """空白账号 id 不能成为共享 unique_id，必须退回脱敏 token 指纹。"""
    payload = scan_login_login_payload()
    token_payload = payload["data"]["token"]  # type: ignore[index]
    assert isinstance(token_payload, dict)
    token_payload["id"] = " "
    token_payload.pop("clientId")
    token_payload.pop("username")
    token_payload["accessToken"] = "scan-access-token-blank-user-id"
    login = parse_scan_login_response(payload)
    assert login.token is not None

    account_key = scan_login_account_key(login.token)

    assert account_key == redacted_token_fingerprint(
        "scan-access-token-blank-user-id"
    )
    assert account_key.startswith("token-")
    assert "scan-access-token-blank-user-id" not in account_key


@pytest.mark.asyncio
async def test_create_entry_persists_scan_login_token_metadata(config_flow) -> None:
    """扫码登录创建 entry 应保存 refresh token、账号和 device 元数据."""
    config_flow._connection_mode = CONNECTION_MODE_CLOUD
    config_flow._domain = "https://api-sg.yeelight.com/apis/iot"
    config_flow._cloud_region = "sg"
    config_flow._house_id = 7
    config_flow._access_token = "scan-access"
    config_flow._refresh_token = "scan-refresh"
    config_flow._token_type = "bearer"
    config_flow._token_expires_in = 777
    config_flow._open_api_client_id = "client-from-scan"
    config_flow._account_user_id = 122349
    config_flow._account_username = "user-1"
    config_flow._scan_login_device = "ha-device"
    config_flow._scan_login_account_key = "122349"

    with patch.object(
        config_flow,
        "async_set_unique_id",
        AsyncMock(),
    ) as set_unique_id, patch.object(
        config_flow,
        "_abort_if_unique_id_configured",
    ):
        result = await config_flow._create_entry()

    set_unique_id.assert_awaited_once_with("cloud:sg:122349:7")
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_CLOUD_REGION] == "sg"
    assert result["data"][CONF_REFRESH_TOKEN] == "scan-refresh"
    assert result["data"][CONF_TOKEN_TYPE] == "bearer"
    assert result["data"][CONF_SCAN_LOGIN_DEVICE] == "ha-device"
    assert result["title"] == "Yeelight Pro Cloud (user-1 · SG · House 7)"


@pytest.mark.asyncio
async def test_create_entry_private_title_includes_endpoint_and_house(
    config_flow,
) -> None:
    """私有部署 entry 标题应可在 HA 集成详情页区分服务器和家庭."""
    config_flow._connection_mode = CONNECTION_MODE_PRIVATE
    config_flow._domain = "10.0.0.10:8080"
    config_flow._access_token = "private-token"
    config_flow._house_id = 1001

    with patch.object(
        config_flow,
        "async_set_unique_id",
        AsyncMock(),
    ), patch.object(
        config_flow,
        "_abort_if_unique_id_configured",
    ):
        result = await config_flow._create_entry()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Yeelight Pro Private (10.0.0.10:8080 · House 1001)"
    assert result["data"][CONF_PRIVATE_DOMAIN] == "10.0.0.10:8080"


def test_config_entry_title_does_not_expose_token_fingerprint() -> None:
    """手动 token 标题不能把 token 指纹当作用户可见账号名."""
    title = config_entry_title({
        "connection_mode": "cloud",
        "cloud_region": "de",
        "house_id": 8,
        "access_token": "secret-access-token",
    })

    assert title == "Yeelight Pro Cloud (EU · House 8)"
    assert "secret-access-token" not in title
    assert "token-" not in title
