"""Runtime options update tests for Yeelight Pro."""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.const import (
    CONF_CONNECTION_MODE,
    CONF_DEBUG_MODE,
    CONF_DEVICE_IMPORT_FILTER,
    CONF_HIDE_UNKNOWN_ENTITIES,
    CONF_LIVE_UPDATES,
    CONF_LOCAL_GATEWAY_CONTROL,
    CONF_LOCAL_GATEWAY_HOST,
    CONF_LOCAL_GATEWAY_PORT,
    CONF_PRIVATE_DOMAIN,
    CONF_PRIVATE_PUSH_DOMAIN,
    CONF_SCAN_INTERVAL,
    CONF_TOPOLOGY_CHANGE_REPAIRS,
    CONNECTION_MODE_PRIVATE,
    DEFAULT_LIVE_UPDATES,
    DEFAULT_LOCAL_GATEWAY_CONTROL,
    DEFAULT_LOCAL_GATEWAY_HOST,
    DEFAULT_LOCAL_GATEWAY_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PLATFORMS,
    get_enabled_platforms,
)
from custom_components.yeelight_pro.core.client import YeelightProClient
from custom_components.yeelight_pro.core.coordinator import YeelightProCoordinator
from custom_components.yeelight_pro.runtime_options import async_options_updated


def _runtime_coordinator(
    *,
    apply_options: Any,
) -> SimpleNamespace:
    """Build a coordinator-like runtime options target."""
    return SimpleNamespace(
        options={
            CONF_SCAN_INTERVAL: 30,
            CONF_DEBUG_MODE: False,
            CONF_HIDE_UNKNOWN_ENTITIES: True,
            CONF_TOPOLOGY_CHANGE_REPAIRS: True,
            CONF_LIVE_UPDATES: DEFAULT_LIVE_UPDATES,
            CONF_LOCAL_GATEWAY_CONTROL: DEFAULT_LOCAL_GATEWAY_CONTROL,
            CONF_LOCAL_GATEWAY_HOST: DEFAULT_LOCAL_GATEWAY_HOST,
            CONF_LOCAL_GATEWAY_PORT: DEFAULT_LOCAL_GATEWAY_PORT,
        },
        apply_options=apply_options,
    )


def _install_runtime(
    hass: HomeAssistant,
    entry,
    coordinator: SimpleNamespace,
) -> None:
    """Install a minimal loaded runtime entry."""
    hass.data[DOMAIN] = {
        entry.entry_id: {
            "coordinator": coordinator,
            "entry": entry,
            "entry_data": dict(entry.data),
        }
    }


def test_enabled_platforms_match_supported_platforms() -> None:
    """平台加载集合只来自当前受支持平台列表."""
    enabled = get_enabled_platforms({})

    assert enabled == PLATFORMS
    assert "vacuum" not in enabled
    assert get_enabled_platforms({"experimental_platforms": True}) == PLATFORMS


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


