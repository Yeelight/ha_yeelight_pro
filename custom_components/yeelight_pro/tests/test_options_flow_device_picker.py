"""Options-flow real cloud device picker tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.data_entry_flow import FlowResultType

from custom_components.yeelight_pro.config_flow import YeelightProOptionsFlow
from custom_components.yeelight_pro.const import (
    CONF_ACCESS_TOKEN,
    CONF_CLOUD_DOMAIN,
    CONF_CONNECTION_MODE,
    CONF_DEVICE_IMPORT_FILTER,
    CONF_DEVICE_IMPORT_FILTER_INCLUDE_DEVICES,
    CONF_DEVICE_IMPORT_FILTER_PICKER,
    CONF_HOUSE_ID,
    CONF_OAUTH_CLIENT_ID,
    CONNECTION_MODE_CLOUD,
    CONNECTION_MODE_PRIVATE,
)
from custom_components.yeelight_pro.core.exceptions import (
    ConnectionError as YeelightConnectionError,
)


@pytest.mark.asyncio
async def test_options_flow_cloud_entry_shows_real_device_picker_opener(
    mock_config_entry,
) -> None:
    """云端 entry 的 options 首屏应提供真实设备 picker 入口."""
    mock_config_entry.data = _cloud_entry_data()
    mock_config_entry.options = {}
    flow = YeelightProOptionsFlow(mock_config_entry)

    result = await flow.async_step_init()

    assert result["type"] == FlowResultType.FORM
    schema = result["data_schema"].schema
    defaults = {marker.schema: marker.default() for marker in schema}
    assert defaults[CONF_DEVICE_IMPORT_FILTER_PICKER] is False


@pytest.mark.asyncio
async def test_options_flow_private_entry_hides_real_device_picker_opener(
    mock_config_entry,
) -> None:
    """私有部署 entry 没有云端真实设备列表，不应显示 picker 入口."""
    mock_config_entry.data = {
        CONF_CONNECTION_MODE: CONNECTION_MODE_PRIVATE,
        CONF_HOUSE_ID: 1,
    }
    mock_config_entry.options = {}
    flow = YeelightProOptionsFlow(mock_config_entry)

    result = await flow.async_step_init()

    assert result["type"] == FlowResultType.FORM
    schema = result["data_schema"].schema
    assert all(
        marker.schema != CONF_DEVICE_IMPORT_FILTER_PICKER
        for marker in schema
    )


@pytest.mark.asyncio
@patch("custom_components.yeelight_pro.config_flow_device_picker.async_get_clientsession")
@patch("custom_components.yeelight_pro.config_flow_device_picker.YeelightProClient")
async def test_options_flow_real_device_picker_loads_current_cloud_devices(
    mock_client_class,
    mock_get_session,
    mock_config_entry,
) -> None:
    """options 里的真实设备 picker 应按当前 entry 拉取 house 设备列表."""
    mock_config_entry.data = _cloud_entry_data()
    mock_config_entry.options = {
        CONF_DEVICE_IMPORT_FILTER: {
            "enabled": True,
            "mode": "or",
            "include": {"devices": ["dev-2"]},
            "exclude": {},
        }
    }
    mock_client = AsyncMock()
    mock_client.get_devices.return_value = [
        {"id": "dev-1", "name": "Kitchen"},
        {"id": "dev-2", "name": "Bedroom"},
    ]
    mock_client_class.return_value = mock_client
    mock_get_session.return_value = MagicMock()
    flow = YeelightProOptionsFlow(mock_config_entry)

    result = await flow.async_step_init({CONF_DEVICE_IMPORT_FILTER_PICKER: True})

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "cloud_devices"
    schema = result["data_schema"].schema
    field = next(iter(schema))
    assert field.schema == CONF_DEVICE_IMPORT_FILTER_INCLUDE_DEVICES
    assert field.default() == ["dev-2"]
    device_selector = schema[field]
    assert device_selector.config["multiple"] is True
    assert device_selector.config["options"] == [
        {"value": "dev-2", "label": "Bedroom"},
        {"value": "dev-1", "label": "Kitchen"},
    ]
    mock_client_class.assert_called_once()
    assert mock_client_class.call_args.kwargs["domain"] == "https://api.yeelight.com"
    assert mock_client_class.call_args.kwargs["client_id"] == "client-from-token"
    mock_client.get_devices.assert_awaited_once_with(12345)


@pytest.mark.asyncio
async def test_options_flow_real_device_picker_selection_requires_reload(
    mock_config_entry,
) -> None:
    """设备 picker 保存导入范围后必须进入 reload 确认并只持久化设备 ID."""
    mock_config_entry.data = _cloud_entry_data()
    mock_config_entry.options = {
        CONF_DEVICE_IMPORT_FILTER: {"enabled": False},
        "future_option": "keep",
    }
    flow = YeelightProOptionsFlow(mock_config_entry)
    flow._device_choices = (
        MagicMock(device_id="dev-1", label="Kitchen Secret / Room Secret"),
        MagicMock(device_id="dev-2", label="Bedroom Secret"),
    )

    result = await flow.async_step_cloud_devices({
        CONF_DEVICE_IMPORT_FILTER_INCLUDE_DEVICES: ["dev-1", "unknown-device"]
    })

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "confirm_reload"
    assert result["description_placeholders"] == {"changed_count": "1"}

    result = await flow.async_step_confirm_reload({})

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_DEVICE_IMPORT_FILTER] == {
        "enabled": True,
        "mode": "or",
        "include": {"devices": ["dev-1"]},
        "exclude": {},
    }
    visible_options = str(result["data"])
    assert "Kitchen Secret" not in visible_options
    assert "Room Secret" not in visible_options
    assert "unknown-device" not in visible_options
    assert result["data"]["future_option"] == "keep"


@pytest.mark.asyncio
@patch("custom_components.yeelight_pro.config_flow_device_picker.async_get_clientsession")
@patch("custom_components.yeelight_pro.config_flow_device_picker.YeelightProClient")
async def test_options_flow_real_device_picker_load_error_is_redacted(
    mock_client_class,
    mock_get_session,
    mock_config_entry,
) -> None:
    """options picker 加载失败时只显示错误码，不泄漏设备或 token 文本."""
    mock_config_entry.data = _cloud_entry_data()
    mock_config_entry.options = {}
    mock_client = AsyncMock()
    mock_client.get_devices.side_effect = YeelightConnectionError(
        "secret-device-id token=secret"
    )
    mock_client_class.return_value = mock_client
    mock_get_session.return_value = MagicMock()
    flow = YeelightProOptionsFlow(mock_config_entry)

    result = await flow.async_step_cloud_devices()

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "cloud_devices"
    assert result["errors"]["base"] == "cannot_connect"
    assert "secret-device-id" not in str(result)
    assert "token=secret" not in str(result)


def _cloud_entry_data() -> dict[str, object]:
    """Return cloud entry data with enough context for the real-device picker."""
    return {
        CONF_CONNECTION_MODE: CONNECTION_MODE_CLOUD,
        CONF_CLOUD_DOMAIN: "https://api.yeelight.com",
        CONF_ACCESS_TOKEN: "test-token",
        CONF_HOUSE_ID: 12345,
        CONF_OAUTH_CLIENT_ID: "client-from-token",
    }
