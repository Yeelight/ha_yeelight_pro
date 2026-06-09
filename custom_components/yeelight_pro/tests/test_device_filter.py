"""Tests for non-destructive Yeelight Pro device import filter preview."""
from __future__ import annotations

from custom_components.yeelight_pro.device_filter import (
    canonical_device_import_filter,
    normalize_device_import_filter,
    preview_device_import_filter,
)


def test_preview_disabled_filter_keeps_all_devices() -> None:
    """默认关闭过滤时，预览不排除任何设备。"""
    devices = [
        {"id": 1, "category": "light"},
        {"id": 2, "category": "curtain"},
    ]

    preview = preview_device_import_filter(devices, {})

    assert preview.as_dict() == {
        "enabled": False,
        "rules_count": 0,
        "visible_devices": 2,
        "excluded_devices": 0,
        "matched_devices": 0,
        "total_devices": 2,
        "mode": "or",
        "rules_by_dimension": {},
        "ignored_rule_count": 0,
        "distinct_value_counts_by_dimension": {
            "categories": 2,
            "devices": 2,
        },
    }


def test_preview_include_rules_count_visible_devices() -> None:
    """include 规则应只预览匹配设备数量，不返回设备标识。"""
    devices = [
        {"id": 1, "category": "light", "roomId": "room_1", "pid": 101},
        {"id": 2, "category": "curtain", "roomId": "room_2", "pid": 102},
        {"id": 3, "category": "human_sensor", "roomId": "room_2", "pid": 103},
    ]

    preview = preview_device_import_filter(
        devices,
        {
            "enabled": True,
            "include": {
                "categories": ["light"],
                "rooms": ["room_2"],
            },
        },
    )

    assert preview.as_dict() == {
        "enabled": True,
        "rules_count": 2,
        "visible_devices": 3,
        "excluded_devices": 0,
        "matched_devices": 3,
        "total_devices": 3,
        "mode": "or",
        "rules_by_dimension": {
            "categories": 1,
            "rooms": 1,
        },
        "ignored_rule_count": 0,
        "distinct_value_counts_by_dimension": {
            "categories": 3,
            "devices": 3,
            "product_ids": 3,
            "rooms": 2,
        },
    }


def test_preview_include_and_mode_requires_every_dimension() -> None:
    """and 模式下，同一设备必须命中所有配置维度。"""
    devices = [
        {"id": 1, "category": "light", "roomId": "room_1"},
        {"id": 2, "category": "light", "roomId": "room_2"},
        {"id": 3, "category": "curtain", "roomId": "room_2"},
    ]

    preview = preview_device_import_filter(
        devices,
        {
            "enabled": True,
            "mode": "and",
            "include": {
                "categories": ["light"],
                "rooms": ["room_2"],
            },
        },
    )

    assert preview.visible_devices == 1
    assert preview.excluded_devices == 2
    assert preview.matched_devices == 1
    assert preview.mode == "and"


def test_preview_exclude_rules_count_excluded_devices() -> None:
    """exclude 规则应只预览被排除数量，不修改输入设备。"""
    devices = [
        {"id": 1, "category": "light", "device_id": "dev_1"},
        {"id": 2, "category": "curtain", "device_id": "dev_2"},
    ]

    preview = preview_device_import_filter(
        devices,
        {
            "enabled": True,
            "exclude": {
                "devices": ["dev_2"],
            },
        },
    )

    assert preview.as_dict() == {
        "enabled": True,
        "rules_count": 1,
        "visible_devices": 1,
        "excluded_devices": 1,
        "matched_devices": 1,
        "total_devices": 2,
        "mode": "or",
        "rules_by_dimension": {"devices": 1},
        "ignored_rule_count": 0,
        "distinct_value_counts_by_dimension": {
            "categories": 2,
            "devices": 2,
        },
    }
    assert len(devices) == 2


