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
    CONF_DEVICE_IMPORT_FILTER,
    CONF_DEVICE_IMPORT_FILTER_INCLUDE_DEVICES,
    CONF_HOUSE_ID,
    CONF_OAUTH_CLIENT_ID,
    CONF_REFRESH_TOKEN,
    CONF_SCAN_LOGIN_DEVICE,
    CONF_TOKEN_TYPE,
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

    with patch.object(
        config_flow,
        "async_step_cloud_devices",
        AsyncMock(return_value={"type": FlowResultType.FORM, "step_id": "cloud_devices"}),
    ) as device_step:
        result = await config_flow.async_step_cloud_houses({CONF_HOUSE_ID: 1})

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "cloud_devices"
    assert config_flow._house_id == 1
    device_step.assert_awaited_once()


@pytest.mark.asyncio
@patch("custom_components.yeelight_pro.config_flow_device_picker.async_get_clientsession")
@patch("custom_components.yeelight_pro.config_flow_device_picker.YeelightProClient")
async def test_cloud_devices_loads_real_devices_and_defaults_to_all(
    mock_client_class,
    mock_get_session,
    config_flow,
) -> None:
    """设备 picker 应只读拉取当前家庭真实设备，并默认全选."""
    mock_client = AsyncMock()
    mock_client.get_devices.return_value = [
        {"id": "dev-1", "name": "Light"},
        {"id": "dev-2", "name": "Curtain"},
    ]
    mock_client_class.return_value = mock_client
    mock_get_session.return_value = MagicMock()
    prepare_cloud_flow(config_flow)
    config_flow._house_id = 1
    config_flow._open_api_client_id = "client-from-token"

    result = await config_flow.async_step_cloud_devices()

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "cloud_devices"
    schema = result["data_schema"].schema
    field = next(iter(schema))
    assert field.schema == CONF_DEVICE_IMPORT_FILTER_INCLUDE_DEVICES
    assert field.default() == ["dev-2", "dev-1"]
    device_selector = schema[field]
    assert device_selector.config["multiple"] is True
    assert device_selector.config["options"] == [
        {"value": "dev-2", "label": "Curtain"},
        {"value": "dev-1", "label": "Light"},
    ]
    mock_client.get_devices.assert_awaited_once_with(1)
    mock_client_class.assert_called_once()
    assert mock_client_class.call_args.kwargs["client_id"] == "client-from-token"


@pytest.mark.asyncio
@patch("custom_components.yeelight_pro.config_flow_device_picker.async_get_clientsession")
@patch("custom_components.yeelight_pro.config_flow_device_picker.YeelightProClient")
async def test_cloud_devices_maps_load_errors_to_form(
    mock_client_class,
    mock_get_session,
    config_flow,
) -> None:
    """设备列表加载失败时停留在 picker 表单并展示错误."""
    mock_client = AsyncMock()
    mock_client.get_devices.side_effect = YeelightConnectionError("Offline")
    mock_client_class.return_value = mock_client
    mock_get_session.return_value = MagicMock()
    prepare_cloud_flow(config_flow)
    config_flow._house_id = 1

    result = await config_flow.async_step_cloud_devices()

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "cloud_devices"
    assert result["errors"]["base"] == "cannot_connect"


@pytest.mark.asyncio
async def test_cloud_devices_user_selection_creates_filtered_entry(config_flow) -> None:
    """用户勾选设备后，创建 entry 时应保存实际导入过滤 options."""
    prepare_cloud_flow(config_flow)
    config_flow._house_id = 1
    config_flow._device_choices = (
        MagicMock(device_id="dev-1", label="Light"),
        MagicMock(device_id="dev-2", label="Curtain"),
    )

    with patch.object(
        config_flow,
        "async_set_unique_id",
        AsyncMock(),
    ), patch.object(
        config_flow,
        "_abort_if_unique_id_configured",
    ):
        result = await config_flow.async_step_cloud_devices({
            CONF_DEVICE_IMPORT_FILTER_INCLUDE_DEVICES: ["dev-1"]
        })

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["options"][CONF_DEVICE_IMPORT_FILTER] == {
        "enabled": True,
        "mode": "or",
        "include": {"devices": ["dev-1"]},
        "exclude": {},
    }


@pytest.mark.asyncio
async def test_cloud_devices_empty_house_creates_entry_without_filter(config_flow) -> None:
    """空家庭直接创建 entry，但不启用无规则设备过滤."""
    prepare_cloud_flow(config_flow)
    config_flow._house_id = 1
    config_flow._device_choices = ()

    with patch.object(
        config_flow,
        "async_set_unique_id",
        AsyncMock(),
    ), patch.object(
        config_flow,
        "_abort_if_unique_id_configured",
    ):
        result = await config_flow.async_step_cloud_devices({
            CONF_DEVICE_IMPORT_FILTER_INCLUDE_DEVICES: []
        })

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["options"][CONF_DEVICE_IMPORT_FILTER] == {
        "enabled": False,
        "mode": "or",
        "include": {},
        "exclude": {},
    }


@pytest.mark.asyncio
async def test_create_entry_persists_open_api_client_id(config_flow) -> None:
    """OAuth 路径创建 entry 时应保留 Open API clientId 头所需字段."""
    config_flow._connection_mode = CONNECTION_MODE_CLOUD
    config_flow._domain = "https://api.yeelight.com/apis/iot"
    config_flow._cloud_region = "cn"
    config_flow._access_token = "oauth-access-token"
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
    assert result["data"][CONF_OAUTH_CLIENT_ID] == "client-from-token"
    assert result["options"][CONF_DEVICE_IMPORT_FILTER] == {
        "enabled": False,
        "mode": "or",
        "include": {},
        "exclude": {},
    }


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
