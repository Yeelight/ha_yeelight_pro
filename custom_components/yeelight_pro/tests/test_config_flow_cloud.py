"""Config-flow cloud manual-token and house selection tests."""
from __future__ import annotations

from collections.abc import Callable
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.data_entry_flow import FlowResultType

from custom_components.yeelight_pro.const import (
    CONF_ACCESS_TOKEN,
    CONF_CLOUD_AUTH_METHOD,
    CONF_CLOUD_REGION,
    CONF_HOUSE_ID,
    CLOUD_AUTH_METHOD_ACCESS_TOKEN,
    CLOUD_AUTH_METHOD_SCAN_LOGIN,
    CONNECTION_MODE_CLOUD,
)
from custom_components.yeelight_pro.core.exceptions import (
    AuthenticationError,
    ConnectionError as YeelightConnectionError,
)

from .config_flow_helpers import prepare_cloud_flow


@pytest.mark.asyncio
async def test_cloud_region_selects_documented_multi_region_domain(config_flow) -> None:
    """云端区域选择应映射到用户确认的多区域 Open API 域名."""
    config_flow._connection_mode = CONNECTION_MODE_CLOUD

    result = await config_flow.async_step_cloud_region({CONF_CLOUD_REGION: "de"})

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "cloud_auth_method"
    assert config_flow._cloud_region == "de"
    assert config_flow._domain == "https://api-de.yeelight.com/apis/iot"


@pytest.mark.asyncio
async def test_cloud_auth_method_routes_to_scan_login(config_flow) -> None:
    """云端认证默认应进入易来 APP 扫码登录路径."""
    config_flow._connection_mode = CONNECTION_MODE_CLOUD
    config_flow._domain = "https://api.yeelight.com/apis/iot"

    with patch.object(
        config_flow,
        "async_step_cloud_scan_login",
        AsyncMock(return_value={"type": FlowResultType.FORM}),
    ) as scan_step:
        result = await config_flow.async_step_cloud_auth_method({
            CONF_CLOUD_AUTH_METHOD: CLOUD_AUTH_METHOD_SCAN_LOGIN
        })

    assert result["type"] == FlowResultType.FORM
    assert config_flow._cloud_auth_method == CLOUD_AUTH_METHOD_SCAN_LOGIN
    scan_step.assert_awaited_once()


@pytest.mark.asyncio
async def test_cloud_auth_method_routes_to_manual_token(config_flow) -> None:
    """云端认证方式选择应保留手动 Access Token 路径."""
    config_flow._connection_mode = CONNECTION_MODE_CLOUD
    config_flow._domain = "https://api.yeelight.com/apis/iot"

    result = await config_flow.async_step_cloud_auth_method({
        CONF_CLOUD_AUTH_METHOD: CLOUD_AUTH_METHOD_ACCESS_TOKEN
    })

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "cloud_auth"
    assert config_flow._cloud_auth_method == CLOUD_AUTH_METHOD_ACCESS_TOKEN


@pytest.mark.asyncio
@patch("custom_components.yeelight_pro.config_flow_helpers.async_get_clientsession")
@patch("custom_components.yeelight_pro.config_flow_helpers.YeelightProClient")
async def test_cloud_auth_success(
    mock_client_class,
    mock_get_session,
    config_flow,
) -> None:
    """测试云端认证成功."""
    mock_client = AsyncMock()
    mock_client.validate_auth.return_value = True
    mock_client.get_houses.return_value = [{"id": 1, "name": "Home"}]
    mock_client_class.return_value = mock_client
    mock_get_session.return_value = MagicMock()

    config_flow._connection_mode = CONNECTION_MODE_CLOUD
    config_flow._domain = "api.yeelight.com"
    config_flow.hass = MagicMock()

    result = await config_flow.async_step_cloud_auth({CONF_ACCESS_TOKEN: "test_token"})

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "cloud_houses"
    assert config_flow._access_token == "test_token"


