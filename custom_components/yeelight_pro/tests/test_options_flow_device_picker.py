"""Options-flow real-device picker tests."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from homeassistant.data_entry_flow import FlowResultType

from custom_components.yeelight_pro.config_flow_device_picker import (
    DevicePickerChoice,
)
from custom_components.yeelight_pro.config_flow import YeelightProOptionsFlow
from custom_components.yeelight_pro.const import (
    CONF_CONNECTION_MODE,
    CONF_DEVICE_IMPORT_FILTER,
    CONF_DEVICE_IMPORT_FILTER_INCLUDE_DEVICES,
    CONF_DEVICE_IMPORT_FILTER_PICKER,
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
    """云端 entry 的 options 菜单应包含真实设备 picker 入口."""
    mock_config_entry.data[CONF_CONNECTION_MODE] = CONNECTION_MODE_CLOUD
    flow = YeelightProOptionsFlow(mock_config_entry)

    result = await flow.async_step_init()

    assert result["type"] == FlowResultType.MENU
    assert CONF_DEVICE_IMPORT_FILTER_PICKER
    assert "cloud_devices" in result["menu_options"]
    assert "filter_categories" in result["menu_options"]


@pytest.mark.asyncio
async def test_options_flow_private_entry_hides_real_device_picker_opener(
    mock_config_entry,
) -> None:
    """私有部署 entry 不显示真实云端设备 picker。"""
    mock_config_entry.data[CONF_CONNECTION_MODE] = CONNECTION_MODE_PRIVATE
    flow = YeelightProOptionsFlow(mock_config_entry)

    result = await flow.async_step_init()

    assert result["type"] == FlowResultType.MENU
    assert "cloud_devices" not in result["menu_options"]


@pytest.mark.asyncio
@patch("custom_components.yeelight_pro.options_flow.async_load_device_choices")
async def test_options_flow_real_device_picker_loads_current_cloud_devices(
    mock_load_choices,
    mock_config_entry,
    mock_hass,
) -> None:
    """options 真实设备 picker 应读取当前云端家庭设备列表。"""
    mock_config_entry.data.update({
        "cloud_domain": "api.yeelight.com",
        "access_token": "token-secret",
        "house_id": 123,
        "open_api_client_id": "client-id",
    })
    mock_config_entry.options = {
        CONF_DEVICE_IMPORT_FILTER: {
            "enabled": True,
            "mode": "or",
            "include": {"devices": ["dev-2"]},
            "exclude": {},
        }
    }
    mock_load_choices.return_value = (
        DevicePickerChoice("dev-1", "Kitchen Secret (开关控制器)"),
        DevicePickerChoice("dev-2", "Hall Light (灯具)"),
    )
    flow = YeelightProOptionsFlow(mock_config_entry)
    flow.hass = mock_hass

    result = await flow.async_step_cloud_devices()

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "cloud_devices"
    schema = result["data_schema"].schema
    field = next(iter(schema))
    assert field.schema == CONF_DEVICE_IMPORT_FILTER_INCLUDE_DEVICES
    assert field.default() == ["dev-2"]
    assert schema[field].config["options"] == [
        {"value": "dev-1", "label": "Kitchen Secret (开关控制器)"},
        {"value": "dev-2", "label": "Hall Light (灯具)"},
    ]
    mock_load_choices.assert_awaited_once_with(
        mock_hass,
        domain="api.yeelight.com",
        access_token="token-secret",
        house_id=123,
        client_id="client-id",
    )


@pytest.mark.asyncio
async def test_options_flow_real_device_picker_selection_requires_reload(
    mock_config_entry,
    mock_hass,
) -> None:
    """真实设备 picker 选择变化后写入 canonical filter 并要求 reload."""
    mock_config_entry.options = {}
    flow = YeelightProOptionsFlow(mock_config_entry)
    flow.hass = mock_hass
    flow._device_choices = (
        DevicePickerChoice("dev-1", "Kitchen Secret (开关控制器)"),
        DevicePickerChoice("dev-2", "Hall Light (灯具)"),
    )

    result = await flow.async_step_cloud_devices({
        CONF_DEVICE_IMPORT_FILTER_INCLUDE_DEVICES: ["dev-1", "unknown-device"],
    })

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "confirm_reload"

    result = await flow.async_step_confirm_reload({})
    visible_data = str(result["data"])

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_DEVICE_IMPORT_FILTER] == {
        "enabled": True,
        "mode": "or",
        "include": {"devices": ["dev-1"]},
        "exclude": {},
    }
    assert "Kitchen Secret" not in visible_data
    assert "unknown-device" not in visible_data


@pytest.mark.asyncio
@patch("custom_components.yeelight_pro.options_flow.async_load_device_choices")
async def test_options_flow_real_device_picker_load_error_is_redacted(
    mock_load_choices,
    mock_config_entry,
    mock_hass,
) -> None:
    """真实设备 picker 加载失败时只返回错误码，不泄露异常文本。"""
    mock_load_choices.side_effect = YeelightConnectionError(
        "Offline Kitchen Secret token-secret"
    )
    flow = YeelightProOptionsFlow(mock_config_entry)
    flow.hass = mock_hass

    result = await flow.async_step_cloud_devices()

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "cloud_devices"
    assert result["errors"]["base"] == "cannot_connect"
    assert "Kitchen Secret" not in str(result)
    assert "token-secret" not in str(result)
