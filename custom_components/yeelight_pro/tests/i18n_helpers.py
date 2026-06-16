"""Focused fixtures for local HA i18n verifier tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .i18n_service_helpers import service_translation_payload, service_yaml_lines
from .i18n_source_fixture_helpers import (
    write_option_schema_sources,
    write_repair_issue_source,
)


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
    write_option_schema_sources(install_root, extra_option_key=extra_option_key)
    write_repair_issue_source(
        install_root,
        extra_placeholder=extra_repair_placeholder,
    )


def translation_payload() -> dict[str, Any]:
    """Return a minimal translation payload matching the production contract."""
    option_data = {
        "scan_interval": "Scan interval",
        "debug_mode": "Debug mode",
        "hide_unknown_entities": "Hide unknown entities",
        "topology_change_repairs": "Topology repairs",
        "live_updates": "Live updates",
        "local_gateway_control": "Local gateway control",
        "local_gateway_host": "Local gateway host",
        "local_gateway_port": "Local gateway port",
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
                    "description": "Enter private Open API URL.",
                    "data": {
                        "private_domain": "Domain",
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
        "options": {
            "step": {
                "init": {
                    "title": "Options",
                    "description": "Adjust options.",
                    "menu_options": {
                        "general": "General settings",
                        "cloud_devices": "Real device picker",
                        "filter_categories": "Device import filter",
                    },
                },
                "general": {
                    "title": "General settings",
                    "description": "Adjust runtime options.",
                    "data": option_data,
                },
                "filter_categories": {
                    "title": "Select categories",
                    "description": "Select device categories.",
                    "data": {"filter_categories": "Categories"},
                },
                "filter_rooms": {
                    "title": "Select rooms",
                    "description": "Select rooms.",
                    "data": {"filter_rooms": "Rooms"},
                },
                "filter_gateways": {
                    "title": "Select gateways",
                    "description": "Select gateways.",
                    "data": {"filter_gateways": "Gateways"},
                },
                "filter_devices": {
                    "title": "Select devices",
                    "description": "Select devices.",
                    "data": {"filter_devices": "Devices"},
                },
                "confirm_runtime": {
                    "title": "Confirm runtime",
                    "description": "Save runtime options.",
                },
                "confirm_reload": {
                    "title": "Confirm reload",
                    "description": "Save reload options.",
                },
                "cloud_devices": {
                    "title": "Select cloud devices",
                    "description": "Select devices to import.",
                    "data": {
                        "device_import_filter_include_devices": "Devices",
                    },
                },
            }
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
        "entity": {
            "select": {
                "active_room": {"name": "Active room"},
                "active_group": {"name": "Active group"},
                "active_scene": {"name": "Active scene"},
            }
        },
        "services": service_translation_payload(),
        "issues": {
            "device_topology_changed": {
                "title": "Topology changed",
                "description": (
                    "Device topology changed: {added} {removed} "
                    "{metadata_changed} {devices} {gateways} {areas} "
                    "{rooms} {groups} {scenes}."
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
    payload["entity"]["select"]["active_room"]["name"] = "当前房间"
    payload["entity"]["select"]["active_group"]["name"] = "当前灯组"
    payload["entity"]["select"]["active_scene"]["name"] = "当前场景"
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write a JSON fixture."""
    path.write_text(json.dumps(payload), encoding="utf-8")
