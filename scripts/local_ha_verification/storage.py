"""Home Assistant storage verification."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from .constants import DOMAIN
from .options import verify_config_entry_options
from .platforms import verify_platform_options_alignment
from .report import VerificationReport
from .storage_entries import (
    verify_config_entry_migration,
    verify_config_entry_titles,
    verify_config_entry_unique_ids,
)
from .storage_helpers import read_json, safe_storage_items, sensitive_cache_hits, storage_path


def verify_storage(
    config_dir: Path,
    report: VerificationReport,
    *,
    expected_config_entries: int,
    expected_devices: int,
    expected_entities: int,
    expected_entity_counts: Mapping[str, int],
) -> None:
    """Verify HA storage metadata without printing raw storage data."""
    config_entries = safe_storage_items(
        config_dir,
        "core.config_entries",
        "entries",
        report,
    )
    device_entries = safe_storage_items(
        config_dir,
        "core.device_registry",
        "devices",
        report,
    )
    entity_entries = safe_storage_items(
        config_dir,
        "core.entity_registry",
        "entities",
        report,
    )
    if config_entries is None or device_entries is None or entity_entries is None:
        return

    entries = [
        entry
        for entry in config_entries
        if entry.get("domain") == DOMAIN
    ]
    enabled_entries = [
        entry for entry in entries if entry.get("disabled_by") in (None, "")
    ]
    if len(enabled_entries) != expected_config_entries:
        report.fail(
            "config entry count mismatch: "
            f"expected {expected_config_entries}, got {len(enabled_entries)}"
        )
    else:
        report.fact(f"enabled config entries: {len(enabled_entries)}")
    report.metric("config_entries", len(enabled_entries))
    verify_config_entry_migration(enabled_entries, report)
    verify_config_entry_titles(enabled_entries, report)
    verify_config_entry_unique_ids(enabled_entries, report)
    verify_config_entry_options(enabled_entries, report)

    devices = [
        device
        for device in device_entries
        if _is_yeelight_device(device)
    ]
    if len(devices) < expected_devices:
        report.fail(
            "device count below minimum: "
            f"expected at least {expected_devices}, got {len(devices)}"
        )
    else:
        report.fact(f"device registry entries: {len(devices)}")
    report.metric("devices", len(devices))
    _verify_device_registry_quality(devices, report)

    counts = _entity_counts(entity_entries)
    entity_total = sum(counts.values())
    if entity_total != expected_entities:
        report.fail(f"entity count mismatch: expected {expected_entities}, got {entity_total}")
    else:
        report.fact(f"entity registry entries: {entity_total}")
    report.metric("entities", entity_total)

    if counts.get("text", 0):
        report.fail("text entities are present for Yeelight Pro")
    else:
        report.fact("text entities: 0")

    expected_counts = Counter(expected_entity_counts)
    if Counter(counts) != expected_counts:
        report.fail(
            "entity domain distribution mismatch: "
            f"expected {dict(sorted(expected_counts.items()))}, "
            f"got {dict(sorted(counts.items()))}"
        )
    else:
        report.fact(f"entity domains: {dict(sorted(counts.items()))}")
    report.metric("entity_domains", dict(sorted(counts.items())))
    _verify_entity_device_links(entity_entries, report)
    verify_platform_options_alignment(enabled_entries, counts, report)


def verify_product_schema_cache(config_dir: Path, report: VerificationReport) -> None:
    """Verify product schema cache privacy if the cache exists."""
    cache_path = storage_path(config_dir, "yeelight_pro.product_schemas")
    if not cache_path.exists():
        report.fact("product schema cache storage not present yet")
        return

    try:
        cache = read_json(cache_path)
    except (OSError, ValueError) as err:
        report.fail(f"product schema cache could not be read: {type(err).__name__}")
        return

    storage_data = cache.get("data", cache)
    if not isinstance(storage_data, Mapping):
        report.fail("product schema cache data is not an object")
        return
    if set(storage_data) != {"schemas"}:
        unexpected = sorted(str(key) for key in set(storage_data) - {"schemas"})
        report.fail(
            "product schema cache has unexpected top-level fields: "
            f"{unexpected}"
        )
        return
    schemas = storage_data.get("schemas")
    if not isinstance(schemas, Mapping):
        report.fail("product schema cache schemas field is not an object")
        return
    invalid_schema_keys = [
        str(key) for key, schema in schemas.items() if not isinstance(schema, Mapping)
    ]
    if invalid_schema_keys:
        report.fail(
            "product schema cache schema values are not objects: "
            f"{sorted(invalid_schema_keys)}"
        )
        return

    hits = sorted(sensitive_cache_hits(schemas))
    if hits:
        report.fail(f"product schema cache contains sensitive markers: {hits}")
    else:
        schema_count = len(schemas)
        report.fact("product schema cache contains no sensitive markers")
        report.fact(f"product schema cache schema count: {schema_count}")
        report.metric("product_schema_cache", {"schema_count": schema_count})


def _is_yeelight_device(device: Mapping[str, Any]) -> bool:
    """Return true when a device registry entry belongs to Yeelight Pro."""
    identifiers = device.get("identifiers")
    if not isinstance(identifiers, list):
        return False
    for identifier in identifiers:
        if (
            isinstance(identifier, (list, tuple))
            and identifier
            and identifier[0] == DOMAIN
        ):
            return True
    return False


def _entity_counts(entities: Iterable[Mapping[str, Any]]) -> Counter[str]:
    """Return entity-domain counts for Yeelight Pro registry entries."""
    counter: Counter[str] = Counter()
    for entity in entities:
        if entity.get("platform") != DOMAIN:
            continue
        entity_id = entity.get("entity_id")
        if not isinstance(entity_id, str) or "." not in entity_id:
            counter["unknown"] += 1
            continue
        counter[entity_id.split(".", 1)[0]] += 1
    return counter


def _verify_device_registry_quality(
    devices: list[Mapping[str, Any]],
    report: VerificationReport,
) -> None:
    """Verify source devices expose friendly metadata in HA's registry."""
    source_devices = [device for device in devices if _is_source_device(device)]
    if not source_devices:
        report.fail("device registry has no Yeelight Pro source devices")
        report.metric(
            "device_registry_quality",
            {
                "source_devices": 0,
                "missing_name": 0,
                "missing_model": 0,
                "missing_area": 0,
            },
        )
        return

    missing_name = sum(1 for device in source_devices if not _device_name(device))
    missing_model = sum(1 for device in source_devices if not device.get("model"))
    missing_area = sum(
        1
        for device in source_devices
        if not device.get("area_id") and not device.get("suggested_area")
    )
    if missing_name:
        report.fail(
            "device registry source devices missing friendly names: "
            f"{missing_name}/{len(source_devices)}"
        )
    if missing_model:
        report.fail(
            "device registry source devices missing model metadata: "
            f"{missing_model}/{len(source_devices)}"
        )
    if missing_area:
        report.fail(
            "device registry source devices missing area metadata: "
            f"{missing_area}/{len(source_devices)}"
        )
    if not missing_name and not missing_model and not missing_area:
        report.fact(
            "device registry source metadata: "
            f"{len(source_devices)} named/modelled/area-linked devices"
        )
    report.metric(
        "device_registry_quality",
        {
            "source_devices": len(source_devices),
            "missing_name": missing_name,
            "missing_model": missing_model,
            "missing_area": missing_area,
        },
    )


