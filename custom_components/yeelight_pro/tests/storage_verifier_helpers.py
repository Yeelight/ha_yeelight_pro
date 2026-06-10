"""Helpers for local HA storage verifier tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.verify_local_ha import DEFAULT_ENTITY_COUNTS


def write_storage(config_dir: Path, key: str, data: dict[str, Any]) -> None:
    """Write a minimal Home Assistant storage file."""
    storage_dir = config_dir / ".storage"
    storage_dir.mkdir(exist_ok=True)
    payload = {"version": 1, "minor_version": 1, "key": key, "data": data}
    (storage_dir / key).write_text(json.dumps(payload), encoding="utf-8")


def config_entry() -> dict[str, Any]:
    """Return a migrated Yeelight Pro config entry shape."""
    return {
        "domain": "yeelight_pro",
        "disabled_by": None,
        "unique_id": "cloud:cn:122349:1",
        "title": "Yeelight Pro Cloud (secret-user · CN · House 1)",
        "version": 1,
        "minor_version": 6,
        "data": {
            "access_token": "secret-token",
            "account_user_id": 122349,
            "account_username": "secret-user",
            "cloud_domain": "https://example.invalid",
            "cloud_region": "cn",
            "connection_mode": "cloud",
            "house_id": 1,
            "open_api_client_id": "",
            "private_domain": "",
            "refresh_token": "secret-refresh",
            "scan_login_device": "secret-device",
            "token_expires_in": 7775999,
            "token_type": "bearer",
        },
        "options": {
            "debug_mode": False,
            "experimental_platforms": False,
            "hide_unknown_entities": True,
            "scan_interval": 30,
            "topology_change_repairs": True,
        },
    }


def yeelight_devices() -> list[dict[str, Any]]:
    """Return aggregate Yeelight device-registry entries with source metadata."""
    return [
        {
            "id": "device-registry-1",
            "identifiers": [
                ["yeelight_pro", "304784333"],
                ["yeelight_pro", "device:304784333"],
            ],
            "name": "客厅筒灯 1",
            "manufacturer": "Yeelight",
            "model": "light",
            "area_id": "ke_ting",
        },
        {
            "id": "device-registry-2",
            "identifiers": [
                ["yeelight_pro", "304784336"],
                ["yeelight_pro", "device:304784336"],
            ],
            "name": "墙壁开关1",
            "manufacturer": "Yeelight",
            "model": "relay_switch",
            "suggested_area": "客厅",
        },
    ]


def yeelight_entities() -> list[dict[str, str | None]]:
    """Return aggregate Yeelight entity-registry entries."""
    entities: list[dict[str, str | None]] = []
    for domain, count in DEFAULT_ENTITY_COUNTS.items():
        entities.extend(
            {
                "platform": "yeelight_pro",
                "entity_id": f"{domain}.sample_{index}",
                "unique_id": _unique_id(domain, index),
                "device_id": _device_id(domain, index),
            }
            for index in range(count)
        )
    return entities


def _unique_id(domain: str, index: int) -> str:
    """Return source-like unique ids for device platforms."""
    if domain in {"light", "switch"}:
        source_id = "304784333" if domain == "light" else "304784336"
        component = "light" if domain == "light" else "switch"
        return f"yeelight_pro_{source_id}_{component}_{index}"
    return f"yeelight_pro_topology_{domain}_{index}"


def _device_id(domain: str, index: int) -> str | None:
    """Return HA device ids for source-device entities only."""
    if domain == "light":
        return "device-registry-1"
    if domain == "switch":
        return "device-registry-2"
    return None
