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
    CONF_DEVICE_IMPORT_FILTER_ENABLED,
    CONF_DEVICE_IMPORT_FILTER_EXCLUDE_CATEGORIES,
    CONF_DEVICE_IMPORT_FILTER_INCLUDE_CATEGORIES,
    CONF_DEVICE_IMPORT_FILTER_INCLUDE_DEVICES,
    CONF_DEVICE_IMPORT_FILTER_MODE,
    CONF_EXPERIMENTAL_PLATFORMS,
    CONF_HIDE_UNKNOWN_ENTITIES,
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
        ("config", "options", "step", "init", "data", CONF_SCAN_INTERVAL),
        ("config", "options", "step", "init", "data", CONF_DEBUG_MODE),
        ("config", "options", "step", "init", "data", CONF_EXPERIMENTAL_PLATFORMS),
        ("config", "options", "step", "init", "data", CONF_HIDE_UNKNOWN_ENTITIES),
        ("config", "options", "step", "init", "data", CONF_TOPOLOGY_CHANGE_REPAIRS),
        ("config", "options", "step", "init", "data", CONF_DEVICE_IMPORT_FILTER_ENABLED),
        ("config", "options", "step", "init", "data", CONF_DEVICE_IMPORT_FILTER_MODE),
        (
            "config",
            "options",
            "step",
            "init",
            "data",
            CONF_DEVICE_IMPORT_FILTER_INCLUDE_CATEGORIES,
        ),
        (
            "config",
            "options",
            "step",
            "init",
            "data",
            CONF_DEVICE_IMPORT_FILTER_EXCLUDE_CATEGORIES,
        ),
        ("config", "options", "step", "confirm_runtime", "title"),
        ("config", "options", "step", "confirm_runtime", "description"),
        ("config", "options", "step", "confirm_reload", "title"),
        ("config", "options", "step", "confirm_reload", "description"),
        ("config", "step", "cloud_region", "data", "cloud_region"),
        ("config", "step", "cloud_auth_method", "data", "cloud_auth_method"),
        ("config", "step", "cloud_scan_login", "data", CONF_SCAN_LOGIN_QRCODE),
        ("config", "step", "cloud_scan_login", "data", CONF_SCAN_LOGIN_REFRESH),
        ("config", "step", "cloud_devices", "data", CONF_DEVICE_IMPORT_FILTER_INCLUDE_DEVICES),
        ("config", "progress", "cloud_scan_login_wait"),
        ("config", "step", "reauth_confirm", "data", "access_token"),
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
        ("services", "refresh_analytics", "description"),
        ("services", "refresh_analytics", "fields", "endpoint", "name"),
        ("services", "refresh_analytics", "fields", "endpoint", "description"),
        ("entity", "sensor", "analytics_alarm_total", "name"),
        ("entity", "sensor", "analytics_alarm_device_count", "name"),
        ("entity", "sensor", "analytics_energy_used_kwh", "name"),
        ("entity", "sensor", "analytics_energy_saved_kwh", "name"),
        ("entity", "sensor", "analytics_action_total", "name"),
    }

    for payload in (strings, english, chinese):
        paths = leaf_paths(payload)
        assert required_paths.issubset(paths)

    assert leaf_paths(strings) == leaf_paths(chinese)
    assert leaf_paths(strings) == leaf_paths(english)


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
            "automations": {},
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
