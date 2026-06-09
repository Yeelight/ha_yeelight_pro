"""Config flow helper regression tests."""
from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from custom_components.yeelight_pro.config_flow_helpers import (
    cloud_oauth_authorization_url,
    merge_options,
    options_schema,
    visible_option_change_count,
)
from custom_components.yeelight_pro.const import (
    CONF_ANALYTICS_RETENTION_DAYS,
    CONF_ANALYTICS_RUNTIME,
    CONF_DEBUG_MODE,
    CONF_DEVICE_IMPORT_FILTER,
    CONF_DEVICE_IMPORT_FILTER_ENABLED,
    CONF_DEVICE_IMPORT_FILTER_EXCLUDE_CATEGORIES,
    CONF_DEVICE_IMPORT_FILTER_EXCLUDE_ROOMS,
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
    DEFAULT_ANALYTICS_RETENTION_DAYS,
    DEFAULT_ANALYTICS_RUNTIME,
    DEFAULT_LIVE_UPDATES,
    DEFAULT_LOCAL_GATEWAY_CONTROL,
    DEFAULT_LOCAL_GATEWAY_HOST,
    DEFAULT_LOCAL_GATEWAY_PORT,
    MAX_SCAN_INTERVAL,
)


def test_options_schema_normalizes_legacy_visible_defaults() -> None:
    """Options schema should display normalized defaults for legacy values."""
    schema = options_schema({
        CONF_SCAN_INTERVAL: "999",
        CONF_DEBUG_MODE: "0",
        CONF_EXPERIMENTAL_PLATFORMS: "false",
        CONF_HIDE_UNKNOWN_ENTITIES: "false",
        CONF_TOPOLOGY_CHANGE_REPAIRS: "off",
    }).schema

    defaults = {marker.schema: marker.default() for marker in schema}
    assert defaults[CONF_SCAN_INTERVAL] == MAX_SCAN_INTERVAL
    assert defaults[CONF_DEBUG_MODE] is False
    assert defaults[CONF_EXPERIMENTAL_PLATFORMS] is False
    assert defaults[CONF_HIDE_UNKNOWN_ENTITIES] is False
    assert defaults[CONF_TOPOLOGY_CHANGE_REPAIRS] is False


def test_options_schema_exposes_device_filter_defaults() -> None:
    """设备过滤表单应从已存储 filter 读取默认值."""
    schema = options_schema({
        CONF_DEVICE_IMPORT_FILTER: {
            "enabled": True,
            "mode": "and",
            "include": {
                "categories": ["light", "curtain"],
                "devices": ["device-1"],
            },
            "exclude": {"rooms": ["room-1"]},
        }
    }).schema

    defaults = {marker.schema: marker.default() for marker in schema}
    assert defaults[CONF_DEVICE_IMPORT_FILTER_ENABLED] is True
    assert defaults[CONF_DEVICE_IMPORT_FILTER_MODE] == "and"
    mode_selector = schema[
        next(marker for marker in schema if marker.schema == CONF_DEVICE_IMPORT_FILTER_MODE)
    ]
    assert mode_selector.config["translation_key"] == "device_import_filter_mode"
    assert mode_selector.config["options"] == ["or", "and"]
    assert defaults[CONF_DEVICE_IMPORT_FILTER_INCLUDE_CATEGORIES] == "curtain, light"
    assert defaults[CONF_DEVICE_IMPORT_FILTER_INCLUDE_DEVICES] == "device-1"
    assert defaults[CONF_DEVICE_IMPORT_FILTER_EXCLUDE_ROOMS] == "room-1"


def test_merge_options_preserves_hidden_advanced_keys() -> None:
    """Options merge should keep hidden advanced keys while replacing visible fields."""
    import_filter = {"enabled": True, "exclude": {"devices": ["secret-device"]}}
    result = merge_options(
        {
            CONF_DEVICE_IMPORT_FILTER: import_filter,
            "future_option": "keep",
            CONF_SCAN_INTERVAL: 15,
        },
        {
            CONF_SCAN_INTERVAL: 45,
            CONF_DEBUG_MODE: True,
            CONF_EXPERIMENTAL_PLATFORMS: True,
            CONF_HIDE_UNKNOWN_ENTITIES: False,
            CONF_TOPOLOGY_CHANGE_REPAIRS: False,
            CONF_DEVICE_IMPORT_FILTER_ENABLED: False,
            CONF_DEVICE_IMPORT_FILTER_MODE: "or",
            CONF_DEVICE_IMPORT_FILTER_INCLUDE_CATEGORIES: "",
            CONF_DEVICE_IMPORT_FILTER_EXCLUDE_CATEGORIES: "",
        },
    )

    assert result == {
        "future_option": "keep",
        CONF_SCAN_INTERVAL: 45,
        CONF_DEBUG_MODE: True,
        CONF_EXPERIMENTAL_PLATFORMS: True,
        CONF_HIDE_UNKNOWN_ENTITIES: False,
        CONF_TOPOLOGY_CHANGE_REPAIRS: False,
        CONF_LIVE_UPDATES: DEFAULT_LIVE_UPDATES,
        CONF_LOCAL_GATEWAY_CONTROL: DEFAULT_LOCAL_GATEWAY_CONTROL,
        CONF_LOCAL_GATEWAY_HOST: DEFAULT_LOCAL_GATEWAY_HOST,
        CONF_LOCAL_GATEWAY_PORT: DEFAULT_LOCAL_GATEWAY_PORT,
        CONF_ANALYTICS_RUNTIME: DEFAULT_ANALYTICS_RUNTIME,
        CONF_ANALYTICS_RETENTION_DAYS: DEFAULT_ANALYTICS_RETENTION_DAYS,
        CONF_DEVICE_IMPORT_FILTER: {
            "enabled": False,
            "mode": "or",
            "include": {},
            "exclude": {"devices": ["secret-device"]},
        },
    }


