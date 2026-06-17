"""Translation and Repairs runtime contract tests."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

import pytest

from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.const import (
    CONF_DEBUG_MODE,
    CONF_DEVICE_IMPORT_FILTER_INCLUDE_CATEGORIES,
    CONF_DEVICE_IMPORT_FILTER_INCLUDE_DEVICES,
    CONF_HIDE_UNKNOWN_ENTITIES,
    CONF_PRIVATE_PUSH_DOMAIN,
    CONF_PRIVATE_PUSH_PROXY,
    CONF_SCAN_INTERVAL,
    CONF_SCAN_LOGIN_QRCODE,
    CONF_SCAN_LOGIN_REFRESH,
    CONF_TOPOLOGY_CHANGE_REPAIRS,
)
from custom_components.yeelight_pro.repair_issues import (
    async_create_topology_changed_issue,
)
from scripts.local_ha_verification.i18n_payloads import leaf_paths


def test_translations_are_valid_and_key_aligned() -> None:
    """英文、简中翻译和 strings.json 的关键配置路径必须对齐."""
    strings, english, chinese = _translation_payloads()
    required_paths = {
        ("options", "step", "init", "menu_options", "general"),
        ("options", "step", "init", "menu_options", "cloud_devices"),
        ("options", "step", "init", "menu_options", "filter_categories"),
        ("options", "step", "general", "data", CONF_SCAN_INTERVAL),
        ("options", "step", "general", "data", CONF_DEBUG_MODE),
        ("options", "step", "general", "data", CONF_HIDE_UNKNOWN_ENTITIES),
        ("options", "step", "general", "data", CONF_TOPOLOGY_CHANGE_REPAIRS),
        ("options", "step", "general", "data", CONF_PRIVATE_PUSH_DOMAIN),
        ("options", "step", "general", "data", CONF_PRIVATE_PUSH_PROXY),
        ("options", "step", "filter_categories", "data", "filter_categories"),
        ("options", "step", "filter_rooms", "data", "filter_rooms"),
        ("options", "step", "filter_gateways", "data", "filter_gateways"),
        ("options", "step", "filter_devices", "data", "filter_devices"),
        (
            "options",
            "step",
            "cloud_devices",
            "data",
            CONF_DEVICE_IMPORT_FILTER_INCLUDE_DEVICES,
        ),
        ("options", "step", "confirm_runtime", "title"),
        ("options", "step", "confirm_runtime", "description"),
        ("options", "step", "confirm_reload", "title"),
        ("options", "step", "confirm_reload", "description"),
        ("config", "step", "cloud_region", "data", "cloud_region"),
        ("config", "step", "cloud_auth_method", "data", "cloud_auth_method"),
        ("config", "step", "cloud_scan_login", "data", CONF_SCAN_LOGIN_QRCODE),
        ("config", "step", "cloud_scan_login", "data", CONF_SCAN_LOGIN_REFRESH),
        ("config", "error", "scan_login_expired"),
        ("config", "step", "cloud_devices", "data", CONF_DEVICE_IMPORT_FILTER_INCLUDE_DEVICES),
        ("config", "progress", "cloud_scan_login_wait"),
        ("config", "step", "private_config", "data", CONF_PRIVATE_PUSH_PROXY),
        ("config", "step", "reauth_confirm", "data", "access_token"),
        ("entity", "select", "active_room", "name"),
        ("entity", "select", "active_group", "name"),
        ("entity", "select", "active_scene", "name"),
        ("services", "debug_emit_event", "description"),
        ("services", "refresh", "description"),
        ("services", "refresh", "fields", "refresh_product_schemas", "name"),
        (
            "services",
            "refresh",
            "fields",
            "refresh_product_schemas",
            "description",
        ),
        ("services", "cleanup_registry", "description"),
        ("services", "cleanup_registry", "fields", "entry_id", "name"),
        ("services", "cleanup_registry", "fields", "entry_id", "description"),
        ("services", "cleanup_registry", "fields", "confirm", "name"),
        ("services", "cleanup_registry", "fields", "confirm", "description"),
        ("services", "cleanup_registry", "fields", "audit_id", "name"),
        ("services", "cleanup_registry", "fields", "audit_id", "description"),
    }

    for payload in (strings, english, chinese):
        paths = leaf_paths(payload)
        assert required_paths.issubset(paths)
        assert "options" in payload
        assert "options" not in payload["config"]
        assert CONF_DEVICE_IMPORT_FILTER_INCLUDE_CATEGORIES

    assert leaf_paths(strings) == leaf_paths(chinese)
    assert leaf_paths(strings) == leaf_paths(english)


def test_scan_login_translations_keep_qr_countdown_and_refresh_guidance() -> None:
    """扫码登录文本必须保留 APP 版本、倒计时、轮询和手动刷新提示."""
    strings, english, chinese = _translation_payloads()

    for payload in (strings, chinese):
        description = payload["config"]["step"]["cloud_scan_login"]["description"]
        progress = payload["config"]["progress"]["cloud_scan_login_wait"]
        assert "易来 APP 1.5.0" in description
        assert "{qrcode}" in description
        assert "{status}" in description
        assert "{remaining_seconds}" in description
        assert "{poll_count}" in description
        assert "刷新" in description
        assert "{remaining_seconds}" in progress
        assert "{poll_count}" in progress

    english_description = english["config"]["step"]["cloud_scan_login"][
        "description"
    ]
    english_progress = english["config"]["progress"]["cloud_scan_login_wait"]
    assert "Yeelight APP 1.5.0" in english_description
    assert "{qrcode}" in english_description
    assert "{status}" in english_description
    assert "{remaining_seconds}" in english_description
    assert "{poll_count}" in english_description
    assert "refresh" in english_description.casefold()
    assert "{remaining_seconds}" in english_progress
    assert "{poll_count}" in english_progress


def test_topology_repair_placeholders_match_translations(
    hass: HomeAssistant,
    mock_config_entry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Repairs 创建路径传入的占位符必须覆盖三份翻译文本."""
    expected_placeholders = set()
    for payload in _translation_payloads():
        description = payload["issues"]["device_topology_changed"]["description"]
        expected_placeholders.update(re.findall(r"{([^{}]+)}", description))

    created: dict[str, Any] = {}

    def capture_issue(*args: object, **kwargs: object) -> None:
        created.update(kwargs)

    monkeypatch.setattr(
        "custom_components.yeelight_pro.repair_issues.ir.async_create_issue",
        capture_issue,
    )
    monkeypatch.setattr(
        "custom_components.yeelight_pro.repair_issues.ir.async_delete_issue",
        lambda *args, **kwargs: None,
    )
    coordinator = type(
        "Coordinator",
        (),
        {
            "topology_generation": 2,
            "devices": {},
            "gateways": {},
            "areas": [{}],
            "rooms": {},
            "groups": {},
            "scenes": {},
        },
    )()

    async_create_topology_changed_issue(
        hass,
        mock_config_entry,
        coordinator,
        previous_generation=1,
    )

    assert set(created["translation_placeholders"]) == expected_placeholders
    assert "areas" in created["translation_placeholders"]


def _translation_payloads() -> list[dict[str, Any]]:
    """Read production translation payloads used by the component."""
    base = Path(__file__).parents[1]
    return [
        json.loads((base / "strings.json").read_text()),
        json.loads((base / "translations" / "en.json").read_text()),
        json.loads((base / "translations" / "zh-Hans.json").read_text()),
    ]