@pytest.mark.asyncio
async def test_options_update_applies_runtime_options_without_reload(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """纯运行时 options 更新应原地生效，避免不必要的 entry reload."""
    applied_options: dict[str, Any] | None = None

    def _apply_options(options: dict[str, Any]) -> None:
        nonlocal applied_options
        applied_options = dict(options)
        coordinator.options = dict(options)

    coordinator = _runtime_coordinator(apply_options=_apply_options)
    _install_runtime(hass, mock_config_entry, coordinator)
    mock_config_entry.options = {
        CONF_SCAN_INTERVAL: 45,
        CONF_DEBUG_MODE: True,
        CONF_HIDE_UNKNOWN_ENTITIES: True,
        CONF_TOPOLOGY_CHANGE_REPAIRS: True,
    }
    hass.config_entries.async_reload = AsyncMock()

    await async_options_updated(hass, mock_config_entry)

    hass.config_entries.async_reload.assert_not_awaited()
    assert applied_options == {
        **mock_config_entry.options,
        CONF_LIVE_UPDATES: DEFAULT_LIVE_UPDATES,
        CONF_LOCAL_GATEWAY_CONTROL: DEFAULT_LOCAL_GATEWAY_CONTROL,
        CONF_LOCAL_GATEWAY_HOST: DEFAULT_LOCAL_GATEWAY_HOST,
        CONF_LOCAL_GATEWAY_PORT: DEFAULT_LOCAL_GATEWAY_PORT,
    }
    assert hass.data[DOMAIN][mock_config_entry.entry_id]["entry"] is mock_config_entry


@pytest.mark.asyncio
async def test_options_update_reloads_when_entity_projection_changes(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """影响平台或实体候选的 options 必须 reload，避免实体集合漂移."""
    coordinator = _runtime_coordinator(apply_options=MagicMock())
    _install_runtime(hass, mock_config_entry, coordinator)
    mock_config_entry.options = {
        CONF_SCAN_INTERVAL: 30,
        CONF_DEBUG_MODE: False,
        CONF_HIDE_UNKNOWN_ENTITIES: False,
        CONF_TOPOLOGY_CHANGE_REPAIRS: True,
    }
    hass.config_entries.async_reload = AsyncMock()

    await async_options_updated(hass, mock_config_entry)

    hass.config_entries.async_reload.assert_awaited_once_with(mock_config_entry.entry_id)
    coordinator.apply_options.assert_not_called()


@pytest.mark.parametrize(
    ("option_key", "changed_value"),
    [
        pytest.param(CONF_LIVE_UPDATES, False, id="live_updates_websocket"),
        pytest.param(CONF_LOCAL_GATEWAY_CONTROL, True, id="local_gateway_control"),
        pytest.param(CONF_LOCAL_GATEWAY_HOST, "192.168.1.20", id="local_gateway_host"),
        pytest.param(CONF_LOCAL_GATEWAY_PORT, 65444, id="local_gateway_port"),
    ],
)
@pytest.mark.asyncio
async def test_options_update_reloads_when_background_runtime_option_changes(
    hass: HomeAssistant,
    mock_config_entry,
    option_key: str,
    changed_value: Any,
) -> None:
    """WebSocket 和 LAN 后台 runtime 配置变化必须 reload entry."""
    coordinator = _runtime_coordinator(apply_options=MagicMock())
    _install_runtime(hass, mock_config_entry, coordinator)
    mock_config_entry.options = {
        **coordinator.options,
        option_key: changed_value,
    }
    hass.config_entries.async_reload = AsyncMock()

    await async_options_updated(hass, mock_config_entry)

    hass.config_entries.async_reload.assert_awaited_once_with(mock_config_entry.entry_id)
    coordinator.apply_options.assert_not_called()


@pytest.mark.asyncio
async def test_options_update_reloads_when_private_push_entry_data_changes(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """Private WebSocket endpoint data changes must rebuild the push transport."""
    mock_config_entry.data.update({
        CONF_CONNECTION_MODE: CONNECTION_MODE_PRIVATE,
        CONF_PRIVATE_DOMAIN: "http://api-test.yeedev.com",
        CONF_PRIVATE_PUSH_DOMAIN: "",
    })
    coordinator = _runtime_coordinator(apply_options=MagicMock())
    _install_runtime(hass, mock_config_entry, coordinator)
    mock_config_entry.data[CONF_PRIVATE_PUSH_DOMAIN] = "ws://ws-test.yeedev.com/ws"
    mock_config_entry.options = dict(coordinator.options)
    hass.config_entries.async_reload = AsyncMock()

    await async_options_updated(hass, mock_config_entry)

    hass.config_entries.async_reload.assert_awaited_once_with(mock_config_entry.entry_id)
    coordinator.apply_options.assert_not_called()


@pytest.mark.asyncio
async def test_options_update_reloads_when_device_import_filter_changes(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """设备导入过滤会影响实体集合，必须通过 reload 重新建候选."""
    coordinator = _runtime_coordinator(apply_options=MagicMock())
    _install_runtime(hass, mock_config_entry, coordinator)
    mock_config_entry.options = {
        CONF_SCAN_INTERVAL: 30,
        CONF_DEBUG_MODE: False,
        CONF_HIDE_UNKNOWN_ENTITIES: True,
        CONF_TOPOLOGY_CHANGE_REPAIRS: True,
        CONF_DEVICE_IMPORT_FILTER: {
            "enabled": True,
            "include": {"categories": ["light"]},
        },
    }
    hass.config_entries.async_reload = AsyncMock()

    await async_options_updated(hass, mock_config_entry)

    hass.config_entries.async_reload.assert_awaited_once_with(mock_config_entry.entry_id)
    coordinator.apply_options.assert_not_called()


@pytest.mark.asyncio
async def test_options_update_does_not_reload_for_equivalent_empty_device_filter(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """空过滤规则的表单残留不应触发实体集合 reload."""
    coordinator = _runtime_coordinator(apply_options=MagicMock())
    coordinator.options[CONF_DEVICE_IMPORT_FILTER] = {"enabled": False}
    _install_runtime(hass, mock_config_entry, coordinator)
    mock_config_entry.options = {
        CONF_SCAN_INTERVAL: 30,
        CONF_DEBUG_MODE: False,
        CONF_HIDE_UNKNOWN_ENTITIES: True,
        CONF_TOPOLOGY_CHANGE_REPAIRS: True,
        CONF_DEVICE_IMPORT_FILTER: {
            "enabled": True,
            "include": {},
            "exclude": {},
        },
    }
    hass.config_entries.async_reload = AsyncMock()

    await async_options_updated(hass, mock_config_entry)

    hass.config_entries.async_reload.assert_not_awaited()
    coordinator.apply_options.assert_called_once_with({
        CONF_SCAN_INTERVAL: 30,
        CONF_DEBUG_MODE: False,
        CONF_HIDE_UNKNOWN_ENTITIES: True,
        CONF_TOPOLOGY_CHANGE_REPAIRS: True,
        CONF_DEVICE_IMPORT_FILTER: {
            "enabled": False,
            "mode": "or",
            "include": {},
            "exclude": {},
        },
        CONF_LIVE_UPDATES: DEFAULT_LIVE_UPDATES,
        CONF_LOCAL_GATEWAY_CONTROL: DEFAULT_LOCAL_GATEWAY_CONTROL,
        CONF_LOCAL_GATEWAY_HOST: DEFAULT_LOCAL_GATEWAY_HOST,
        CONF_LOCAL_GATEWAY_PORT: DEFAULT_LOCAL_GATEWAY_PORT,
    })


@pytest.mark.asyncio
async def test_options_update_reloads_when_runtime_missing(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """缺失运行态时应回退 reload，保持 HA entry 状态自愈."""
    hass.data[DOMAIN] = {}
    hass.config_entries.async_reload = AsyncMock()

    await async_options_updated(hass, mock_config_entry)

    hass.config_entries.async_reload.assert_awaited_once_with(mock_config_entry.entry_id)


@pytest.mark.asyncio
async def test_options_update_clears_topology_repairs_when_disabled(
    hass: HomeAssistant,
    mock_config_entry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """关闭拓扑 Repairs 开关后应清理已有提示，并原地更新运行态."""
    coordinator = _runtime_coordinator(apply_options=MagicMock())
    _install_runtime(hass, mock_config_entry, coordinator)
    mock_config_entry.options = {
        CONF_HIDE_UNKNOWN_ENTITIES: True,
        CONF_TOPOLOGY_CHANGE_REPAIRS: False,
    }
    hass.config_entries.async_reload = AsyncMock()
    delete_issues = MagicMock()
    monkeypatch.setattr(
        "custom_components.yeelight_pro.runtime_options."
        "async_delete_topology_changed_issues",
        delete_issues,
    )

    await async_options_updated(hass, mock_config_entry)

    delete_issues.assert_called_once_with(hass, mock_config_entry)
    hass.config_entries.async_reload.assert_not_awaited()
    coordinator.apply_options.assert_called_once()
    applied = coordinator.apply_options.call_args.args[0]
    assert applied[CONF_TOPOLOGY_CHANGE_REPAIRS] is False
    assert applied[CONF_SCAN_INTERVAL] == DEFAULT_SCAN_INTERVAL
    assert applied[CONF_DEBUG_MODE] is False


@pytest.mark.asyncio
async def test_options_update_keeps_topology_repairs_when_enabled(
    hass: HomeAssistant,
    mock_config_entry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """保持拓扑 Repairs 开启时不应清理现有提示."""
    coordinator = _runtime_coordinator(apply_options=MagicMock())
    _install_runtime(hass, mock_config_entry, coordinator)
    mock_config_entry.options = {
        CONF_HIDE_UNKNOWN_ENTITIES: True,
        CONF_TOPOLOGY_CHANGE_REPAIRS: True,
    }
    hass.config_entries.async_reload = AsyncMock()
    delete_issues = MagicMock()
    monkeypatch.setattr(
        "custom_components.yeelight_pro.runtime_options."
        "async_delete_topology_changed_issues",
        delete_issues,
    )

    await async_options_updated(hass, mock_config_entry)

    delete_issues.assert_not_called()
    hass.config_entries.async_reload.assert_not_awaited()
    coordinator.apply_options.assert_called_once()
    applied = coordinator.apply_options.call_args.args[0]
    assert applied[CONF_TOPOLOGY_CHANGE_REPAIRS] is True
    assert applied[CONF_SCAN_INTERVAL] == DEFAULT_SCAN_INTERVAL
    assert applied[CONF_DEBUG_MODE] is False
