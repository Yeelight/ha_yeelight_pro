"""Config entry options migration tests."""
from __future__ import annotations

import pytest

from custom_components.yeelight_pro.const import (
    CONF_DEBUG_MODE,
    CONF_DEVICE_IMPORT_FILTER,
    CONF_DEVICE_IMPORT_FILTER_ENABLED,
    CONF_DEVICE_IMPORT_FILTER_EXCLUDE_CATEGORIES,
    CONF_DEVICE_IMPORT_FILTER_INCLUDE_DEVICES,
    CONF_DEVICE_IMPORT_FILTER_INCLUDE_ROOMS,
    CONF_DEVICE_IMPORT_FILTER_MODE,
    CONF_EXPERIMENTAL_PLATFORMS,
    CONF_HIDE_UNKNOWN_ENTITIES,
    CONF_LIVE_UPDATES,
    CONF_LOCAL_GATEWAY_CONTROL,
    CONF_LOCAL_GATEWAY_HOST,
    CONF_LOCAL_GATEWAY_PORT,
    CONF_SCAN_INTERVAL,
    CONF_TOPOLOGY_CHANGE_REPAIRS,
    DEFAULT_SCAN_INTERVAL,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from custom_components.yeelight_pro.entry_migration import normalize_entry_options


def test_normalize_entry_options_clamps_scan_interval() -> None:
    """轮询间隔迁移必须保持在当前 options schema 范围内."""
    assert normalize_entry_options({CONF_SCAN_INTERVAL: 1})[CONF_SCAN_INTERVAL] == (
        MIN_SCAN_INTERVAL
    )
    assert normalize_entry_options({CONF_SCAN_INTERVAL: 999})[CONF_SCAN_INTERVAL] == (
        MAX_SCAN_INTERVAL
    )
    assert normalize_entry_options({CONF_SCAN_INTERVAL: "bad"})[CONF_SCAN_INTERVAL] == (
        DEFAULT_SCAN_INTERVAL
    )

def test_normalize_entry_options_canonicalizes_device_import_filter() -> None:
    """迁移不得丢弃有效过滤规则，但必须写回稳定存储形态."""
    filter_config = {
        "enabled": "true",
        "mode": " AND ",
        "include": {
            "category": "light, curtain, light",
            "unsupported": "token-secret",
        },
        "exclude": {"roomId": ["room-1", " room-2 "]},
    }

    assert normalize_entry_options({
        CONF_DEVICE_IMPORT_FILTER: filter_config
    })[CONF_DEVICE_IMPORT_FILTER] == {
        "enabled": True,
        "mode": "and",
        "include": {"categories": ["curtain", "light"]},
        "exclude": {"rooms": ["room-1", "room-2"]},
    }


def test_normalize_entry_options_migrates_legacy_device_filter_form_keys() -> None:
    """误保存到 options 顶层的表单字段应迁移并从存储中移除."""
    options = normalize_entry_options({
        CONF_DEVICE_IMPORT_FILTER_ENABLED: "true",
        CONF_DEVICE_IMPORT_FILTER_MODE: " AND ",
        CONF_DEVICE_IMPORT_FILTER_INCLUDE_ROOMS: " room-2, room-1, room-2 ",
        CONF_DEVICE_IMPORT_FILTER_INCLUDE_DEVICES: " device-1 ",
        CONF_DEVICE_IMPORT_FILTER_EXCLUDE_CATEGORIES: "other",
    })

    assert options[CONF_DEVICE_IMPORT_FILTER] == {
        "enabled": True,
        "mode": "and",
        "include": {
            "rooms": ["room-1", "room-2"],
            "devices": ["device-1"],
        },
        "exclude": {"categories": ["other"]},
    }
    assert CONF_DEVICE_IMPORT_FILTER_ENABLED not in options
    assert CONF_DEVICE_IMPORT_FILTER_MODE not in options
    assert CONF_DEVICE_IMPORT_FILTER_INCLUDE_ROOMS not in options
    assert CONF_DEVICE_IMPORT_FILTER_INCLUDE_DEVICES not in options
    assert CONF_DEVICE_IMPORT_FILTER_EXCLUDE_CATEGORIES not in options


def test_normalize_entry_options_disables_filter_without_effective_rules() -> None:
    """只有无效维度或空值时不应保存启用态过滤."""
    options = normalize_entry_options({
        CONF_DEVICE_IMPORT_FILTER: {
            "enabled": "true",
            "include": {"unsupported": "token-secret", "categories": ""},
        }
    })

    assert options[CONF_DEVICE_IMPORT_FILTER] == {
        "enabled": False,
        "mode": "or",
        "include": {},
        "exclude": {},
    }


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("false", False),
        ("0", False),
        ("off", False),
        ("true", True),
        ("1", True),
        ("on", True),
    ],
)
def test_normalize_entry_options_parses_string_bools(
    raw: str,
    expected: bool,
) -> None:
    """字符串 bool 不能按 Python truthiness 误判."""
    options = normalize_entry_options({
        CONF_DEBUG_MODE: raw,
        CONF_EXPERIMENTAL_PLATFORMS: raw,
        CONF_HIDE_UNKNOWN_ENTITIES: raw,
        CONF_TOPOLOGY_CHANGE_REPAIRS: raw,
        CONF_LIVE_UPDATES: raw,
        CONF_LOCAL_GATEWAY_CONTROL: raw,
        CONF_LOCAL_GATEWAY_HOST: " 192.168.1.20 ",
        CONF_LOCAL_GATEWAY_PORT: "65444",
    })

    assert options[CONF_DEBUG_MODE] is expected
    assert options[CONF_EXPERIMENTAL_PLATFORMS] is expected
    assert options[CONF_HIDE_UNKNOWN_ENTITIES] is expected
    assert options[CONF_TOPOLOGY_CHANGE_REPAIRS] is expected
    assert options[CONF_LIVE_UPDATES] is expected
    assert options[CONF_LOCAL_GATEWAY_CONTROL] is expected
    assert options[CONF_LOCAL_GATEWAY_HOST] == "192.168.1.20"
    assert options[CONF_LOCAL_GATEWAY_PORT] == 65444
