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
        "version": 1,
        "minor_version": 4,
        "data": {
            "access_token": "secret-token",
            "account_user_id": 122349,
            "account_username": "secret-user",
            "cloud_domain": "https://example.invalid",
            "cloud_region": "cn",
            "connection_mode": "cloud",
            "house_id": 1,
            "oauth_client_id": "",
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


def yeelight_devices() -> list[dict[str, list[list[str]]]]:
    """Return two aggregate Yeelight device-registry entries."""
    return [
        {"identifiers": [["yeelight_pro", "gateway"]]},
        {"identifiers": [["yeelight_pro", "child"]]},
    ]


def yeelight_entities() -> list[dict[str, str]]:
    """Return aggregate Yeelight entity-registry entries."""
    entities: list[dict[str, str]] = []
    for domain, count in DEFAULT_ENTITY_COUNTS.items():
        entities.extend(
            {
                "platform": "yeelight_pro",
                "entity_id": f"{domain}.sample_{index}",
            }
            for index in range(count)
        )
    return entities
