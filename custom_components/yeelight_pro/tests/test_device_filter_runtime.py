"""Runtime matching tests for Yeelight Pro device import filters."""
from __future__ import annotations

from custom_components.yeelight_pro.device_filter import matches_device_import_filter


def test_matches_device_import_filter_supports_include_rules() -> None:
    """运行时 gate 必须复用 include 规则判断."""
    filter_config = {
        "enabled": True,
        "include": {"categories": ["light"]},
    }

    assert matches_device_import_filter({"id": 1, "category": "light"}, filter_config)
    assert not matches_device_import_filter(
        {"id": 2, "category": "curtain"},
        filter_config,
    )


def test_matches_device_import_filter_supports_exclude_rules() -> None:
    """运行时 gate 必须复用 exclude 规则判断."""
    filter_config = {
        "enabled": True,
        "exclude": {"devices": ["dev_2"]},
    }

    assert matches_device_import_filter(
        {"id": 1, "device_id": "dev_1"},
        filter_config,
    )
    assert not matches_device_import_filter(
        {"id": 2, "device_id": "dev_2"},
        filter_config,
    )


def test_matches_device_import_filter_trims_runtime_payload_values() -> None:
    """运行时载荷里的空白不应绕过设备导入过滤."""
    filter_config = {
        "enabled": True,
        "include": {"categories": "light, curtain"},
        "exclude": {"devices": "dev_2"},
    }

    assert matches_device_import_filter(
        {"id": " dev_1 ", "category": " light "},
        filter_config,
    )
    assert not matches_device_import_filter(
        {"id": " dev_2 ", "category": " curtain "},
        filter_config,
    )
