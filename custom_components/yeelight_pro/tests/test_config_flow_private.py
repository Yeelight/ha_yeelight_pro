"""Private-domain config-flow tests."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import voluptuous_serialize

from homeassistant.data_entry_flow import FlowResultType

from custom_components.yeelight_pro.const import (
    CONF_ACCESS_TOKEN,
    CONF_CLOUD_AUTH_METHOD,
    CONF_HOUSE_ID,
    CONF_PRIVATE_DOMAIN,
    CONF_PRIVATE_PUSH_DOMAIN,
    CONF_PRIVATE_PUSH_PROXY,
    CONNECTION_MODE_PRIVATE,
)
from custom_components.yeelight_pro.core.exceptions import (
    ConnectionError as YeelightConnectionError,
)
from custom_components.yeelight_pro.scan_login_contract import parse_scan_login_response

from .p0_client_helpers import scan_login_login_payload


def test_private_config_schema_is_frontend_serializable() -> None:
    """私有部署 URL 表单必须能被 HA 前端序列化。"""
    schema = __import__(
        "custom_components.yeelight_pro.config_flow_helpers",
        fromlist=["private_config_schema"],
    ).private_config_schema()

    fields = voluptuous_serialize.convert(schema)

    assert fields == [
        {
            "name": CONF_PRIVATE_DOMAIN,
            "required": True,
            "type": "string",
            "default": "",
        },
        {
            "name": CONF_PRIVATE_PUSH_DOMAIN,
            "optional": True,
            "type": "string",
            "default": "",
        },
        {
            "name": CONF_PRIVATE_PUSH_PROXY,
            "optional": True,
            "type": "string",
            "default": "",
        },
    ]


def test_private_config_schema_only_requests_private_url(config_flow) -> None:
    """私有部署首屏填写 API URL、WebSocket URL 和可选代理。"""
    result = config_flow.async_show_form(
        step_id="private_config",
        data_schema=__import__(
            "custom_components.yeelight_pro.config_flow_helpers",
            fromlist=["private_config_schema"],
        ).private_config_schema(),
    )

    schema_keys = {key.schema for key in result["data_schema"].schema}
    assert schema_keys == {
        CONF_PRIVATE_DOMAIN,
        CONF_PRIVATE_PUSH_DOMAIN,
        CONF_PRIVATE_PUSH_PROXY,
    }
    assert CONF_ACCESS_TOKEN not in schema_keys
    assert CONF_HOUSE_ID not in schema_keys


@pytest.mark.asyncio
async def test_private_config_rejects_blank_url(config_flow) -> None:
    """私有部署 URL 为空时停留在 URL 页面，不进入认证流程。"""
    config_flow._connection_mode = CONNECTION_MODE_PRIVATE

    result = await config_flow.async_step_private_config({
        CONF_PRIVATE_DOMAIN: "   ",
    })

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "private_config"
    assert result["errors"][CONF_PRIVATE_DOMAIN] == "required"
    assert config_flow._domain is None


@pytest.mark.asyncio
async def test_private_config_routes_to_same_auth_method_flow(config_flow) -> None:
    """私有部署 URL 提交后应进入与云端一致的认证方式选择。"""
    config_flow._connection_mode = CONNECTION_MODE_PRIVATE

    result = await config_flow.async_step_private_config({
        CONF_PRIVATE_DOMAIN: " https://private.example ",
    })

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "cloud_auth_method"
    assert config_flow._domain == "https://private.example"
    assert config_flow._private_push_domain == ""
    assert config_flow._private_push_proxy == ""
    schema_keys = {key.schema for key in result["data_schema"].schema}
    assert schema_keys == {CONF_CLOUD_AUTH_METHOD}


@pytest.mark.asyncio
async def test_private_config_accepts_separate_push_domain(config_flow) -> None:
    """私有部署 API 与 WebSocket 域名可独立填写并规范化保存."""
    config_flow._connection_mode = CONNECTION_MODE_PRIVATE

    result = await config_flow.async_step_private_config({
        CONF_PRIVATE_DOMAIN: "api-dev.yeedev.com",
        CONF_PRIVATE_PUSH_DOMAIN: "ws-dev.yeedev.com",
    })

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "cloud_auth_method"
    assert config_flow._domain == "https://api-dev.yeedev.com"
    assert config_flow._private_push_domain == "wss://ws-dev.yeedev.com/ws"


@pytest.mark.asyncio
async def test_private_config_accepts_push_proxy(config_flow) -> None:
    """私有部署 WebSocket 代理可独立填写，且不影响 API 根 URL。"""
    config_flow._connection_mode = CONNECTION_MODE_PRIVATE

    result = await config_flow.async_step_private_config({
        CONF_PRIVATE_DOMAIN: "api-dev.yeedev.com",
        CONF_PRIVATE_PUSH_DOMAIN: "ws-dev.yeedev.com",
        CONF_PRIVATE_PUSH_PROXY: " http://host.docker.internal:7890 ",
    })

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "cloud_auth_method"
    assert config_flow._domain == "https://api-dev.yeedev.com"
    assert config_flow._private_push_domain == "wss://ws-dev.yeedev.com/ws"
    assert config_flow._private_push_proxy == "http://host.docker.internal:7890"


@pytest.mark.asyncio
async def test_private_config_accepts_legacy_iot_api_prefix(config_flow) -> None:
    """旧版私有 Open API 前缀输入应兼容并规范化为部署根 URL。"""
    config_flow._connection_mode = CONNECTION_MODE_PRIVATE

    result = await config_flow.async_step_private_config({
        CONF_PRIVATE_DOMAIN: " https://private.example/apis/iot/ ",
    })

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "cloud_auth_method"
    assert config_flow._domain == "https://private.example"


@pytest.mark.asyncio
async def test_private_manual_token_reuses_cloud_auth_and_house_flow(
    config_flow,
) -> None:
    """私有部署 Access Token 路径应复用云端认证页并用私有 URL 校验。"""
    config_flow._connection_mode = CONNECTION_MODE_PRIVATE
    config_flow._domain = "https://private.example"

    with patch(
        "custom_components.yeelight_pro.config_flow.async_validate_private_auth",
        AsyncMock(),
    ) as validate_auth, patch.object(
        config_flow,
        "async_step_cloud_houses",
        AsyncMock(return_value={"type": FlowResultType.FORM, "step_id": "cloud_houses"}),
    ) as houses_step:
        result = await config_flow.async_step_cloud_auth({
            CONF_ACCESS_TOKEN: "private-token",
        })

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "cloud_houses"
    validate_auth.assert_awaited_once_with(
        config_flow.hass,
        domain="https://private.example",
        access_token="private-token",
        client_id="",
        house_id=None,
    )
    houses_step.assert_awaited_once()


@pytest.mark.asyncio
async def test_private_house_selection_uses_private_precheck_and_device_picker(
    config_flow,
) -> None:
    """私有部署家庭选择应和云端一样进入设备选择，但校验私有 URL。"""
    config_flow._connection_mode = CONNECTION_MODE_PRIVATE
    config_flow._domain = "https://private.example"
    config_flow._access_token = "private-token"
    config_flow._house_choices = {1001: "Office"}

    with patch(
        "custom_components.yeelight_pro.config_flow.async_validate_private_auth",
        AsyncMock(),
    ) as validate_auth, patch.object(
        config_flow,
        "async_step_cloud_devices",
        AsyncMock(return_value={"type": FlowResultType.FORM, "step_id": "cloud_devices"}),
    ) as device_step:
        result = await config_flow.async_step_cloud_houses({CONF_HOUSE_ID: 1001})

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "cloud_devices"
    assert config_flow._house_id == 1001
    assert config_flow._house_name == "Office"
    validate_auth.assert_awaited_once_with(
        config_flow.hass,
        domain="https://private.example",
        access_token="private-token",
        client_id="",
        house_id=1001,
    )
    device_step.assert_awaited_once()


@pytest.mark.asyncio
async def test_private_house_precheck_failure_stays_on_house_form(config_flow) -> None:
    """私有部署已选家庭后的 Open API 读预检失败时应停留在家庭选择页。"""
    config_flow._connection_mode = CONNECTION_MODE_PRIVATE
    config_flow._domain = "https://private.example"
    config_flow._access_token = "private-token"
    config_flow._house_choices = {1001: "Project A"}

    with patch(
        "custom_components.yeelight_pro.config_flow.async_validate_private_auth",
        AsyncMock(side_effect=YeelightConnectionError("private endpoint")),
    ) as validate_auth, patch.object(
        config_flow,
        "async_step_cloud_devices",
        AsyncMock(),
    ) as device_step:
        result = await config_flow.async_step_cloud_houses({CONF_HOUSE_ID: 1001})

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "cloud_houses"
    assert result["errors"]["base"] == "cannot_connect"
    validate_auth.assert_awaited_once()
    device_step.assert_not_awaited()


@pytest.mark.asyncio
async def test_private_scan_login_uses_private_url_and_skips_region_guard(
    config_flow,
) -> None:
    """私有部署扫码登录应使用用户 URL，并不按云端区域拒绝 token。"""
    qr_code = parse_scan_login_response(_scan_login_payload_with_token_region("US"))
    client = MagicMock()
    client.create_scan_login_qrcode = AsyncMock(return_value=qr_code)
    config_flow._connection_mode = CONNECTION_MODE_PRIVATE
    config_flow._domain = "https://private.example"
    config_flow._cloud_region = "cn"
    config_flow.hass = MagicMock()

    with patch(
        "custom_components.yeelight_pro.config_flow_scan_login.async_scan_login_device_id",
        AsyncMock(return_value="ha-device-1"),
    ), patch.object(config_flow, "_scan_login_client", return_value=client):
        result = await config_flow.async_step_cloud_scan_login()

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "cloud_scan_login"
    client.create_scan_login_qrcode.assert_awaited_once_with(
        region="cn",
        device="ha-device-1",
        base_url="https://private.example/apis/account",
    )

    config_flow._scan_login_poll_task_ref = asyncio.Future()
    config_flow._scan_login_poll_task_ref.set_result(qr_code)
    with patch(
        "custom_components.yeelight_pro.config_flow.async_load_house_choices",
        AsyncMock(return_value={1001: "Project A"}),
    ):
        progress_result = await config_flow.async_step_cloud_scan_login_wait()

    assert progress_result["type"] == FlowResultType.SHOW_PROGRESS_DONE
    assert progress_result["step_id"] == "cloud_houses"
    assert config_flow._access_token == "access-1"
    assert config_flow._scan_login_state.last_error is None


def _scan_login_payload_with_token_region(region: str) -> dict[str, object]:
    """Return a scan-login LOGIN payload with an explicit token region."""
    payload = scan_login_login_payload()
    data = payload["data"]
    assert isinstance(data, dict)
    token = data["token"]
    assert isinstance(token, dict)
    token["region"] = region
    return payload
