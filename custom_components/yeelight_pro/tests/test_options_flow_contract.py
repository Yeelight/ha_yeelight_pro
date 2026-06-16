"""Options flow and runtime option contract tests."""

from __future__ import annotations

import pytest

from homeassistant.data_entry_flow import FlowResultType

from custom_components.yeelight_pro.config_flow import YeelightProOptionsFlow
from custom_components.yeelight_pro.const import (
    CONF_CONNECTION_MODE,
    CONF_DEBUG_MODE,
    CONF_DEVICE_IMPORT_FILTER,
    CONF_HIDE_UNKNOWN_ENTITIES,
    CONF_LIVE_UPDATES,
    CONF_LOCAL_GATEWAY_CONTROL,
    CONF_LOCAL_GATEWAY_HOST,
    CONF_LOCAL_GATEWAY_PORT,
    CONF_SCAN_INTERVAL,
    CONF_TOPOLOGY_CHANGE_REPAIRS,
    DEFAULT_LIVE_UPDATES,
    DEFAULT_LOCAL_GATEWAY_CONTROL,
    DEFAULT_LOCAL_GATEWAY_HOST,
    DEFAULT_LOCAL_GATEWAY_PORT,
    DEFAULT_SCAN_INTERVAL,
    CONNECTION_MODE_LAN,
)


@pytest.mark.asyncio
async def test_options_flow_shows_defaults(mock_config_entry) -> None:
    """未保存 options 时表单必须使用生产默认值."""
    mock_config_entry.options = {}
    flow = YeelightProOptionsFlow(mock_config_entry)

    result = await flow.async_step_general()

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "general"
    schema = result["data_schema"].schema
    defaults = {marker.schema: marker.default() for marker in schema}
    assert defaults[CONF_SCAN_INTERVAL] == DEFAULT_SCAN_INTERVAL
    assert defaults[CONF_DEBUG_MODE] is False
    assert defaults[CONF_HIDE_UNKNOWN_ENTITIES] is True
    assert defaults[CONF_TOPOLOGY_CHANGE_REPAIRS] is True
    assert defaults[CONF_LIVE_UPDATES] is DEFAULT_LIVE_UPDATES
    assert CONF_LOCAL_GATEWAY_CONTROL not in defaults
    assert CONF_LOCAL_GATEWAY_HOST not in defaults
    assert CONF_LOCAL_GATEWAY_PORT not in defaults


@pytest.mark.asyncio
async def test_options_flow_shows_local_gateway_defaults_for_lan(
    mock_config_entry,
) -> None:
    """局域网模式才应在通用页显示本地网关 options."""
    mock_config_entry.data[CONF_CONNECTION_MODE] = CONNECTION_MODE_LAN
    mock_config_entry.options = {}
    flow = YeelightProOptionsFlow(mock_config_entry)

    result = await flow.async_step_general()

    assert result["type"] == FlowResultType.FORM
    schema = result["data_schema"].schema
    defaults = {marker.schema: marker.default() for marker in schema}
    assert CONF_LIVE_UPDATES not in defaults
    assert defaults[CONF_LOCAL_GATEWAY_CONTROL] is DEFAULT_LOCAL_GATEWAY_CONTROL
    assert defaults[CONF_LOCAL_GATEWAY_HOST] == DEFAULT_LOCAL_GATEWAY_HOST
    assert defaults[CONF_LOCAL_GATEWAY_PORT] == DEFAULT_LOCAL_GATEWAY_PORT


@pytest.mark.asyncio
async def test_options_flow_ignores_invalid_legacy_options(mock_config_entry) -> None:
    """旧 entry 或测试替身的非 dict options 不应破坏 options flow."""
    mock_config_entry.options = None
    flow = YeelightProOptionsFlow(mock_config_entry)

    result = await flow.async_step_general()

    assert result["type"] == FlowResultType.FORM
    schema = result["data_schema"].schema
    defaults = {marker.schema: marker.default() for marker in schema}
    assert defaults[CONF_SCAN_INTERVAL] == DEFAULT_SCAN_INTERVAL
    assert defaults[CONF_DEBUG_MODE] is False
    assert defaults[CONF_HIDE_UNKNOWN_ENTITIES] is True
    assert defaults[CONF_TOPOLOGY_CHANGE_REPAIRS] is True


