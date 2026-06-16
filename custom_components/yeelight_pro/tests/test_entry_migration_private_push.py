"""Private deployment push endpoint entry-migration tests."""

from __future__ import annotations

from custom_components.yeelight_pro.const import (
    CONF_ACCESS_TOKEN,
    CONF_CLOUD_DOMAIN,
    CONF_CONNECTION_MODE,
    CONF_HOUSE_ID,
    CONF_PRIVATE_DOMAIN,
    CONF_PRIVATE_PUSH_DOMAIN,
    CONNECTION_MODE_PRIVATE,
    DEFAULT_CLOUD_DOMAIN,
    DEFAULT_PRIVATE_DOMAIN,
)
from custom_components.yeelight_pro.entry_migration import (
    config_entry_unique_id,
    normalize_entry_data,
)


def test_normalize_entry_data_private_domain_is_deployment_root_url() -> None:
    """私有部署 entry 应存根 URL，兼容旧 /apis/iot 和 /apis/account 前缀."""
    iot = normalize_entry_data({
        CONF_CONNECTION_MODE: CONNECTION_MODE_PRIVATE,
        CONF_PRIVATE_DOMAIN: "http://private.example/apis/iot",
        CONF_HOUSE_ID: "1",
    })
    account = normalize_entry_data({
        CONF_CONNECTION_MODE: CONNECTION_MODE_PRIVATE,
        CONF_PRIVATE_DOMAIN: "https://private.example/apis/account/",
        CONF_HOUSE_ID: "1",
    })

    assert iot[CONF_PRIVATE_DOMAIN] == "http://private.example"
    assert account[CONF_PRIVATE_DOMAIN] == "https://private.example"
    assert config_entry_unique_id(iot) == "private:http://private.example:1"


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
    assert cloud[CONF_PRIVATE_PUSH_DOMAIN] == ""
    assert private[CONF_CLOUD_DOMAIN] == ""
    assert private[CONF_PRIVATE_DOMAIN] == DEFAULT_PRIVATE_DOMAIN
    assert private[CONF_PRIVATE_PUSH_DOMAIN] == ""


def test_normalize_entry_data_private_push_domain_is_independent_endpoint() -> None:
    """私有部署 WebSocket endpoint 独立于 Open API 根 URL 保存。"""
    data = normalize_entry_data({
        CONF_CONNECTION_MODE: CONNECTION_MODE_PRIVATE,
        CONF_PRIVATE_DOMAIN: "api-dev.yeedev.com",
        CONF_PRIVATE_PUSH_DOMAIN: "ws-dev.yeedev.com",
        CONF_HOUSE_ID: "1",
    })

    assert data[CONF_PRIVATE_DOMAIN] == "https://api-dev.yeedev.com"
    assert data[CONF_PRIVATE_PUSH_DOMAIN] == "wss://ws-dev.yeedev.com/ws"


def test_normalize_entry_data_private_push_domain_accepts_legacy_alias() -> None:
    """旧别名中的私有 WebSocket endpoint 应迁移到当前字段。"""
    data = normalize_entry_data({
        CONF_CONNECTION_MODE: CONNECTION_MODE_PRIVATE,
        CONF_PRIVATE_DOMAIN: "https://api-dev.yeedev.com/apis/iot",
        "websocket_url": "wss://ws-dev.yeedev.com/ws",
        CONF_HOUSE_ID: "1",
    })

    assert data[CONF_PRIVATE_DOMAIN] == "https://api-dev.yeedev.com"
    assert data[CONF_PRIVATE_PUSH_DOMAIN] == "wss://ws-dev.yeedev.com/ws"
