"""Config-entry setup runtime fallback tests."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from custom_components.yeelight_pro.const import (
    CONF_CONNECTION_MODE,
    CONF_LAN_GATEWAY_IP,
    CONF_LAN_GATEWAY_PORT,
    CONF_LAN_GATEWAY_PRODUCT_ID,
    CONF_LIVE_UPDATES,
    CONF_LOCAL_GATEWAY_CONTROL,
    CONF_LOCAL_GATEWAY_HOST,
    CONNECTION_MODE_LAN,
    DOMAIN,
    LAN_GATEWAY_PRODUCT_ID_WIFI_PANEL,
)
from custom_components.yeelight_pro.lan_runtime_endpoints import LAN_ENDPOINT_WIFI_PANEL

from .config_entry_lifecycle_helpers import (
    make_client,
    make_config_entry,
    make_setup_coordinator,
    register_config_entry,
)


@pytest.mark.asyncio
async def test_setup_entry_keeps_cloud_runtime_when_lan_start_fails(
    hass: HomeAssistant,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """本地网关启动失败时，云端轮询和控制 fallback 仍应可用."""
    hass.data.setdefault(DOMAIN, {})
    entry = make_config_entry()
    registered_entry = register_config_entry(hass, entry)
    registered_entry.mock_state(hass, ConfigEntryState.SETUP_IN_PROGRESS)
    entry.options = {
        CONF_LIVE_UPDATES: True,
        CONF_LOCAL_GATEWAY_CONTROL: True,
        CONF_LOCAL_GATEWAY_HOST: "192.168.1.20",
    }
    client = make_client()
    push_manager = AsyncMock()
    push_manager.async_stop = AsyncMock()
    client.disconnect = AsyncMock()

    with patch(
        "custom_components.yeelight_pro.YeelightProClient",
        return_value=client,
    ), patch(
        "custom_components.yeelight_pro.YeelightProCoordinator",
    ) as coordinator_class, patch(
        "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
        new_callable=AsyncMock,
    ) as forward_platforms, patch(
        "custom_components.yeelight_pro.async_start_live_runtime",
        AsyncMock(return_value=push_manager),
    ), patch(
        "custom_components.yeelight_pro.entry_setup.async_start_lan_runtime",
        AsyncMock(side_effect=OSError("gateway-secret")),
    ):
        coordinator = make_setup_coordinator()
        coordinator_class.return_value = coordinator

        from custom_components.yeelight_pro import async_setup_entry

        assert await async_setup_entry(hass, entry) is True

    push_manager.async_stop.assert_not_awaited()
    client.disconnect.assert_not_awaited()
    forward_platforms.assert_awaited_once()
    runtime_data = hass.data[DOMAIN][entry.entry_id]
    assert runtime_data["push_manager"] is push_manager
    assert runtime_data["lan_runtime"].health.as_dict() == {
        "running": False,
        "connected": False,
        "sent_count": 0,
        "received_count": 0,
        "last_error_type": "OSError",
    }
    coordinator.set_lan_runtime.assert_called_once_with(None)
    assert "OSError" in caplog.text
    assert "gateway-secret" not in caplog.text


@pytest.mark.asyncio
async def test_setup_entry_keeps_polling_when_live_runtime_initial_connect_fails(
    hass: HomeAssistant,
) -> None:
    """WebSocket 初始网络失败不能阻断集成回退到轮询运行."""
    hass.data.setdefault(DOMAIN, {})
    entry = make_config_entry()
    registered_entry = register_config_entry(hass, entry)
    registered_entry.mock_state(hass, ConfigEntryState.SETUP_IN_PROGRESS)
    entry.options = {CONF_LIVE_UPDATES: True}
    push_manager = MagicMock()
    push_manager.health.as_dict.return_value = {
        "running": True,
        "started_count": 1,
        "stopped_count": 0,
        "handled_payloads": 0,
        "last_error_type": "OSError",
    }

    with patch(
        "custom_components.yeelight_pro.YeelightProClient",
        return_value=make_client(),
    ), patch(
        "custom_components.yeelight_pro.YeelightProCoordinator",
    ) as coordinator_class, patch(
        "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
        new_callable=AsyncMock,
    ) as forward_platforms, patch(
        "custom_components.yeelight_pro.async_start_live_runtime",
        AsyncMock(return_value=push_manager),
    ):
        coordinator_class.return_value = make_setup_coordinator()

        from custom_components.yeelight_pro import async_setup_entry

        assert await async_setup_entry(hass, entry) is True

    forward_platforms.assert_awaited_once()
    assert hass.data[DOMAIN][entry.entry_id]["push_manager"] is push_manager


@pytest.mark.asyncio
async def test_lan_entry_waits_for_property_ready_without_fixed_sleep(
    hass: HomeAssistant,
) -> None:
    """LAN-only setup 收到属性同步后应立即继续，不再固定 sleep(1)。"""
    hass.data.setdefault(DOMAIN, {})
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "lan_entry"
    entry.domain = DOMAIN
    entry.data = {
        CONF_CONNECTION_MODE: CONNECTION_MODE_LAN,
        CONF_LAN_GATEWAY_IP: "192.168.1.20",
        CONF_LAN_GATEWAY_PORT: 65443,
    }
    entry.options = {}
    entry.async_on_unload = MagicMock()
    entry.add_update_listener = MagicMock(return_value=MagicMock())
    registered_entry = register_config_entry(hass, entry)
    registered_entry.mock_state(hass, ConfigEntryState.SETUP_IN_PROGRESS)
    runtime_holder: dict[str, Any] = {}

    class FakeRuntime:
        def __init__(self, *, host: str, port: int, endpoint_kind: str) -> None:
            self.host = host
            self.port = port
            self.endpoint_kind = endpoint_kind
            self.callback = None
            runtime_holder["runtime"] = self

        async def async_start(self, callback) -> None:
            self.callback = callback

        async def async_get_topology(self) -> None:
            assert self.callback is not None
            await self.callback(
                {
                    "method": "gateway_post.topology",
                    "nodes": [{"id": 67890, "nt": 2, "type": 3, "name": "客厅灯"}],
                }
            )
            await self.callback(
                {
                    "method": "gateway_post.prop",
                    "nodes": [{"id": 67890, "nt": 2, "params": {"p": True}}],
                }
            )

    original_sleep = asyncio.sleep

    async def _forbid_fixed_sleep(delay: float) -> None:
        if delay == 1:
            raise AssertionError(f"unexpected fixed sleep: {delay}")
        await original_sleep(0)

    with patch(
        "custom_components.yeelight_pro.lan_runtime.LanGatewayRuntime",
        FakeRuntime,
    ), patch(
        "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
        new_callable=AsyncMock,
    ), patch(
        "custom_components.yeelight_pro.entry_setup.async_sync_gateway_devices",
        AsyncMock(),
    ), patch(
        "custom_components.yeelight_pro.entry_setup.async_reconcile_entity_registry",
        AsyncMock(return_value=set()),
    ), patch.object(
        asyncio,
        "sleep",
        _forbid_fixed_sleep,
    ):
        from custom_components.yeelight_pro import async_setup_entry

        assert await async_setup_entry(hass, entry) is True

    runtime = runtime_holder["runtime"]
    assert runtime.host == "192.168.1.20"
    assert hass.data[DOMAIN][entry.entry_id]["lan_runtime"] is runtime
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    assert coordinator.config_entry.entry_id == entry.entry_id
    await coordinator.async_shutdown()


@pytest.mark.asyncio
async def test_lan_entry_start_failure_raises_not_ready_and_cleans_runtime(
    hass: HomeAssistant,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """LAN-only 初始 TCP 启动失败不能留下已加载但不可用的 entry。"""
    hass.data.setdefault(DOMAIN, {})
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "lan_start_failure"
    entry.domain = DOMAIN
    entry.data = {
        CONF_CONNECTION_MODE: CONNECTION_MODE_LAN,
        CONF_LAN_GATEWAY_IP: "192.168.1.20",
        CONF_LAN_GATEWAY_PORT: 65443,
    }
    entry.options = {}
    entry.async_on_unload = MagicMock()
    entry.add_update_listener = MagicMock(return_value=MagicMock())
    registered_entry = register_config_entry(hass, entry)
    registered_entry.mock_state(hass, ConfigEntryState.SETUP_IN_PROGRESS)

    class FailingRuntime:
        def __init__(self, *, host: str, port: int, endpoint_kind: str) -> None:
            self.host = host
            self.port = port
            self.endpoint_kind = endpoint_kind

        async def async_start(self, callback) -> None:
            raise OSError("192.168.1.20 token-secret gateway-secret")

    with patch(
        "custom_components.yeelight_pro.lan_runtime.LanGatewayRuntime",
        FailingRuntime,
    ):
        from custom_components.yeelight_pro import async_setup_entry

        with pytest.raises(ConfigEntryNotReady, match="OSError"):
            await async_setup_entry(hass, entry)

    assert entry.entry_id not in hass.data[DOMAIN]
    assert "OSError" in caplog.text
    assert "192.168.1.20" not in caplog.text
    assert "token-secret" not in caplog.text
    assert "gateway-secret" not in caplog.text


@pytest.mark.asyncio
async def test_lan_entry_uses_saved_wifi_panel_endpoint_kind(
    hass: HomeAssistant,
) -> None:
    """LAN-only setup 必须使用 entry 保存的 pid=2 来选择全面屏方法族。"""
    hass.data.setdefault(DOMAIN, {})
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "lan_wifi_panel"
    entry.domain = DOMAIN
    entry.data = {
        CONF_CONNECTION_MODE: CONNECTION_MODE_LAN,
        CONF_LAN_GATEWAY_IP: "192.168.1.21",
        CONF_LAN_GATEWAY_PORT: 65443,
        CONF_LAN_GATEWAY_PRODUCT_ID: LAN_GATEWAY_PRODUCT_ID_WIFI_PANEL,
    }
    entry.options = {}
    entry.async_on_unload = MagicMock()
    entry.add_update_listener = MagicMock(return_value=MagicMock())
    registered_entry = register_config_entry(hass, entry)
    registered_entry.mock_state(hass, ConfigEntryState.SETUP_IN_PROGRESS)
    runtime_holder: dict[str, Any] = {}

    class FakeRuntime:
        def __init__(self, *, host: str, port: int, endpoint_kind: str) -> None:
            self.host = host
            self.port = port
            self.endpoint_kind = endpoint_kind
            self.callback = None
            runtime_holder["runtime"] = self

        async def async_start(self, callback) -> None:
            self.callback = callback

        async def async_get_topology(self) -> None:
            assert self.callback is not None
            await self.callback(
                {
                    "method": "getway_post.topology",
                    "nodes": [{"id": 67891, "nt": 2, "type": 7, "name": "全面屏"}],
                }
            )

    with patch(
        "custom_components.yeelight_pro.lan_runtime.LanGatewayRuntime",
        FakeRuntime,
    ), patch(
        "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
        new_callable=AsyncMock,
    ), patch(
        "custom_components.yeelight_pro.entry_setup.async_sync_gateway_devices",
        AsyncMock(),
    ), patch(
        "custom_components.yeelight_pro.entry_setup.async_reconcile_entity_registry",
        AsyncMock(return_value=set()),
    ):
        from custom_components.yeelight_pro import async_setup_entry

        assert await async_setup_entry(hass, entry) is True

    runtime = runtime_holder["runtime"]
    assert runtime.endpoint_kind == LAN_ENDPOINT_WIFI_PANEL
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    await coordinator.async_shutdown()


@pytest.mark.asyncio
async def test_lan_entry_cleans_runtime_when_platform_forward_fails(
    hass: HomeAssistant,
) -> None:
    """LAN-only 平台加载失败时应关闭 TCP runtime 并清除 runtime data."""
    hass.data.setdefault(DOMAIN, {})
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "lan_forward_failure"
    entry.domain = DOMAIN
    entry.data = {
        CONF_CONNECTION_MODE: CONNECTION_MODE_LAN,
        CONF_LAN_GATEWAY_IP: "192.168.1.20",
        CONF_LAN_GATEWAY_PORT: 65443,
    }
    entry.options = {}
    entry.async_on_unload = MagicMock()
    entry.add_update_listener = MagicMock(return_value=MagicMock())
    registered_entry = register_config_entry(hass, entry)
    registered_entry.mock_state(hass, ConfigEntryState.SETUP_IN_PROGRESS)
    runtime_holder: dict[str, Any] = {}

    class FakeRuntime:
        def __init__(self, *, host: str, port: int, endpoint_kind: str) -> None:
            self.host = host
            self.port = port
            self.endpoint_kind = endpoint_kind
            self.callback = None
            self.async_stop = AsyncMock()
            runtime_holder["runtime"] = self

        async def async_start(self, callback) -> None:
            self.callback = callback

        async def async_get_topology(self) -> None:
            assert self.callback is not None
            await self.callback(
                {
                    "method": "gateway_post.topology",
                    "nodes": [{"id": 67890, "nt": 2, "type": 3}],
                }
            )

    with patch(
        "custom_components.yeelight_pro.lan_runtime.LanGatewayRuntime",
        FakeRuntime,
    ), patch(
        "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
        AsyncMock(side_effect=RuntimeError("platform failed")),
    ), patch(
        "custom_components.yeelight_pro.entry_setup.async_sync_gateway_devices",
        AsyncMock(),
    ), patch(
        "custom_components.yeelight_pro.entry_setup.async_reconcile_entity_registry",
        AsyncMock(return_value=set()),
    ):
        from custom_components.yeelight_pro import async_setup_entry

        with pytest.raises(RuntimeError, match="platform failed"):
            await async_setup_entry(hass, entry)

    runtime_holder["runtime"].async_stop.assert_awaited_once()
    assert entry.entry_id not in hass.data[DOMAIN]
