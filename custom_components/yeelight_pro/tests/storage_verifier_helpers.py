"""Helpers for local HA storage verifier tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.verify_local_ha import DEFAULT_ENTITY_COUNTS


def write_storage(config_dir: Path, key: str, data: Any) -> None:
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
        "title": "Yeelight Pro Cloud (secret-user · CN · 绿地中央公园)",
        "version": 1,
        "minor_version": 10,
        "data": {
            "access_token": "secret-token",
            "account_user_id": 122349,
            "account_username": "secret-user",
            "cloud_domain": "https://example.invalid",
            "cloud_region": "cn",
            "connection_mode": "cloud",
            "house_id": 1,
            "house_name": "绿地中央公园",
            "open_api_client_id": "secret-client-id",
            "open_api_client_secret": "secret-client-secret",
            "private_domain": "",
            "private_push_domain": "",
            "refresh_token": "secret-refresh",
            "scan_login_device": "secret-device",
            "token_expires_in": 7775999,
            "token_type": "bearer",
        },
        "options": {
            "debug_mode": False,
            "hide_unknown_entities": True,
            "scan_interval": 30,
            "topology_change_repairs": True,
        },
    }


def lan_config_entry() -> dict[str, Any]:
    """Return a migrated LAN-only Yeelight Pro config entry shape."""
    entry = config_entry()
    entry["unique_id"] = "lan:192.168.0.252:65443"
    entry["title"] = "Yeelight Pro LAN (192.168.0.252:65443)"
    entry["data"] = {
        **entry["data"],
        "account_user_id": None,
        "account_username": "",
        "cloud_domain": "",
        "cloud_region": "",
        "connection_mode": "lan",
        "house_id": 0,
        "house_name": "",
        "lan_gateway_ip": "192.168.0.252",
        "lan_gateway_port": 65443,
        "local_gateway_host": "192.168.0.252",
        "local_gateway_port": 65443,
        "open_api_client_id": "",
        "open_api_client_secret": "",
        "private_domain": "",
        "private_push_domain": "",
        "refresh_token": "",
        "scan_login_device": "",
        "token_expires_in": 0,
        "token_type": "",
    }
    return entry


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
            "model": "筒灯",
            "model_id": "YL-100",
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
            "model": "墙壁开关",
            "model_id": "YL-201",
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
    for entity in entities:
        translation_key = _translation_key(entity.get("unique_id"))
        if translation_key is not None:
            entity["translation_key"] = translation_key
        entity_category = _entity_category(entity.get("entity_id"))
        if entity_category is not None:
            entity["entity_category"] = entity_category
    return entities


def _unique_id(domain: str, index: int) -> str:
    """Return source-like scoped unique ids for registry fixtures."""
    scope = "cloud_cn_account_fixture_house_1"
    if domain in {"light", "switch"}:
        source_id = "304784333" if domain == "light" else "304784336"
        component = "light" if domain == "light" else "switch"
        return f"yeelight_pro_{scope}_device_{source_id}_{component}_{index}"
    if domain == "select":
        selectors = ("room", "group", "scene")
        if index < len(selectors):
            return f"yeelight_pro_{scope}_select_{selectors[index]}"
        return f"yeelight_pro_{scope}_device_304784336_switch_{index}_mode_select"
    return f"yeelight_pro_{scope}_topology_{domain}_{index}"


def _device_id(domain: str, index: int) -> str | None:
    """Return HA device ids for source-device entities only."""
    if domain == "light":
        return "device-registry-1"
    if domain == "switch":
        return "device-registry-2"
    if domain == "select" and index >= 3:
        return "device-registry-2"
    return None


def _translation_key(unique_id: str | None) -> str | None:
    """Return HA translation keys for static house-level selectors."""
    if unique_id is None:
        return None
    if unique_id.endswith("_select_room"):
        return "active_room"
    if unique_id.endswith("_select_group"):
        return "active_group"
    if unique_id.endswith("_select_scene"):
        return "active_scene"
    return None


def _entity_category(entity_id: str | None) -> str | None:
    """Return expected HA entity category for helper fixture domains."""
    if entity_id is None or "." not in entity_id:
        return None
    domain = entity_id.split(".", 1)[0]
    if domain in {"button", "number", "select"}:
        return "config"
    if domain in {"binary_sensor", "event", "sensor"}:
        return "diagnostic"
    return None