def test_normalize_filter_reports_ignored_rules_without_raw_values() -> None:
    """未知过滤维度只计数，不输出规则原值。"""
    normalized = normalize_device_import_filter(
        {
            "enabled": True,
            "include": {
                "categories": ["light", "curtain"],
                "rooms": "room-secret",
                "unsupported": ["token-secret", "device-secret"],
            },
            "exclude": {
                "devices": ["device-secret"],
                "custom": "house-secret",
            },
        }
    )

    assert normalized.enabled is True
    assert normalized.rules_count == 4
    assert normalized.rules_by_dimension == {
        "categories": 2,
        "devices": 1,
        "rooms": 1,
    }
    assert normalized.ignored_rule_count == 3


def test_normalize_filter_accepts_dimension_aliases() -> None:
    """配置维度别名应归一到 canonical dimensions."""
    normalized = normalize_device_import_filter(
        {
            "enabled": True,
            "include": {
                "category": "light",
                "nodeType": 2,
                "roomId": "room-secret",
                "gatewayDeviceId": "gateway-secret",
                "productId": 101,
                "deviceId": "device-secret",
            },
            "exclude": {
                "productID": 102,
                "node_types": [4],
            },
        }
    )

    assert normalized.rules_by_dimension == {
        "categories": 1,
        "devices": 1,
        "gateways": 1,
        "product_ids": 2,
        "rooms": 1,
        "types": 2,
    }
    assert normalized.ignored_rule_count == 0
    assert normalized.rules_count == 8


def test_normalize_filter_trims_comma_strings_and_case_variants() -> None:
    """手工 options 输入的空白、逗号和大小写不应导致规则失效."""
    normalized = normalize_device_import_filter(
        {
            "enabled": True,
            "mode": " AND ",
            "include": {
                " Category ": " light, curtain, light ",
                " ProductID ": " 101, 102 ",
            },
            "exclude": {
                " DeviceId ": [" dev-1 ", "", None],
            },
        }
    )

    assert normalized.enabled is True
    assert normalized.mode == "and"
    assert normalized.include == {
        "categories": {"light", "curtain"},
        "product_ids": {"101", "102"},
    }
    assert normalized.exclude == {"devices": {"dev-1"}}
    assert normalized.rules_by_dimension == {
        "categories": 2,
        "devices": 1,
        "product_ids": 2,
    }
    assert normalized.ignored_rule_count == 0


def test_canonical_filter_returns_stable_storage_shape() -> None:
    """存储形态必须稳定，避免 options 比较和 diagnostics 边界漂移."""
    assert canonical_device_import_filter({
        "enabled": "true",
        "mode": " AND ",
        "include": {
            " ProductID ": "102, 101, 101",
            "unsupported": "token-secret",
        },
        "exclude": {" DeviceId ": [" dev-2 ", "dev-1"]},
    }) == {
        "enabled": True,
        "mode": "and",
        "include": {"product_ids": ["101", "102"]},
        "exclude": {"devices": ["dev-1", "dev-2"]},
    }


def test_canonical_filter_treats_legacy_false_string_as_disabled() -> None:
    """旧 options 中字符串 false 不能按 Python truthiness 误启用过滤."""
    assert canonical_device_import_filter({
        "enabled": "false",
        "include": {"categories": ["light"]},
    }) == {
        "enabled": False,
        "mode": "or",
        "include": {"categories": ["light"]},
        "exclude": {},
    }


def test_preview_supports_yeelight_dimension_aliases() -> None:
    """预览规则支持 Yeelight 文档中的常见字段别名。"""
    devices = [
        {
            "id": 1,
            "nodeType": 2,
            "roomIds": ["11", "12"],
            "gatewayId": "gw_1",
            "productId": 101,
        },
        {
            "deviceId": "device_2",
            "node_type": 4,
            "room_id": "13",
            "gateway_id": "gw_2",
            "product_key": 102,
        },
    ]

    preview = preview_device_import_filter(
        devices,
        {
            "enabled": True,
            "include": {
                "types": ["2"],
                "rooms": ["13"],
                "gateways": ["gw_2"],
                "product_ids": ["101"],
                "devices": ["device_2"],
            },
        },
    )

    assert preview.visible_devices == 2
    assert preview.matched_devices == 2
