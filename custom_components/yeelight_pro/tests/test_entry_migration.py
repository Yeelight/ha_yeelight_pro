"""Config entry migration tests."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro import async_migrate_entry
from custom_components.yeelight_pro.const import (
    CONF_ACCESS_TOKEN,
    CONF_ACCOUNT_USER_ID,
    CONF_ACCOUNT_USERNAME,
    CONF_CLOUD_DOMAIN,
    CONF_CLOUD_REGION,
    CONF_CONNECTION_MODE,
    CONF_DEBUG_MODE,
    CONF_EXPERIMENTAL_PLATFORMS,
    CONF_HIDE_UNKNOWN_ENTITIES,
    CONF_HOUSE_ID,
    CONF_LIVE_UPDATES,
    CONF_LOCAL_GATEWAY_CONTROL,
    CONF_LOCAL_GATEWAY_HOST,
    CONF_LOCAL_GATEWAY_PORT,
    CONF_OPEN_API_CLIENT_ID,
    CONF_PRIVATE_DOMAIN,
    CONF_REFRESH_TOKEN,
    CONF_SCAN_INTERVAL,
    CONF_SCAN_LOGIN_DEVICE,
    CONF_TOKEN_EXPIRES_IN,
    CONF_TOKEN_TYPE,
    CONF_TOPOLOGY_CHANGE_REPAIRS,
    CONNECTION_MODE_CLOUD,
    CONNECTION_MODE_PRIVATE,
    DEFAULT_CLOUD_DOMAIN,
    DEFAULT_DEBUG_MODE,
    DEFAULT_EXPERIMENTAL_PLATFORMS,
    DEFAULT_HIDE_UNKNOWN_ENTITIES,
    DEFAULT_LIVE_UPDATES,
    DEFAULT_LOCAL_GATEWAY_CONTROL,
    DEFAULT_LOCAL_GATEWAY_HOST,
    DEFAULT_LOCAL_GATEWAY_PORT,
    DEFAULT_PRIVATE_DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TOPOLOGY_CHANGE_REPAIRS,
)
from custom_components.yeelight_pro.entry_migration import (
    ENTRY_MINOR_VERSION,
    ENTRY_VERSION,
    config_entry_unique_id,
    normalize_entry_data,
)


def _entry(
    *,
    data: dict,
    options: object | None = None,
    version: int = 1,
    minor_version: int = 0,
    unique_id: str | None = None,
) -> MagicMock:
    """Build a config entry test double."""
    entry = MagicMock(spec=ConfigEntry)
    entry.data = data
    entry.options = options
    entry.version = version
    entry.minor_version = minor_version
    entry.entry_id = "entry-1"
    entry.unique_id = unique_id
    return entry


def _expected_default_options() -> dict[str, object]:
    """Return current default options shape."""
    return {
        CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
        CONF_DEBUG_MODE: DEFAULT_DEBUG_MODE,
        CONF_EXPERIMENTAL_PLATFORMS: DEFAULT_EXPERIMENTAL_PLATFORMS,
        CONF_HIDE_UNKNOWN_ENTITIES: DEFAULT_HIDE_UNKNOWN_ENTITIES,
        CONF_TOPOLOGY_CHANGE_REPAIRS: DEFAULT_TOPOLOGY_CHANGE_REPAIRS,
        CONF_LIVE_UPDATES: DEFAULT_LIVE_UPDATES,
        CONF_LOCAL_GATEWAY_CONTROL: DEFAULT_LOCAL_GATEWAY_CONTROL,
        CONF_LOCAL_GATEWAY_HOST: DEFAULT_LOCAL_GATEWAY_HOST,
        CONF_LOCAL_GATEWAY_PORT: DEFAULT_LOCAL_GATEWAY_PORT,
    }


@pytest.mark.asyncio
async def test_migrate_cloud_entry_aliases_and_option_defaults(
    hass: HomeAssistant,
) -> None:
    """旧云端 entry 字段别名应迁移为当前 data/options 形状."""
    entry = _entry(
        data={
            "domain": "https://api.yeelight.com/apis/iot",
            "accessToken": "token-1",
            "refreshToken": "refresh-1",
            "houseId": "429392",
            "region": "CN",
            "username": "user-1",
        },
        options={
            "future_option": "keep",
            CONF_SCAN_INTERVAL: "45",
            CONF_DEBUG_MODE: "1",
            CONF_EXPERIMENTAL_PLATFORMS: "false",
            CONF_HIDE_UNKNOWN_ENTITIES: "0",
            CONF_TOPOLOGY_CHANGE_REPAIRS: "off",
        },
        version=1,
        minor_version=1,
        unique_id="yeelight_pro_cloud",
    )
    entry.title = "Yeelight Pro Cloud"
    hass.config_entries.async_update_entry = MagicMock()

    assert await async_migrate_entry(hass, entry) is True

    hass.config_entries.async_update_entry.assert_called_once_with(
        entry,
        data={
            "domain": "https://api.yeelight.com/apis/iot",
            "accessToken": "token-1",
            "refreshToken": "refresh-1",
            "houseId": "429392",
            "region": "CN",
            "username": "user-1",
            CONF_CONNECTION_MODE: CONNECTION_MODE_CLOUD,
            CONF_CLOUD_DOMAIN: "https://api.yeelight.com/apis/iot",
            CONF_PRIVATE_DOMAIN: "",
            CONF_ACCESS_TOKEN: "token-1",
            CONF_REFRESH_TOKEN: "refresh-1",
            CONF_TOKEN_EXPIRES_IN: None,
            CONF_TOKEN_TYPE: "",
            CONF_HOUSE_ID: 429392,
            CONF_CLOUD_REGION: "cn",
            CONF_OPEN_API_CLIENT_ID: "",
            CONF_ACCOUNT_USER_ID: None,
            CONF_ACCOUNT_USERNAME: "user-1",
            CONF_SCAN_LOGIN_DEVICE: "",
        },
        options={
            "future_option": "keep",
            CONF_SCAN_INTERVAL: 45,
            CONF_DEBUG_MODE: True,
            CONF_EXPERIMENTAL_PLATFORMS: False,
            CONF_HIDE_UNKNOWN_ENTITIES: False,
            CONF_TOPOLOGY_CHANGE_REPAIRS: False,
            CONF_LIVE_UPDATES: DEFAULT_LIVE_UPDATES,
            CONF_LOCAL_GATEWAY_CONTROL: DEFAULT_LOCAL_GATEWAY_CONTROL,
            CONF_LOCAL_GATEWAY_HOST: DEFAULT_LOCAL_GATEWAY_HOST,
            CONF_LOCAL_GATEWAY_PORT: DEFAULT_LOCAL_GATEWAY_PORT,
        },
        title="Yeelight Pro Cloud (user-1 · CN · House 429392)",
        unique_id="cloud:cn:user-1:429392",
        version=ENTRY_VERSION,
        minor_version=ENTRY_MINOR_VERSION,
    )


@pytest.mark.asyncio
async def test_migrate_private_entry_fills_domains_and_default_options(
    hass: HomeAssistant,
) -> None:
    """私有部署旧 entry 应保留 server 字段并补齐当前 domain keys."""
    entry = _entry(
        data={
            CONF_CONNECTION_MODE: CONNECTION_MODE_PRIVATE,
            "server": "10.0.0.10:8080",
            CONF_ACCESS_TOKEN: "token-2",
            "home_id": "1001",
        },
        options=None,
    )
    entry.title = "Yeelight Pro Private"
    hass.config_entries.async_update_entry = MagicMock()

    assert await async_migrate_entry(hass, entry) is True

    update = hass.config_entries.async_update_entry.call_args.kwargs
    assert update["data"] == {
        CONF_CONNECTION_MODE: CONNECTION_MODE_PRIVATE,
        "server": "10.0.0.10:8080",
        CONF_ACCESS_TOKEN: "token-2",
        "home_id": "1001",
        CONF_CLOUD_DOMAIN: "",
        CONF_PRIVATE_DOMAIN: "10.0.0.10:8080",
        CONF_REFRESH_TOKEN: "",
        CONF_TOKEN_EXPIRES_IN: None,
        CONF_TOKEN_TYPE: "",
        CONF_HOUSE_ID: 1001,
        CONF_CLOUD_REGION: "cn",
        CONF_OPEN_API_CLIENT_ID: "",
        CONF_ACCOUNT_USER_ID: None,
        CONF_ACCOUNT_USERNAME: "",
        CONF_SCAN_LOGIN_DEVICE: "",
    }
    assert update["options"] == _expected_default_options()
    assert update["title"] == "Yeelight Pro Private (10.0.0.10:8080 · House 1001)"
    assert update["unique_id"] == "private:10.0.0.10:8080:1001"
    assert update["version"] == ENTRY_VERSION
    assert update["minor_version"] == ENTRY_MINOR_VERSION


@pytest.mark.asyncio
async def test_migrate_current_entry_is_noop(hass: HomeAssistant) -> None:
    """当前版本且 data/options 已归一时不应重复写 entry."""
    entry = _entry(
        data=normalize_entry_data({
            CONF_CONNECTION_MODE: CONNECTION_MODE_CLOUD,
            CONF_CLOUD_DOMAIN: DEFAULT_CLOUD_DOMAIN,
            CONF_PRIVATE_DOMAIN: "",
            CONF_ACCESS_TOKEN: "token-3",
            CONF_REFRESH_TOKEN: "",
            CONF_TOKEN_EXPIRES_IN: None,
            CONF_TOKEN_TYPE: "",
            CONF_HOUSE_ID: 429392,
            CONF_CLOUD_REGION: "cn",
            CONF_OPEN_API_CLIENT_ID: "",
            CONF_ACCOUNT_USER_ID: None,
            CONF_ACCOUNT_USERNAME: "",
            CONF_SCAN_LOGIN_DEVICE: "",
        }),
        options={
            CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
            CONF_DEBUG_MODE: DEFAULT_DEBUG_MODE,
            CONF_EXPERIMENTAL_PLATFORMS: DEFAULT_EXPERIMENTAL_PLATFORMS,
            CONF_HIDE_UNKNOWN_ENTITIES: DEFAULT_HIDE_UNKNOWN_ENTITIES,
            CONF_TOPOLOGY_CHANGE_REPAIRS: DEFAULT_TOPOLOGY_CHANGE_REPAIRS,
            CONF_LIVE_UPDATES: DEFAULT_LIVE_UPDATES,
            CONF_LOCAL_GATEWAY_CONTROL: DEFAULT_LOCAL_GATEWAY_CONTROL,
            CONF_LOCAL_GATEWAY_HOST: DEFAULT_LOCAL_GATEWAY_HOST,
            CONF_LOCAL_GATEWAY_PORT: DEFAULT_LOCAL_GATEWAY_PORT,
        },
        version=ENTRY_VERSION,
        minor_version=ENTRY_MINOR_VERSION,
        unique_id="cloud:cn:token-a2f2b0b588bcc84f:429392",
    )
    entry.title = "Yeelight Pro Cloud (CN · House 429392)"
    hass.config_entries.async_update_entry = MagicMock()

    assert await async_migrate_entry(hass, entry) is True

    hass.config_entries.async_update_entry.assert_not_called()


def test_normalize_entry_data_preserves_open_api_client_id_alias() -> None:
    """旧 Open API clientId 别名应迁移为当前运行时请求头字段."""
    data = normalize_entry_data({
        CONF_ACCESS_TOKEN: "token",
        CONF_HOUSE_ID: "1",
        "clientId": "client-1",
    })

    assert data[CONF_OPEN_API_CLIENT_ID] == "client-1"


def test_normalize_entry_data_detects_region_from_cloud_domain() -> None:
    """旧 entry 缺少 region 时应从多区域域名推导存储 key."""
    data = normalize_entry_data({
        CONF_CLOUD_DOMAIN: "https://api-de.yeelight.com/apis/iot",
        CONF_ACCESS_TOKEN: "token",
        CONF_HOUSE_ID: "1",
    })

    assert data[CONF_CLOUD_REGION] == "de"


def test_normalize_entry_data_uses_mode_defaults() -> None:
    """缺少 domain 字段时按连接模式补当前默认值."""
    cloud = normalize_entry_data({
        CONF_ACCESS_TOKEN: "token",
        CONF_HOUSE_ID: "1",
    })
    private = normalize_entry_data({
        CONF_CONNECTION_MODE: CONNECTION_MODE_PRIVATE,
        CONF_ACCESS_TOKEN: "token",
        CONF_HOUSE_ID: "1",
    })

    assert cloud[CONF_CLOUD_DOMAIN] == DEFAULT_CLOUD_DOMAIN
    assert cloud[CONF_PRIVATE_DOMAIN] == ""
    assert private[CONF_CLOUD_DOMAIN] == ""
    assert private[CONF_PRIVATE_DOMAIN] == DEFAULT_PRIVATE_DOMAIN


def test_config_entry_unique_id_separates_cloud_region_account_and_house() -> None:
    """云端 entry unique_id 必须同时隔离区域、账号和家庭."""
    first = config_entry_unique_id({
        CONF_CONNECTION_MODE: CONNECTION_MODE_CLOUD,
        CONF_CLOUD_REGION: "sg",
        CONF_ACCESS_TOKEN: "token-1",
        CONF_ACCOUNT_USER_ID: 122349,
        CONF_HOUSE_ID: 7,
    })
    second = config_entry_unique_id({
        CONF_CONNECTION_MODE: CONNECTION_MODE_CLOUD,
        CONF_CLOUD_REGION: "us",
        CONF_ACCESS_TOKEN: "token-1",
        CONF_ACCOUNT_USER_ID: 122349,
        CONF_HOUSE_ID: 7,
    })
    third = config_entry_unique_id({
        CONF_CONNECTION_MODE: CONNECTION_MODE_CLOUD,
        CONF_CLOUD_REGION: "sg",
        CONF_ACCESS_TOKEN: "token-2",
        CONF_ACCOUNT_USER_ID: 122350,
        CONF_HOUSE_ID: 7,
    })
    fourth = config_entry_unique_id({
        CONF_CONNECTION_MODE: CONNECTION_MODE_CLOUD,
        CONF_CLOUD_REGION: "sg",
        CONF_ACCESS_TOKEN: "token-1",
        CONF_ACCOUNT_USER_ID: 122349,
        CONF_HOUSE_ID: 8,
    })

    assert first == "cloud:sg:122349:7"
    assert len({first, second, third, fourth}) == 4


@pytest.mark.asyncio
async def test_migrate_legacy_cloud_entry_updates_region_account_unique_id(
    hass: HomeAssistant,
) -> None:
    """旧 cloud unique_id 应迁移为区域/账号/家庭隔离形态."""
    entry = _entry(
        data={
            CONF_CONNECTION_MODE: CONNECTION_MODE_CLOUD,
            CONF_CLOUD_REGION: "us",
            CONF_CLOUD_DOMAIN: "https://api-us.yeelight.com/apis/iot",
            CONF_ACCESS_TOKEN: "legacy-token",
            CONF_HOUSE_ID: 9,
            CONF_ACCOUNT_USER_ID: 122349,
        },
        options=_expected_default_options(),
        version=ENTRY_VERSION,
        minor_version=ENTRY_MINOR_VERSION,
        unique_id="yeelight_pro_cloud",
    )
    hass.config_entries.async_update_entry = MagicMock()

    assert await async_migrate_entry(hass, entry) is True

    update = hass.config_entries.async_update_entry.call_args.kwargs
    assert update["unique_id"] == "cloud:us:122349:9"
    assert update["title"] == "Yeelight Pro Cloud (UID 122349 · US · House 9)"
    assert update["minor_version"] == ENTRY_MINOR_VERSION


@pytest.mark.asyncio
async def test_migrate_current_data_updates_legacy_title(
    hass: HomeAssistant,
) -> None:
    """当前 data/options 但旧标题仍应迁移到账号/区域/家庭可辨识标题."""
    entry = _entry(
        data=normalize_entry_data({
            CONF_CONNECTION_MODE: CONNECTION_MODE_CLOUD,
            CONF_CLOUD_DOMAIN: DEFAULT_CLOUD_DOMAIN,
            CONF_PRIVATE_DOMAIN: "",
            CONF_ACCESS_TOKEN: "token-3",
            CONF_REFRESH_TOKEN: "",
            CONF_TOKEN_EXPIRES_IN: None,
            CONF_TOKEN_TYPE: "",
            CONF_HOUSE_ID: 429392,
            CONF_CLOUD_REGION: "cn",
            CONF_OPEN_API_CLIENT_ID: "",
            CONF_ACCOUNT_USER_ID: None,
            CONF_ACCOUNT_USERNAME: "",
            CONF_SCAN_LOGIN_DEVICE: "",
        }),
        options=_expected_default_options(),
        version=ENTRY_VERSION,
        minor_version=ENTRY_MINOR_VERSION,
        unique_id="cloud:cn:token-a2f2b0b588bcc84f:429392",
    )
    entry.title = "Yeelight Pro Cloud"
    hass.config_entries.async_update_entry = MagicMock()

    assert await async_migrate_entry(hass, entry) is True

    update = hass.config_entries.async_update_entry.call_args.kwargs
    assert update["title"] == "Yeelight Pro Cloud (CN · House 429392)"
    assert update["unique_id"] == "cloud:cn:token-a2f2b0b588bcc84f:429392"
