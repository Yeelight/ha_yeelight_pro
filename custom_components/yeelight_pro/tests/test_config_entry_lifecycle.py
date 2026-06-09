"""Config entry lifecycle tests."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.const import (
    CONF_CONNECTION_MODE,
    CONF_HOUSE_ID,
    CONF_LIVE_UPDATES,
    CONF_LOCAL_GATEWAY_CONTROL,
    CONF_LOCAL_GATEWAY_HOST,
    CONF_TOPOLOGY_CHANGE_REPAIRS,
    CONNECTION_MODE_CLOUD,
    DOMAIN,
)

from .config_entry_lifecycle_helpers import (
    make_client,
    make_config_entry,
    make_coordinator,
    make_setup_coordinator,
)


@pytest.fixture
def mock_config_entry() -> MagicMock:
    """Build a config entry test double."""
    return make_config_entry()


@pytest.fixture
def mock_client() -> AsyncMock:
    """Build a client test double."""
    return make_client()


@pytest.fixture
def mock_coordinator(hass: HomeAssistant, mock_client: AsyncMock) -> MagicMock:
    """Build a coordinator test double."""
    return make_coordinator(hass, mock_client)


@pytest.mark.asyncio
async def test_setup_entry(
    hass: HomeAssistant,
    mock_config_entry: MagicMock,
    mock_client: AsyncMock,
) -> None:
    """Integration setup should initialize runtime and forward platforms."""
    hass.data.setdefault(DOMAIN, {})

    with patch(
        "custom_components.yeelight_pro.YeelightProClient",
        return_value=mock_client,
    ), patch(
        "custom_components.yeelight_pro.YeelightProCoordinator",
    ) as coordinator_class, patch(
        "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
        new_callable=AsyncMock,
    ):
        coordinator_class.return_value = make_setup_coordinator()

        from custom_components.yeelight_pro import async_setup_entry

        assert await async_setup_entry(hass, mock_config_entry) is True


@pytest.mark.asyncio
async def test_setup_entry_normalizes_legacy_cloud_entry(
    hass: HomeAssistant,
    mock_client: AsyncMock,
) -> None:
    """Setup should tolerate legacy data if HA skipped migration."""
    hass.data.setdefault(DOMAIN, {})
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "legacy_entry"
    entry.domain = DOMAIN
    entry.data = {
        "domain": "https://api.yeelight.com/apis/iot",
        "accessToken": "legacy-token",
        "houseId": "429392",
    }
    entry.options = {}
    entry.async_on_unload = MagicMock()
    entry.add_update_listener = MagicMock(return_value=MagicMock())

    with patch(
        "custom_components.yeelight_pro.YeelightProClient",
        return_value=mock_client,
    ) as client_class, patch(
        "custom_components.yeelight_pro.YeelightProCoordinator",
    ) as coordinator_class, patch(
        "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
        new_callable=AsyncMock,
    ):
        coordinator_class.return_value = make_setup_coordinator()

        from custom_components.yeelight_pro import async_setup_entry

        assert await async_setup_entry(hass, entry) is True

    client_class.assert_called_once()
    assert client_class.call_args.kwargs["domain"] == "https://api.yeelight.com/apis/iot"
    assert client_class.call_args.kwargs["access_token"] == "legacy-token"
    assert client_class.call_args.kwargs["client_id"] == ""
    coordinator_class.assert_called_once()
    assert coordinator_class.call_args.kwargs["house_id"] == 429392


@pytest.mark.asyncio
async def test_setup_entry_passes_open_api_client_id_to_client(
    hass: HomeAssistant,
    mock_config_entry: MagicMock,
    mock_client: AsyncMock,
) -> None:
    """Setup 应把 OAuth 获取的 Open API clientId 传给 HTTP client."""
    hass.data.setdefault(DOMAIN, {})

    with patch(
        "custom_components.yeelight_pro.YeelightProClient",
        return_value=mock_client,
    ) as client_class, patch(
        "custom_components.yeelight_pro.YeelightProCoordinator",
    ) as coordinator_class, patch(
        "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
        new_callable=AsyncMock,
    ):
        coordinator_class.return_value = make_setup_coordinator()

        from custom_components.yeelight_pro import async_setup_entry

        assert await async_setup_entry(hass, mock_config_entry) is True

    client_class.assert_called_once()
    assert client_class.call_args.kwargs["client_id"] == "client-1"


@pytest.mark.asyncio
async def test_setup_entry_normalizes_legacy_open_api_client_id_alias(
    hass: HomeAssistant,
    mock_client: AsyncMock,
) -> None:
    """Setup 直接遇到旧 clientId 别名时也应传入运行时 client."""
    hass.data.setdefault(DOMAIN, {})
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "legacy_client_id_entry"
    entry.domain = DOMAIN
    entry.data = {
        CONF_CONNECTION_MODE: CONNECTION_MODE_CLOUD,
        CONF_ACCESS_TOKEN: "legacy-token",
        CONF_HOUSE_ID: 429392,
        "cloud_domain": "api.yeelight.com",
        "clientId": "client-from-alias",
    }
    entry.options = {}
    entry.async_on_unload = MagicMock()
    entry.add_update_listener = MagicMock(return_value=MagicMock())

    with patch(
        "custom_components.yeelight_pro.YeelightProClient",
        return_value=mock_client,
    ) as client_class, patch(
        "custom_components.yeelight_pro.YeelightProCoordinator",
    ) as coordinator_class, patch(
        "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
        new_callable=AsyncMock,
    ):
        coordinator_class.return_value = make_setup_coordinator()

        from custom_components.yeelight_pro import async_setup_entry

        assert await async_setup_entry(hass, entry) is True

    client_class.assert_called_once()
    assert client_class.call_args.kwargs["client_id"] == "client-from-alias"


@pytest.mark.asyncio
async def test_setup_entry_creates_repair_issue_on_topology_change(
    hass: HomeAssistant,
    mock_config_entry: MagicMock,
    mock_client: AsyncMock,
) -> None:
    """Topology changes should create one Repairs issue per generation."""
    hass.data.setdefault(DOMAIN, {})

    with patch(
        "custom_components.yeelight_pro.YeelightProClient",
        return_value=mock_client,
    ), patch(
        "custom_components.yeelight_pro.YeelightProCoordinator",
    ) as coordinator_class, patch(
        "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
        new_callable=AsyncMock,
    ), patch(
        "custom_components.yeelight_pro.async_create_topology_changed_issue",
    ) as create_issue:
        listener_holder = {}
        coordinator = make_setup_coordinator()
        coordinator.topology_generation = 1

        def _add_listener(listener):
            listener_holder["listener"] = listener
            return MagicMock()

        coordinator.async_add_listener = MagicMock(side_effect=_add_listener)
        coordinator_class.return_value = coordinator

        from custom_components.yeelight_pro import async_setup_entry

        assert await async_setup_entry(hass, mock_config_entry) is True
        listener_holder["listener"]()
        create_issue.assert_not_called()

        coordinator.topology_generation = 2
        listener_holder["listener"]()
        create_issue.assert_called_once_with(
            hass,
            mock_config_entry,
            coordinator,
            previous_generation=1,
        )

        listener_holder["listener"]()
        create_issue.assert_called_once()


@pytest.mark.asyncio
async def test_setup_entry_respects_disabled_topology_repairs_option(
    hass: HomeAssistant,
    mock_config_entry: MagicMock,
    mock_client: AsyncMock,
) -> None:
    """Disabled topology Repairs should still allow registry maintenance."""
    hass.data.setdefault(DOMAIN, {})
    mock_config_entry.options = {CONF_TOPOLOGY_CHANGE_REPAIRS: False}

    with patch(
        "custom_components.yeelight_pro.YeelightProClient",
        return_value=mock_client,
    ), patch(
        "custom_components.yeelight_pro.YeelightProCoordinator",
    ) as coordinator_class, patch(
        "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
        new_callable=AsyncMock,
    ), patch(
        "custom_components.yeelight_pro.async_create_topology_changed_issue",
    ) as create_issue:
        listener_holder = {}
        coordinator = make_setup_coordinator()
        coordinator.topology_generation = 1

        def _add_listener(listener):
            listener_holder["listener"] = listener
            return MagicMock()

        coordinator.async_add_listener = MagicMock(side_effect=_add_listener)
        coordinator_class.return_value = coordinator

        from custom_components.yeelight_pro import async_setup_entry

        assert await async_setup_entry(hass, mock_config_entry) is True
        coordinator.topology_generation = 2
        listener_holder["listener"]()

    create_issue.assert_not_called()


@pytest.mark.asyncio
async def test_setup_entry_cleans_optional_runtime_when_lan_start_fails(
    hass: HomeAssistant,
    mock_config_entry: MagicMock,
    mock_client: AsyncMock,
) -> None:
    """可选 live/LAN runtime 启动失败时应清理半加载资源."""
    hass.data.setdefault(DOMAIN, {})
    mock_config_entry.options = {
        CONF_LIVE_UPDATES: True,
        CONF_LOCAL_GATEWAY_CONTROL: True,
        CONF_LOCAL_GATEWAY_HOST: "192.168.1.20",
    }
    push_manager = AsyncMock()
    push_manager.async_stop = AsyncMock()
    mock_client.disconnect = AsyncMock()

    with patch(
        "custom_components.yeelight_pro.YeelightProClient",
        return_value=mock_client,
    ), patch(
        "custom_components.yeelight_pro.YeelightProCoordinator",
    ) as coordinator_class, patch(
        "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
        new_callable=AsyncMock,
    ) as forward_platforms, patch(
        "custom_components.yeelight_pro.async_start_live_runtime",
        AsyncMock(return_value=push_manager),
    ), patch(
        "custom_components.yeelight_pro.async_start_lan_runtime",
        AsyncMock(side_effect=OSError("gateway-secret")),
    ):
        coordinator_class.return_value = make_setup_coordinator()

        from custom_components.yeelight_pro import async_setup_entry

        with pytest.raises(OSError):
            await async_setup_entry(hass, mock_config_entry)

    push_manager.async_stop.assert_awaited_once()
    mock_client.disconnect.assert_awaited_once()
    forward_platforms.assert_not_awaited()
    assert mock_config_entry.entry_id not in hass.data[DOMAIN]
