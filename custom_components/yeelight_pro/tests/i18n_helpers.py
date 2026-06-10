"""Focused fixtures for local HA i18n verifier tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .i18n_service_helpers import service_translation_payload, service_yaml_lines


def write_installed_i18n(
    install_root: Path,
    *,
    strings: dict[str, Any] | None = None,
    english: dict[str, Any] | None = None,
    chinese: dict[str, Any] | None = None,
    extra_option_key: str | None = None,
    extra_repair_placeholder: str | None = None,
) -> None:
    """Write installed translation and services.yaml fixtures."""
    install_root.mkdir(parents=True, exist_ok=True)
    (install_root / "translations").mkdir()
    (install_root / "services.yaml").write_text(
        "\n".join(service_yaml_lines()),
        encoding="utf-8",
    )
    _write_json(install_root / "strings.json", strings or chinese_translation_payload())
    _write_json(
        install_root / "translations" / "en.json",
        english or translation_payload(),
    )
    _write_json(
        install_root / "translations" / "zh-Hans.json",
        chinese or chinese_translation_payload(),
    )
    _write_option_schema_sources(install_root, extra_option_key=extra_option_key)
    _write_repair_issue_source(
        install_root,
        extra_placeholder=extra_repair_placeholder,
    )


def translation_payload() -> dict[str, Any]:
    """Return a minimal translation payload matching the production contract."""
    option_data = {
        "scan_interval": "Scan interval",
        "debug_mode": "Debug mode",
        "experimental_platforms": "Experimental platforms",
        "hide_unknown_entities": "Hide unknown entities",
        "topology_change_repairs": "Topology repairs",
        "live_updates": "Live updates",
        "local_gateway_control": "Local gateway control",
        "local_gateway_host": "Local gateway host",
        "local_gateway_port": "Local gateway port",
        "analytics_runtime": "Analytics runtime",
        "analytics_retention_days": "Analytics retention days",
        "device_import_filter_enabled": "Enable device filter",
        "device_import_filter_mode": "Device filter mode",
    }

    return {
        "config": {
            "step": {
                "user": {
                    "title": "Connection",
                    "description": "Select connection.",
                    "data": {"connection_mode": "Connection mode"},
                },
                "cloud_auth": {
                    "title": "Cloud",
                    "description": "Enter token.",
                    "data": {"access_token": "Access token"},
                },
                "cloud_auth_method": {
                    "title": "Cloud auth",
                    "description": "Select method.",
                    "data": {"cloud_auth_method": "Auth method"},
                },
                "cloud_region": {
                    "title": "Cloud region",
                    "description": "Select region.",
                    "data": {"cloud_region": "Region"},
                },
                "cloud_scan_login": {
                    "title": "Scan login",
                    "description": (
                        "Open Yeelight APP 1.5.0 or later and scan the QR code. "
                        "Manual content: {qrcode}. Status: {status}. "
                        "Remaining seconds: {remaining_seconds}. "
                        "Poll count: {poll_count}. Select refresh after expiry."
                    ),
                    "data": {
                        "scan_login_qrcode": "Login QR code",
                        "scan_login_refresh": "Refresh QR code",
                    },
                },
                "cloud_houses": {
                    "title": "House",
                    "description": "Select house.",
                    "data": {"house_id": "House"},
                },
                "cloud_devices": {
                    "title": "Devices",
                    "description": "Select devices.",
                    "data": {
                        "device_import_filter_include_devices": "Devices",
                    },
                },
                "private_config": {
                    "title": "Private",
                    "description": "Enter private config.",
                    "data": {
                        "private_domain": "Domain",
                        "access_token": "Access token",
                        "house_id": "House ID",
                    },
                },
                "reauth_confirm": {
                    "title": "Reauth",
                    "description": "Enter new token.",
                    "data": {"access_token": "New token"},
                },
            },
            "progress": {
                "cloud_scan_login_wait": (
                    "Waiting for scan authorization. Status: {status}. "
                    "Remaining seconds: {remaining_seconds}. "
                    "Poll count: {poll_count}."
                ),
            },
            "options": {
                "step": {
                    "init": {
                        "title": "Options",
                        "description": "Adjust options.",
                        "data": option_data,
                    },
                    "confirm_runtime": {
                        "title": "Confirm runtime",
                        "description": "Save runtime options.",
                    },
                    "confirm_reload": {
                        "title": "Confirm reload",
                        "description": "Save reload options.",
                    },
                }
            },
            "error": {
                "cannot_connect": "Cannot connect",
                "invalid_auth": "Invalid auth",
                "unknown": "Unknown error",
            },
            "abort": {
                "already_configured": "Already configured",
                "no_houses_found": "No houses found",
                "reauth_successful": "Reauth successful",
            },
        },
        "selector": {
            "connection_mode": {
                "options": {
                    "cloud": "Yeelight Pro cloud",
                    "private": "Private deployment",
                }
            },
            "cloud_auth_method": {
                "options": {
                    "scan_login": "Yeelight APP scan login",
                    "access_token": "Manual Access Token",
                }
            },
            "cloud_region": {
                "options": {
                    "cn": "Mainland China",
                    "sg": "Singapore",
                    "us": "North America",
                    "de": "Europe",
                }
            },
            "device_import_filter_mode": {
                "options": {
                    "or": "Any matching dimension",
                    "and": "All matching dimensions",
                }
            }
        },
        "services": service_translation_payload(),
        "entity": {
            "sensor": {
                "analytics_alarm_total": {"name": "Analytics alarm total"},
                "analytics_alarm_device_count": {
                    "name": "Analytics alarm devices",
                },
                "analytics_energy_used_kwh": {"name": "Analytics energy used"},
                "analytics_energy_saved_kwh": {"name": "Analytics energy saved"},
                "analytics_action_total": {"name": "Analytics action total"},
            }
        },
        "issues": {
            "device_topology_changed": {
                "title": "Topology changed",
                "description": (
                    "Device topology changed: {added} {removed} "
                    "{metadata_changed} {devices} {gateways} {areas} "
                    "{rooms} {groups} {scenes} {automations}."
                ),
            }
        },
    }


def chinese_translation_payload() -> dict[str, Any]:
    """Return a Simplified Chinese variant with the same translation key shape."""
    payload = translation_payload()
    payload["config"]["step"]["cloud_scan_login"].update(
        {
            "title": "易来 APP 扫码登录",
            "description": (
                "请打开易来 APP 1.5.0 或以上版本并扫描二维码。"
                "手动内容：{qrcode}。当前状态：{status}。"
                "剩余秒数：{remaining_seconds}。轮询次数：{poll_count}。"
                "过期后勾选刷新。"
            ),
        }
    )
    payload["config"]["step"]["cloud_scan_login"]["data"][
        "scan_login_refresh"
    ] = "刷新二维码"
    payload["config"]["progress"]["cloud_scan_login_wait"] = (
        "正在等待扫码授权。当前状态：{status}。"
        "剩余秒数：{remaining_seconds}。轮询次数：{poll_count}。"
    )
    payload["selector"]["cloud_auth_method"]["options"][
        "scan_login"
    ] = "易来 APP 扫码登录"
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write a JSON fixture."""
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_option_schema_sources(
    install_root: Path,
    *,
    extra_option_key: str | None,
) -> None:
    """Write focused option-schema source fixtures."""
    const_lines = [
        'CONF_SCAN_INTERVAL = "scan_interval"',
        'CONF_DEBUG_MODE = "debug_mode"',
    ]
    options_lines = [
        "def options_schema(options):",
        "    return vol.Schema({",
        "        vol.Required(CONF_SCAN_INTERVAL): int,",
        "        vol.Required(CONF_DEBUG_MODE): bool,",
    ]
    if extra_option_key is not None:
        const_lines.append(f'CONF_FUTURE_OPTION = "{extra_option_key}"')
        options_lines.append("        vol.Required(CONF_FUTURE_OPTION): bool,")
    options_lines.extend(["    })"])
    (install_root / "const.py").write_text("\n".join(const_lines), encoding="utf-8")
    (install_root / "config_flow_options.py").write_text(
        "\n".join(options_lines),
        encoding="utf-8",
    )
    (install_root / "config_flow_helpers.py").write_text(
        "\n".join(
            [
                'CONNECTION_MODE_CLOUD = "cloud"',
                'CONNECTION_MODE_PRIVATE = "private"',
                'CLOUD_AUTH_METHOD_ACCESS_TOKEN = "access_token"',
                'CLOUD_AUTH_METHOD_SCAN_LOGIN = "scan_login"',
                'CLOUD_REGION_CN = "cn"',
                'CLOUD_REGION_SG = "sg"',
                'CLOUD_REGION_US = "us"',
                'CLOUD_REGION_EU = "de"',
                "CLOUD_REGIONS = [CLOUD_REGION_CN, CLOUD_REGION_SG, CLOUD_REGION_US, CLOUD_REGION_EU]",
                "def user_schema():",
                "    return {",
                "        vol.Required(",
                '            "connection_mode",',
                "        ): selector.SelectSelector(",
                "            selector.SelectSelectorConfig(",
                "                options=[CONNECTION_MODE_CLOUD, CONNECTION_MODE_PRIVATE],",
                '                translation_key="connection_mode",',
                "            )",
                "        )",
                "    }",
                "def cloud_auth_method_schema():",
                "    return {",
                "        vol.Required(",
                '            "cloud_auth_method",',
                "        ): selector.SelectSelector(",
                "            selector.SelectSelectorConfig(",
                "                options=[",
                "                    CLOUD_AUTH_METHOD_SCAN_LOGIN,",
                "                    CLOUD_AUTH_METHOD_ACCESS_TOKEN,",
                "                ],",
                '                translation_key="cloud_auth_method",',
                "            )",
                "        )",
                "    }",
                "def cloud_auth_schema():",
                "    return vol.Schema({",
                '        vol.Required("access_token"): str,',
                '        vol.Optional("house_id"): str,',
                "    })",
                "def cloud_region_schema():",
                "    return {",
                '        vol.Required("cloud_region"): selector.SelectSelector(',
                "            selector.SelectSelectorConfig(",
                "                options=CLOUD_REGIONS,",
                '                translation_key="cloud_region",',
                "            )",
                "        )",
                "    }",
            ]
        ),
        encoding="utf-8",
    )
    (install_root / "device_filter_options.py").write_text(
        "\n".join(
            [
                'FILTER_MODE_ANY = "or"',
                'FILTER_MODE_ALL = "and"',
                "def device_filter_schema_fields(options):",
                "    return {",
                "        vol.Required(",
                '            "device_import_filter_mode",',
                '        ): selector.SelectSelector(',
                "            selector.SelectSelectorConfig(",
                "                options=[FILTER_MODE_ANY, FILTER_MODE_ALL],",
                '                translation_key="device_import_filter_mode",',
                "            )",
                "        )",
                "    }",
            ]
        ),
        encoding="utf-8",
    )


