"""Config flow helper regression tests."""
from __future__ import annotations

from custom_components.yeelight_pro.config_flow_helpers import (
    merge_options,
    options_schema,
    visible_option_change_count,
)
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
    CONNECTION_MODE_CLOUD,
    CONNECTION_MODE_LAN,
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
        "experimental_platforms": "true",
        CONF_HIDE_UNKNOWN_ENTITIES: "false",
        CONF_TOPOLOGY_CHANGE_REPAIRS: "off",
    }).schema

    defaults = {marker.schema: marker.default() for marker in schema}
    assert defaults[CONF_SCAN_INTERVAL] == MAX_SCAN_INTERVAL
    assert defaults[CONF_DEBUG_MODE] is False
    assert defaults[CONF_HIDE_UNKNOWN_ENTITIES] is False
    assert defaults[CONF_TOPOLOGY_CHANGE_REPAIRS] is False
    assert defaults[CONF_LIVE_UPDATES] is DEFAULT_LIVE_UPDATES
    assert CONF_LOCAL_GATEWAY_CONTROL not in defaults
    assert CONF_LOCAL_GATEWAY_HOST not in defaults
    assert CONF_LOCAL_GATEWAY_PORT not in defaults
    assert "experimental_platforms" not in defaults


def test_options_schema_shows_local_gateway_fields_only_for_lan_mode() -> None:
    """本地网关字段只应出现在局域网连接模式的 options 页."""
    cloud_entry = type(
        "Entry",
        (),
        {"data": {CONF_CONNECTION_MODE: CONNECTION_MODE_CLOUD}},
    )()
    lan_entry = type(
        "Entry",
        (),
        {"data": {CONF_CONNECTION_MODE: CONNECTION_MODE_LAN}},
    )()

    cloud_defaults = {
        marker.schema: marker.default()
        for marker in options_schema({}, cloud_entry).schema
    }
    lan_defaults = {
        marker.schema: marker.default()
        for marker in options_schema({}, lan_entry).schema
    }

    assert CONF_LIVE_UPDATES in cloud_defaults
    assert CONF_LOCAL_GATEWAY_CONTROL not in cloud_defaults
    assert CONF_LOCAL_GATEWAY_HOST not in cloud_defaults
    assert CONF_LOCAL_GATEWAY_PORT not in cloud_defaults
    assert CONF_LIVE_UPDATES not in lan_defaults
    assert lan_defaults[CONF_LOCAL_GATEWAY_CONTROL] is DEFAULT_LOCAL_GATEWAY_CONTROL
    assert lan_defaults[CONF_LOCAL_GATEWAY_HOST] == DEFAULT_LOCAL_GATEWAY_HOST
    assert lan_defaults[CONF_LOCAL_GATEWAY_PORT] == DEFAULT_LOCAL_GATEWAY_PORT


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
            CONF_HIDE_UNKNOWN_ENTITIES: False,
            CONF_TOPOLOGY_CHANGE_REPAIRS: False,
            CONF_LIVE_UPDATES: DEFAULT_LIVE_UPDATES,
        },
    )

    assert result == {
        "future_option": "keep",
        CONF_SCAN_INTERVAL: 45,
        CONF_DEBUG_MODE: True,
        CONF_HIDE_UNKNOWN_ENTITIES: False,
        CONF_TOPOLOGY_CHANGE_REPAIRS: False,
        CONF_LIVE_UPDATES: DEFAULT_LIVE_UPDATES,
        CONF_DEVICE_IMPORT_FILTER: {
            "enabled": True,
            "mode": "or",
            "include": {},
            "exclude": {"devices": ["secret-device"]},
        },
    }


def test_merge_options_removes_cloud_hidden_local_gateway_defaults() -> None:
    """云端 options 保存时不应写入本地网关默认字段."""
    cloud_entry = type(
        "Entry",
        (),
        {"data": {CONF_CONNECTION_MODE: CONNECTION_MODE_CLOUD}},
    )()
    result = merge_options(
        {
            CONF_LOCAL_GATEWAY_CONTROL: True,
            CONF_LOCAL_GATEWAY_HOST: "192.168.1.10",
            CONF_LOCAL_GATEWAY_PORT: 65444,
        },
        {
            CONF_SCAN_INTERVAL: 45,
            CONF_DEBUG_MODE: False,
            CONF_HIDE_UNKNOWN_ENTITIES: True,
            CONF_TOPOLOGY_CHANGE_REPAIRS: True,
            CONF_LIVE_UPDATES: True,
        },
        cloud_entry,
    )

    assert CONF_LOCAL_GATEWAY_CONTROL not in result
    assert CONF_LOCAL_GATEWAY_HOST not in result
    assert CONF_LOCAL_GATEWAY_PORT not in result
    assert result[CONF_LIVE_UPDATES] is True


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
