"""Config-flow cloud real-device picker tests."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.data_entry_flow import FlowResultType

from custom_components.yeelight_pro.const import (
    CONF_DEVICE_IMPORT_FILTER,
    CONF_DEVICE_IMPORT_FILTER_INCLUDE_DEVICES,
)
from custom_components.yeelight_pro.core.exceptions import (
    ConnectionError as YeelightConnectionError,
)

from .config_flow_helpers import prepare_cloud_flow


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
    assert config_flow._device_choices == ()


@pytest.mark.asyncio
@patch("custom_components.yeelight_pro.config_flow_device_picker.async_get_clientsession")
@patch("custom_components.yeelight_pro.config_flow_device_picker.YeelightProClient")
async def test_cloud_devices_can_continue_without_filter_after_load_error(
    mock_client_class,
    mock_get_session,
    config_flow,
) -> None:
    """设备列表加载失败后仍可继续创建 entry，且不启用过滤。"""
    mock_client = AsyncMock()
    mock_client.get_devices.side_effect = YeelightConnectionError(
        "Offline secret-device-marker"
    )
    mock_client_class.return_value = mock_client
    mock_get_session.return_value = MagicMock()
    prepare_cloud_flow(config_flow)
    config_flow._house_id = 1

    form = await config_flow.async_step_cloud_devices()

    assert form["type"] == FlowResultType.FORM
    assert form["errors"]["base"] == "cannot_connect"
    with patch.object(config_flow, "async_set_unique_id", AsyncMock()), patch.object(
        config_flow,
        "_abort_if_unique_id_configured",
    ):
        result = await config_flow.async_step_cloud_devices({
            CONF_DEVICE_IMPORT_FILTER_INCLUDE_DEVICES: []
        })

    visible_options = str(result["options"])
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["options"][CONF_DEVICE_IMPORT_FILTER] == {
        "enabled": False,
        "mode": "or",
        "include": {},
        "exclude": {},
    }
    assert "Offline" not in visible_options
    assert "secret-device-marker" not in visible_options


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
async def test_cloud_devices_entry_options_store_ids_not_picker_labels(
    config_flow,
) -> None:
    """真实设备 picker 的名称和房间标签只用于 UI，不应持久化到 options。"""
    prepare_cloud_flow(config_flow)
    config_flow._house_id = 1
    config_flow._device_choices = (
        MagicMock(device_id="dev-1", label="Kitchen Secret / Room Secret"),
        MagicMock(device_id="dev-2", label="Bedroom Secret"),
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
            CONF_DEVICE_IMPORT_FILTER_INCLUDE_DEVICES: ["dev-1", "unknown-device"]
        })

    visible_options = str(result["options"])
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["options"][CONF_DEVICE_IMPORT_FILTER] == {
        "enabled": True,
        "mode": "or",
        "include": {"devices": ["dev-1"]},
        "exclude": {},
    }
    assert "Kitchen Secret" not in visible_options
    assert "Room Secret" not in visible_options
    assert "unknown-device" not in visible_options


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