@pytest.mark.asyncio
async def test_options_flow_confirms_runtime_only_options(mock_config_entry) -> None:
    """运行时 options 变更先显示确认页，确认后再保存."""
    import_filter = {
        "enabled": True,
        "exclude": {"devices": ["device-secret-1"]},
    }
    mock_config_entry.options = {
        CONF_DEVICE_IMPORT_FILTER: import_filter,
        "future_option": "keep",
        "experimental_platforms": True,
        CONF_HIDE_UNKNOWN_ENTITIES: True,
    }
    flow = YeelightProOptionsFlow(mock_config_entry)

    result = await flow.async_step_general({
        CONF_SCAN_INTERVAL: 45,
        CONF_DEBUG_MODE: True,
        CONF_HIDE_UNKNOWN_ENTITIES: True,
        CONF_TOPOLOGY_CHANGE_REPAIRS: False,
        CONF_LIVE_UPDATES: DEFAULT_LIVE_UPDATES,
    })

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "confirm_runtime"
    assert result["description_placeholders"] == {
        "changed_count": "3",
    }

    result = await flow.async_step_confirm_runtime({})

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_DEVICE_IMPORT_FILTER: {
            "enabled": True,
            "mode": "or",
            "include": {},
            "exclude": {"devices": ["device-secret-1"]},
        },
        "future_option": "keep",
        CONF_SCAN_INTERVAL: 45,
        CONF_DEBUG_MODE: True,
        CONF_HIDE_UNKNOWN_ENTITIES: True,
        CONF_TOPOLOGY_CHANGE_REPAIRS: False,
        CONF_LIVE_UPDATES: DEFAULT_LIVE_UPDATES,
    }


@pytest.mark.parametrize(
    ("option_key", "changed_value"),
    [
        pytest.param(CONF_LIVE_UPDATES, True, id="live_updates_websocket"),
    ],
)
@pytest.mark.asyncio
async def test_options_flow_background_runtime_options_require_reload(
    mock_config_entry,
    option_key: str,
    changed_value,
) -> None:
    """启停 WebSocket/LAN 后台 runtime 必须进入 reload 确认页."""
    mock_config_entry.options = {
        CONF_SCAN_INTERVAL: 15,
        CONF_DEBUG_MODE: False,
        CONF_HIDE_UNKNOWN_ENTITIES: True,
        CONF_TOPOLOGY_CHANGE_REPAIRS: True,
        CONF_LIVE_UPDATES: False,
    }
    flow = YeelightProOptionsFlow(mock_config_entry)

    result = await flow.async_step_general({
        **mock_config_entry.options,
        option_key: changed_value,
    })

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "confirm_reload"
    assert result["description_placeholders"] == {
        "changed_count": "1",
    }


@pytest.mark.parametrize(
    ("option_key", "changed_value"),
    [
        pytest.param(CONF_LOCAL_GATEWAY_CONTROL, True, id="local_gateway_control"),
        pytest.param(CONF_LOCAL_GATEWAY_HOST, "192.168.1.20", id="local_gateway_host"),
        pytest.param(CONF_LOCAL_GATEWAY_PORT, 65444, id="local_gateway_port"),
    ],
)
@pytest.mark.asyncio
async def test_options_flow_lan_runtime_options_require_reload(
    mock_config_entry,
    option_key: str,
    changed_value,
) -> None:
    """局域网 runtime 选项变更必须进入 reload 确认页."""
    mock_config_entry.data[CONF_CONNECTION_MODE] = CONNECTION_MODE_LAN
    mock_config_entry.options = {
        CONF_SCAN_INTERVAL: 15,
        CONF_DEBUG_MODE: False,
        CONF_HIDE_UNKNOWN_ENTITIES: True,
        CONF_TOPOLOGY_CHANGE_REPAIRS: True,
        CONF_LOCAL_GATEWAY_CONTROL: False,
        CONF_LOCAL_GATEWAY_HOST: "",
        CONF_LOCAL_GATEWAY_PORT: 65443,
    }
    flow = YeelightProOptionsFlow(mock_config_entry)

    result = await flow.async_step_general({
        **mock_config_entry.options,
        option_key: changed_value,
    })

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "confirm_reload"
    assert result["description_placeholders"] == {
        "changed_count": "1",
    }


@pytest.mark.asyncio
async def test_options_flow_confirms_reload_required_options(mock_config_entry) -> None:
    """影响实体集合的 options 应在确认页明确提示需要 reload."""
    mock_config_entry.options = {
        CONF_SCAN_INTERVAL: 15,
        CONF_DEBUG_MODE: False,
        CONF_HIDE_UNKNOWN_ENTITIES: True,
        CONF_TOPOLOGY_CHANGE_REPAIRS: True,
    }
    flow = YeelightProOptionsFlow(mock_config_entry)

    result = await flow.async_step_general({
        CONF_SCAN_INTERVAL: 15,
        CONF_DEBUG_MODE: False,
        CONF_HIDE_UNKNOWN_ENTITIES: False,
        CONF_TOPOLOGY_CHANGE_REPAIRS: True,
    })

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "confirm_reload"
    assert result["description_placeholders"] == {
        "changed_count": "1",
    }