@pytest.mark.asyncio
@patch("custom_components.yeelight_pro.config_flow_helpers.async_get_clientsession")
@patch("custom_components.yeelight_pro.config_flow_helpers.YeelightProClient")
async def test_cloud_auth_invalid_token(
    mock_client_class,
    mock_get_session,
    config_flow,
) -> None:
    """测试云端认证失败."""
    mock_client = AsyncMock()
    mock_client.validate_auth.side_effect = AuthenticationError("Invalid")
    mock_client_class.return_value = mock_client
    mock_get_session.return_value = MagicMock()

    config_flow._connection_mode = CONNECTION_MODE_CLOUD
    config_flow._domain = "api.yeelight.com"
    config_flow.hass = MagicMock()

    result = await config_flow.async_step_cloud_auth({
        CONF_ACCESS_TOKEN: "invalid_token"
    })

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_auth"


@pytest.mark.asyncio
@patch("custom_components.yeelight_pro.config_flow_helpers.async_get_clientsession")
@patch("custom_components.yeelight_pro.config_flow_helpers.YeelightProClient")
async def test_cloud_houses_no_houses_aborts(
    mock_client_class,
    mock_get_session,
    config_flow,
) -> None:
    """家庭列表为空时保留明确 abort 语义."""
    mock_client = AsyncMock()
    mock_client.get_houses.return_value = []
    mock_client_class.return_value = mock_client
    mock_get_session.return_value = MagicMock()
    prepare_cloud_flow(config_flow)

    result = await config_flow.async_step_cloud_houses()

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "no_houses_found"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error_factory", "expected_error"),
    [
        (lambda: AuthenticationError("Invalid"), "invalid_auth"),
        (lambda: YeelightConnectionError("Offline"), "cannot_connect"),
        (lambda: RuntimeError("Boom"), "unknown"),
    ],
)
@patch("custom_components.yeelight_pro.config_flow_helpers.async_get_clientsession")
@patch("custom_components.yeelight_pro.config_flow_helpers.YeelightProClient")
async def test_cloud_houses_maps_load_errors_to_form(
    mock_client_class,
    mock_get_session,
    config_flow,
    error_factory: Callable[[], Exception],
    expected_error: str,
) -> None:
    """加载家庭失败时显示 cloud_houses 表单并映射错误."""
    mock_client = AsyncMock()
    mock_client.get_houses.side_effect = error_factory()
    mock_client_class.return_value = mock_client
    mock_get_session.return_value = MagicMock()
    prepare_cloud_flow(config_flow)

    result = await config_flow.async_step_cloud_houses()

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "cloud_houses"
    assert result["errors"]["base"] == expected_error


@pytest.mark.asyncio
async def test_cloud_houses_user_selection_opens_real_device_picker(config_flow) -> None:
    """已选家庭后应进入真实设备 picker，而不是直接导入全量设备."""
    prepare_cloud_flow(config_flow)

    with patch(
        "custom_components.yeelight_pro.config_flow.async_validate_auth",
        AsyncMock(),
    ) as validate_auth, patch.object(
        config_flow,
        "async_step_cloud_devices",
        AsyncMock(return_value={"type": FlowResultType.FORM, "step_id": "cloud_devices"}),
    ) as device_step:
        result = await config_flow.async_step_cloud_houses({CONF_HOUSE_ID: 1})

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "cloud_devices"
    assert config_flow._house_id == 1
    validate_auth.assert_awaited_once_with(
        config_flow.hass,
        domain=config_flow._domain,
        access_token=config_flow._access_token,
        client_id=config_flow._open_api_client_id,
        house_id=1,
    )
    device_step.assert_awaited_once()


@pytest.mark.asyncio
async def test_cloud_houses_user_selection_precheck_failure_stays_on_form(
    config_flow,
) -> None:
    """已选家庭后的 Open API 读预检失败时应停留在家庭选择页。"""
    prepare_cloud_flow(config_flow)
    config_flow._house_choices = {1: "Home"}

    with patch(
        "custom_components.yeelight_pro.config_flow.async_validate_auth",
        AsyncMock(side_effect=YeelightConnectionError("secret-token url")),
    ) as validate_auth, patch.object(
        config_flow,
        "async_step_cloud_devices",
        AsyncMock(),
    ) as device_step:
        result = await config_flow.async_step_cloud_houses({CONF_HOUSE_ID: 1})

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "cloud_houses"
    assert result["errors"]["base"] == "cannot_connect"
    validate_auth.assert_awaited_once()
    device_step.assert_not_awaited()
