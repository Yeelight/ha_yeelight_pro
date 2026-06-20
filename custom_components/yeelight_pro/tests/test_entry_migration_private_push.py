"""Private deployment push endpoint entry-migration tests."""

from __future__ import annotations

from custom_components.yeelight_pro.const import (
    CONF_ACCESS_TOKEN,
    CONF_CLOUD_DOMAIN,
    CONF_CONNECTION_MODE,
    CONF_HOUSE_ID,
    CONF_LAN_GATEWAY_IP,
    CONF_PRIVATE_DOMAIN,
    CONF_PRIVATE_PUSH_DOMAIN,
    CONNECTION_MODE_LAN,
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
        CONF_PRIVATE_PUSH_DOMAIN: "192.168.1.202:7779",
        CONF_HOUSE_ID: "1",
    })

    assert data[CONF_PRIVATE_DOMAIN] == "https://api-dev.yeedev.com"
    assert data[CONF_PRIVATE_PUSH_DOMAIN] == "ws://192.168.1.202:7779/ws"


def test_normalize_entry_data_private_push_domain_accepts_legacy_alias() -> None:
    """旧别名中的私有 WebSocket endpoint 应迁移到当前字段。"""
    data = normalize_entry_data({
        CONF_CONNECTION_MODE: CONNECTION_MODE_PRIVATE,
        CONF_PRIVATE_DOMAIN: "https://api-dev.yeedev.com/apis/iot",
        "websocket_url": "ws://192.168.1.202:7779/ws",
        CONF_HOUSE_ID: "1",
    })

    assert data[CONF_PRIVATE_DOMAIN] == "https://api-dev.yeedev.com"
    assert data[CONF_PRIVATE_PUSH_DOMAIN] == "ws://192.168.1.202:7779/ws"


def test_normalize_entry_data_private_push_proxy_legacy_alias_is_dropped() -> None:
    """旧代理别名不再写入 entry，避免把用户引向错误排障方向."""
    data = normalize_entry_data({
        CONF_CONNECTION_MODE: CONNECTION_MODE_PRIVATE,
        CONF_PRIVATE_DOMAIN: "https://api-dev.yeedev.com/apis/iot",
        "websocketProxy": "http://host.docker.internal:7890",
        CONF_HOUSE_ID: "1",
    })

    assert data[CONF_PRIVATE_DOMAIN] == "https://api-dev.yeedev.com"
    assert "websocketProxy" not in data
    assert "private_push_proxy" not in data


def test_normalize_entry_data_lan_push_proxy_legacy_alias_is_dropped() -> None:
    """LAN entry 迁移同样不保留旧代理字段。"""
    data = normalize_entry_data({
        CONF_CONNECTION_MODE: CONNECTION_MODE_LAN,
        CONF_LAN_GATEWAY_IP: "192.168.0.10",
        "websocketProxy": "http://host.docker.internal:7890",
    })

    assert "websocketProxy" not in data
    assert "private_push_proxy" not in data


def test_normalize_entry_data_private_test_push_host_preserves_ws_path() -> None:
    """api-test 私有部署应迁移到符合事件通知文档的 /ws endpoint."""
    data = normalize_entry_data({
        CONF_CONNECTION_MODE: CONNECTION_MODE_PRIVATE,
        CONF_PRIVATE_DOMAIN: "http://api-test.yeedev.com",
        CONF_PRIVATE_PUSH_DOMAIN: "ws://192.168.0.89:7779",
        CONF_HOUSE_ID: "1",
    })

    assert data[CONF_PRIVATE_DOMAIN] == "http://api-test.yeedev.com"
    assert data[CONF_PRIVATE_PUSH_DOMAIN] == "ws://192.168.0.89:7779/ws"


def test_normalize_entry_data_repairs_known_private_push_cross_route() -> None:
    """已知内部私有环境不能保留另一个环境的 WebSocket endpoint."""
    data = normalize_entry_data({
        CONF_CONNECTION_MODE: CONNECTION_MODE_PRIVATE,
        CONF_PRIVATE_DOMAIN: "http://api-dev.yeedev.com",
        CONF_PRIVATE_PUSH_DOMAIN: "ws://192.168.0.89:7779/ws",
        CONF_HOUSE_ID: "1",
    })

    assert data[CONF_PRIVATE_DOMAIN] == "http://api-dev.yeedev.com"
    assert data[CONF_PRIVATE_PUSH_DOMAIN] == "ws://192.168.1.202:7779/ws"


def test_normalize_entry_data_preserves_custom_private_push_override() -> None:
    """普通私有部署继续保留用户独立填写的 WebSocket endpoint."""
    data = normalize_entry_data({
        CONF_CONNECTION_MODE: CONNECTION_MODE_PRIVATE,
        CONF_PRIVATE_DOMAIN: "https://private.example",
        CONF_PRIVATE_PUSH_DOMAIN: "ws://192.168.8.9:7779",
        CONF_HOUSE_ID: "1",
    })

    assert data[CONF_PRIVATE_DOMAIN] == "https://private.example"
    assert data[CONF_PRIVATE_PUSH_DOMAIN] == "ws://192.168.8.9:7779/ws"
