"""Options flow and runtime option contract tests."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.yeelight_pro.config_flow import YeelightProOptionsFlow
from custom_components.yeelight_pro.const import (
    CONF_DEBUG_MODE,
    CONF_DEVICE_IMPORT_FILTER,
    CONF_DEVICE_IMPORT_FILTER_ENABLED,
    CONF_DEVICE_IMPORT_FILTER_INCLUDE_CATEGORIES,
    CONF_DEVICE_IMPORT_FILTER_INCLUDE_DEVICES,
    CONF_DEVICE_IMPORT_FILTER_MODE,
    CONF_EXPERIMENTAL_PLATFORMS,
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
    EXPERIMENTAL_PLATFORMS,
    PLATFORMS,
    get_enabled_platforms,
)
from custom_components.yeelight_pro.core.client import YeelightProClient
from custom_components.yeelight_pro.core.coordinator import YeelightProCoordinator


@pytest.mark.asyncio
async def test_options_flow_shows_defaults(mock_config_entry) -> None:
    """未保存 options 时表单必须使用生产默认值."""
    mock_config_entry.options = {}
    flow = YeelightProOptionsFlow(mock_config_entry)

    result = await flow.async_step_init()

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"
    schema = result["data_schema"].schema
    defaults = {marker.schema: marker.default() for marker in schema}
    assert defaults[CONF_SCAN_INTERVAL] == DEFAULT_SCAN_INTERVAL
    assert defaults[CONF_DEBUG_MODE] is False
    assert defaults[CONF_EXPERIMENTAL_PLATFORMS] is False
    assert defaults[CONF_HIDE_UNKNOWN_ENTITIES] is True
    assert defaults[CONF_TOPOLOGY_CHANGE_REPAIRS] is True
    assert defaults[CONF_LIVE_UPDATES] is False
    assert defaults[CONF_LOCAL_GATEWAY_CONTROL] is False
    assert defaults[CONF_LOCAL_GATEWAY_HOST] == ""
    assert defaults[CONF_LOCAL_GATEWAY_PORT] == 65443
    assert defaults[CONF_DEVICE_IMPORT_FILTER_ENABLED] is False
    assert defaults[CONF_DEVICE_IMPORT_FILTER_MODE] == "or"


@pytest.mark.asyncio
async def test_options_flow_ignores_invalid_legacy_options(mock_config_entry) -> None:
    """旧 entry 或测试替身的非 dict options 不应破坏 options flow."""
    mock_config_entry.options = None
    flow = YeelightProOptionsFlow(mock_config_entry)

    result = await flow.async_step_init()

    assert result["type"] == FlowResultType.FORM
    schema = result["data_schema"].schema
    defaults = {marker.schema: marker.default() for marker in schema}
    assert defaults[CONF_SCAN_INTERVAL] == DEFAULT_SCAN_INTERVAL
    assert defaults[CONF_DEBUG_MODE] is False
    assert defaults[CONF_EXPERIMENTAL_PLATFORMS] is False
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
        CONF_EXPERIMENTAL_PLATFORMS: False,
        CONF_HIDE_UNKNOWN_ENTITIES: True,
    }
    flow = YeelightProOptionsFlow(mock_config_entry)

    result = await flow.async_step_init({
        CONF_SCAN_INTERVAL: 45,
        CONF_DEBUG_MODE: True,
        CONF_EXPERIMENTAL_PLATFORMS: False,
        CONF_HIDE_UNKNOWN_ENTITIES: True,
        CONF_TOPOLOGY_CHANGE_REPAIRS: False,
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
        CONF_EXPERIMENTAL_PLATFORMS: False,
        CONF_HIDE_UNKNOWN_ENTITIES: True,
        CONF_TOPOLOGY_CHANGE_REPAIRS: False,
        CONF_LIVE_UPDATES: DEFAULT_LIVE_UPDATES,
        CONF_LOCAL_GATEWAY_CONTROL: DEFAULT_LOCAL_GATEWAY_CONTROL,
        CONF_LOCAL_GATEWAY_HOST: DEFAULT_LOCAL_GATEWAY_HOST,
        CONF_LOCAL_GATEWAY_PORT: DEFAULT_LOCAL_GATEWAY_PORT,
    }


@pytest.mark.parametrize(
    ("option_key", "changed_value"),
    [
        pytest.param(CONF_LIVE_UPDATES, True, id="live_updates_websocket"),
        pytest.param(CONF_LOCAL_GATEWAY_CONTROL, True, id="local_gateway_control"),
        pytest.param(CONF_LOCAL_GATEWAY_HOST, "192.168.1.20", id="local_gateway_host"),
        pytest.param(CONF_LOCAL_GATEWAY_PORT, 65444, id="local_gateway_port"),
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
        CONF_EXPERIMENTAL_PLATFORMS: False,
        CONF_HIDE_UNKNOWN_ENTITIES: True,
        CONF_TOPOLOGY_CHANGE_REPAIRS: True,
        CONF_LIVE_UPDATES: False,
        CONF_LOCAL_GATEWAY_CONTROL: False,
        CONF_LOCAL_GATEWAY_HOST: "",
        CONF_LOCAL_GATEWAY_PORT: 65443,
    }
    flow = YeelightProOptionsFlow(mock_config_entry)

    result = await flow.async_step_init({
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
        CONF_EXPERIMENTAL_PLATFORMS: False,
        CONF_HIDE_UNKNOWN_ENTITIES: True,
        CONF_TOPOLOGY_CHANGE_REPAIRS: True,
    }
    flow = YeelightProOptionsFlow(mock_config_entry)

    result = await flow.async_step_init({
        CONF_SCAN_INTERVAL: 15,
        CONF_DEBUG_MODE: False,
        CONF_EXPERIMENTAL_PLATFORMS: True,
        CONF_HIDE_UNKNOWN_ENTITIES: False,
        CONF_TOPOLOGY_CHANGE_REPAIRS: True,
    })

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "confirm_reload"
    assert result["description_placeholders"] == {
        "changed_count": "2",
    }


@pytest.mark.asyncio
async def test_options_flow_manual_device_filter_requires_reload(
    mock_config_entry,
) -> None:
    """手动设备过滤配置写入 options 后必须走 reload 确认."""
    mock_config_entry.options = {
        CONF_SCAN_INTERVAL: 15,
        CONF_DEBUG_MODE: False,
        CONF_EXPERIMENTAL_PLATFORMS: False,
        CONF_HIDE_UNKNOWN_ENTITIES: True,
        CONF_TOPOLOGY_CHANGE_REPAIRS: True,
    }
    flow = YeelightProOptionsFlow(mock_config_entry)

    result = await flow.async_step_init({
        CONF_SCAN_INTERVAL: 15,
        CONF_DEBUG_MODE: False,
        CONF_EXPERIMENTAL_PLATFORMS: False,
        CONF_HIDE_UNKNOWN_ENTITIES: True,
        CONF_TOPOLOGY_CHANGE_REPAIRS: True,
        CONF_DEVICE_IMPORT_FILTER_ENABLED: True,
        CONF_DEVICE_IMPORT_FILTER_MODE: "or",
        CONF_DEVICE_IMPORT_FILTER_INCLUDE_CATEGORIES: "light, curtain",
        CONF_DEVICE_IMPORT_FILTER_INCLUDE_DEVICES: "device-1",
    })

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "confirm_reload"
    assert result["description_placeholders"] == {
        "changed_count": "1",
    }

    result = await flow.async_step_confirm_reload({})

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_DEVICE_IMPORT_FILTER] == {
        "enabled": True,
        "mode": "or",
        "include": {
            "categories": ["curtain", "light"],
            "devices": ["device-1"],
        },
        "exclude": {},
    }
    assert CONF_DEVICE_IMPORT_FILTER_ENABLED not in result["data"]


@pytest.mark.asyncio
async def test_options_flow_confirm_without_pending_returns_init(mock_config_entry) -> None:
    """直接访问确认步骤时应回到初始表单，避免保存空 options."""
    flow = YeelightProOptionsFlow(mock_config_entry)

    result = await flow.async_step_confirm_runtime({})

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"


@pytest.mark.asyncio
async def test_options_flow_confirm_step_rechecks_reload_requirement(
    mock_config_entry,
) -> None:
    """确认步骤自身必须复核 reload 判断，避免错误 step 直接保存."""
    mock_config_entry.options = {
        CONF_SCAN_INTERVAL: 15,
        CONF_DEBUG_MODE: False,
        CONF_EXPERIMENTAL_PLATFORMS: False,
        CONF_HIDE_UNKNOWN_ENTITIES: True,
        CONF_TOPOLOGY_CHANGE_REPAIRS: True,
    }
    flow = YeelightProOptionsFlow(mock_config_entry)

    result = await flow.async_step_init({
        CONF_SCAN_INTERVAL: 15,
        CONF_DEBUG_MODE: False,
        CONF_EXPERIMENTAL_PLATFORMS: True,
        CONF_HIDE_UNKNOWN_ENTITIES: True,
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
        CONF_EXPERIMENTAL_PLATFORMS: False,
        CONF_HIDE_UNKNOWN_ENTITIES: True,
        CONF_TOPOLOGY_CHANGE_REPAIRS: True,
    }
    flow = YeelightProOptionsFlow(mock_config_entry)

    result = await flow.async_step_init({
        CONF_SCAN_INTERVAL: 45,
        CONF_DEBUG_MODE: False,
        CONF_EXPERIMENTAL_PLATFORMS: False,
        CONF_HIDE_UNKNOWN_ENTITIES: True,
        CONF_TOPOLOGY_CHANGE_REPAIRS: True,
    })
    assert result["step_id"] == "confirm_runtime"

    result = await flow.async_step_confirm_reload({})

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "confirm_runtime"


def test_enabled_platforms_hide_experimental_by_default() -> None:
    """实验平台默认不加载，但仍保留在声明平台中供显式启用."""
    enabled = get_enabled_platforms({})

    assert all(platform in PLATFORMS for platform in enabled)
    assert all(platform in PLATFORMS for platform in EXPERIMENTAL_PLATFORMS)
    assert not set(EXPERIMENTAL_PLATFORMS).intersection(enabled)
    assert set(EXPERIMENTAL_PLATFORMS).issubset(
        get_enabled_platforms({CONF_EXPERIMENTAL_PLATFORMS: True})
    )


def test_coordinator_scan_interval_reads_entry_options(hass: HomeAssistant) -> None:
    """coordinator 必须从 entry.options 读取轮询间隔."""
    coordinator = YeelightProCoordinator(
        hass=hass,
        client=AsyncMock(spec=YeelightProClient),
        house_id=12345,
        options={
            CONF_SCAN_INTERVAL: 45,
            CONF_DEBUG_MODE: True,
            CONF_HIDE_UNKNOWN_ENTITIES: False,
        },
    )

    assert coordinator.update_interval.total_seconds() == 45
    assert coordinator.scan_interval == 45
    assert coordinator.debug_mode is True
    assert coordinator.hide_unknown_entities is False