def _verify_entity_device_links(
    entities: Iterable[Mapping[str, Any]],
    report: VerificationReport,
) -> None:
    """Verify device-backed Yeelight entities are linked to HA devices."""
    device_backed_entries = [
        entity
        for entity in entities
        if entity.get("platform") == DOMAIN
        and _source_device_id_from_unique_id(entity.get("unique_id"))
    ]
    missing_device_id = sum(
        1 for entity in device_backed_entries if not entity.get("device_id")
    )
    if missing_device_id:
        report.fail(
            "device-backed entity registry entries missing device_id: "
            f"{missing_device_id}/{len(device_backed_entries)}"
        )
    elif device_backed_entries:
        report.fact(
            "device-backed entity registry links: "
            f"{len(device_backed_entries)} linked"
        )
    report.metric(
        "entity_device_links",
        {
            "device_backed_entities": len(device_backed_entries),
            "missing_device_id": missing_device_id,
        },
    )


def _is_source_device(device: Mapping[str, Any]) -> bool:
    """Return true for source devices, excluding house/gateway aggregate entries."""
    identifiers = device.get("identifiers")
    if not isinstance(identifiers, list):
        return False
    for identifier in identifiers:
        if not (
            isinstance(identifier, (list, tuple))
            and len(identifier) == 2
            and identifier[0] == DOMAIN
        ):
            continue
        value = str(identifier[1])
        if value.startswith("device:"):
            return True
    return False


def _device_name(device: Mapping[str, Any]) -> str | None:
    """Return the effective HA device display name."""
    for key in ("name_by_user", "name"):
        value = device.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _source_device_id_from_unique_id(value: Any) -> str | None:
    """Extract source device id from Yeelight entity unique_id."""
    if not isinstance(value, str):
        return None
    prefix = f"{DOMAIN}_"
    if not value.startswith(prefix):
        return None
    source_device_id = value[len(prefix):].split("_", 1)[0]
    return source_device_id if source_device_id.isdigit() else None