def _write_repair_issue_source(
    install_root: Path,
    *,
    extra_placeholder: str | None,
) -> None:
    """Write a focused repair issue source fixture."""
    placeholder_lines = [
        '                "devices": counts["devices"],',
        '                "gateways": counts["gateways"],',
        '                "areas": counts["areas"],',
        '                "rooms": counts["rooms"],',
        '                "groups": counts["groups"],',
        '                "scenes": counts["scenes"],',
        '                "automations": counts["automations"],',
        '                "added": diff_summary["total_added"],',
        '                "removed": diff_summary["total_removed"],',
        '                "metadata_changed": diff_summary["total_metadata_changed"],',
    ]
    if extra_placeholder is not None:
        placeholder_lines.append(f'                "{extra_placeholder}": "1",')
    (install_root / "repair_issues.py").write_text(
        "\n".join(
            [
                "def create_issue(ir, hass, counts, diff_summary):",
                "    ir.async_create_issue(",
                "        hass,",
                '        "yeelight_pro",',
                '        "device_topology_changed_entry_1",',
                '        translation_key="device_topology_changed",',
                "        translation_placeholders={",
                "            key: str(value)",
                "            for key, value in {",
                *placeholder_lines,
                "            }.items()",
                "        },",
                "    )",
            ]
        ),
        encoding="utf-8",
    )