def test_merge_options_writes_manual_device_filter_config() -> None:
    """options flow 手动过滤字段应写入既有 device_import_filter 契约."""
    result = merge_options(
        {
            CONF_SCAN_INTERVAL: 15,
            CONF_DEBUG_MODE: False,
            CONF_EXPERIMENTAL_PLATFORMS: False,
            CONF_HIDE_UNKNOWN_ENTITIES: True,
            CONF_TOPOLOGY_CHANGE_REPAIRS: True,
        },
        {
            CONF_SCAN_INTERVAL: 15,
            CONF_DEBUG_MODE: False,
            CONF_EXPERIMENTAL_PLATFORMS: False,
            CONF_HIDE_UNKNOWN_ENTITIES: True,
            CONF_TOPOLOGY_CHANGE_REPAIRS: True,
            CONF_DEVICE_IMPORT_FILTER_ENABLED: True,
            CONF_DEVICE_IMPORT_FILTER_MODE: "and",
            CONF_DEVICE_IMPORT_FILTER_INCLUDE_CATEGORIES: "light, curtain, light",
            CONF_DEVICE_IMPORT_FILTER_EXCLUDE_ROOMS: "room-1",
        },
    )

    assert result[CONF_DEVICE_IMPORT_FILTER] == {
        "enabled": True,
        "mode": "and",
        "include": {"categories": ["curtain", "light"]},
        "exclude": {"rooms": ["room-1"]},
    }
    assert CONF_DEVICE_IMPORT_FILTER_ENABLED not in result
    assert CONF_DEVICE_IMPORT_FILTER_INCLUDE_CATEGORIES not in result


def test_merge_options_canonicalizes_legacy_device_filter_input() -> None:
    """设备过滤保存必须输出 canonical shape，并正确处理字符串 false."""
    result = merge_options(
        {
            CONF_SCAN_INTERVAL: 15,
            CONF_DEBUG_MODE: False,
            CONF_EXPERIMENTAL_PLATFORMS: False,
            CONF_HIDE_UNKNOWN_ENTITIES: True,
            CONF_TOPOLOGY_CHANGE_REPAIRS: True,
        },
        {
            CONF_SCAN_INTERVAL: 15,
            CONF_DEBUG_MODE: False,
            CONF_EXPERIMENTAL_PLATFORMS: False,
            CONF_HIDE_UNKNOWN_ENTITIES: True,
            CONF_TOPOLOGY_CHANGE_REPAIRS: True,
            CONF_DEVICE_IMPORT_FILTER_ENABLED: "false",
            CONF_DEVICE_IMPORT_FILTER_MODE: " AND ",
            CONF_DEVICE_IMPORT_FILTER_INCLUDE_CATEGORIES: "light, light",
            CONF_DEVICE_IMPORT_FILTER_EXCLUDE_ROOMS: "room-1, room-2",
        },
    )

    assert result[CONF_DEVICE_IMPORT_FILTER] == {
        "enabled": False,
        "mode": "and",
        "include": {"categories": ["light"]},
        "exclude": {"rooms": ["room-1", "room-2"]},
    }


def test_visible_option_change_count_ignores_hidden_advanced_keys() -> None:
    """确认页变更数量只统计可见 options 字段."""
    assert visible_option_change_count(
        {
            CONF_SCAN_INTERVAL: 15,
            CONF_DEBUG_MODE: False,
            CONF_DEVICE_IMPORT_FILTER: {"enabled": False},
        },
        {
            CONF_SCAN_INTERVAL: 45,
            CONF_DEBUG_MODE: False,
            CONF_DEVICE_IMPORT_FILTER: {"enabled": True},
        },
    ) == 1


def test_visible_option_change_count_counts_effective_device_filter_once() -> None:
    """设备过滤多字段变更在确认页只算一个可见选项."""
    assert visible_option_change_count(
        {
            CONF_SCAN_INTERVAL: 15,
            CONF_DEBUG_MODE: False,
            CONF_DEVICE_IMPORT_FILTER: {"enabled": False},
        },
        {
            CONF_SCAN_INTERVAL: 15,
            CONF_DEBUG_MODE: False,
            CONF_DEVICE_IMPORT_FILTER: {
                "enabled": True,
                "include": {"categories": ["light"], "devices": ["device-1"]},
            },
        },
    ) == 1


def test_cloud_oauth_authorization_url_contains_no_secret_material() -> None:
    """配置流授权链接只携带开放平台授权页必需字段."""
    url = cloud_oauth_authorization_url(
        client_id="client-1",
        redirect_uri="https://ha.example.test/auth/external/callback",
    )

    parsed = urlparse(url)
    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == (
        "https://api.yeelight.com/apis/account/oauth/authorize"
    )
    assert parse_qs(parsed.query) == {
        "client_id": ["client-1"],
        "redirect_uri": ["https://ha.example.test/auth/external/callback"],
        "response_type": ["code"],
        "skip_confirm": ["true"],
    }
    assert "secret" not in url.lower()