@pytest.mark.asyncio
async def test_options_flow_device_filter_wizard_requires_reload(
    mock_config_entry,
    mock_hass,
) -> None:
    """设备过滤向导取消选择后写入 exclude 规则并要求 reload."""
    mock_config_entry.options = {
        CONF_SCAN_INTERVAL: 15,
        CONF_DEBUG_MODE: False,
        CONF_HIDE_UNKNOWN_ENTITIES: True,
        CONF_TOPOLOGY_CHANGE_REPAIRS: True,
    }
    flow = YeelightProOptionsFlow(mock_config_entry)
    flow.hass = mock_hass
    mock_hass.data["yeelight_pro"] = {
        mock_config_entry.entry_id: {
            "coordinator": type(
                "Coordinator",
                (),
                {
                    "data": {
                        "device-1": {
                            "device_id": "device-1",
                            "name": "客厅灯",
                            "category": "light",
                            "roomId": "room-1",
                            "roomName": "客厅",
                            "gatewayId": "gw-1",
                        },
                        "device-2": {
                            "device_id": "device-2",
                            "name": "卧室灯",
                            "category": "light",
                            "roomId": "room-2",
                            "roomName": "卧室",
                            "gatewayId": "gw-1",
                        },
                    },
                },
            )(),
        }
    }

    result = await flow.async_step_filter_categories({"filter_categories": ["light"]})
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "filter_rooms"

    result = await flow.async_step_filter_rooms({"filter_rooms": ["room-1"]})
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "filter_gateways"

    result = await flow.async_step_filter_gateways({"filter_gateways": ["gw-1"]})
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "filter_devices"

    result = await flow.async_step_filter_devices({"filter_devices": ["device-1"]})
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "confirm_reload"

    result = await flow.async_step_confirm_reload({})

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_DEVICE_IMPORT_FILTER] == {
        "enabled": True,
        "mode": "or",
        "include": {},
        "exclude": {
            "devices": ["device-2"],
            "rooms": ["room-2"],
        },
    }


@pytest.mark.asyncio
async def test_options_flow_confirm_without_pending_returns_init(mock_config_entry) -> None:
    """直接访问确认步骤时应回到初始菜单，避免保存空 options."""
    flow = YeelightProOptionsFlow(mock_config_entry)

    result = await flow.async_step_confirm_runtime({})

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "init"


@pytest.mark.asyncio
async def test_options_flow_confirm_step_rechecks_reload_requirement(
    mock_config_entry,
) -> None:
    """确认步骤自身必须复核 reload 判断，避免错误 step 直接保存."""
    mock_config_entry.options = {
        CONF_SCAN_INTERVAL: 15,
        CONF_DEBUG_MODE: False,
        CONF_HIDE_UNKNOWN_ENTITIES: True,
        CONF_TOPOLOGY_CHANGE_REPAIRS: True,
    }
    flow = YeelightProOptionsFlow(mock_config_entry)

    result = await flow.async_step_general({
        CONF_SCAN_INTERVAL: 15,
        CONF_DEBUG_MODE: False,
        CONF_HIDE_UNKNOWN_ENTITIES: False,
        CONF_TOPOLOGY_CHANGE_REPAIRS: True,
    })
    assert result["step_id"] == "confirm_reload"

    result = await flow.async_step_confirm_runtime({})

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "confirm_reload"


@pytest.mark.asyncio
async def test_options_flow_confirm_step_rechecks_runtime_requirement(
    mock_config_entry,
) -> None:
    """运行时变更被误送到 reload 确认 step 时应回到 runtime 确认页."""
    mock_config_entry.options = {
        CONF_SCAN_INTERVAL: 15,
        CONF_DEBUG_MODE: False,
        CONF_HIDE_UNKNOWN_ENTITIES: True,
        CONF_TOPOLOGY_CHANGE_REPAIRS: True,
    }
    flow = YeelightProOptionsFlow(mock_config_entry)

    result = await flow.async_step_general({
        CONF_SCAN_INTERVAL: 45,
        CONF_DEBUG_MODE: False,
        CONF_HIDE_UNKNOWN_ENTITIES: True,
        CONF_TOPOLOGY_CHANGE_REPAIRS: True,
    })
    assert result["step_id"] == "confirm_runtime"

    result = await flow.async_step_confirm_reload({})

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "confirm_runtime"
