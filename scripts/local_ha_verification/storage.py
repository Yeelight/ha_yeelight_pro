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
from .storage_device_quality import verify_device_registry_quality
from .storage_entity_quality import verify_entity_registry_quality
from .storage_entries import (
    verify_config_entry_migration,
    verify_config_entry_titles,
    verify_config_entry_unique_ids,
)
from .storage_helpers import (
    read_json,
    safe_storage_items,
    sensitive_cache_hits,
    storage_path,
)


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
    verify_device_registry_quality(devices, report)

    counts = _entity_counts(entity_entries)
    entity_total = sum(counts.values())
    if entity_total < expected_entities:
        report.fail(
            "entity registry retained count below active baseline: "
            f"expected at least {expected_entities}, got {entity_total}"
        )
    else:
        report.fact(f"entity registry retained entries: {entity_total}")
    report.metric("retained_entities", entity_total)

    if counts.get("text", 0):
        report.fail("text entities are present for Yeelight Pro")
    else:
        report.fact("text entities: 0")
    expected_counts = Counter(expected_entity_counts)
    missing_counts = {
        domain: expected_count - counts.get(domain, 0)
        for domain, expected_count in expected_counts.items()
        if counts.get(domain, 0) < expected_count
    }
    if missing_counts:
        report.fail(
            "entity registry retained domain count below active baseline: "
            f"missing {dict(sorted(missing_counts.items()))}, "
            f"got {dict(sorted(counts.items()))}"
        )
    else:
        report.fact(f"entity registry retained domains: {dict(sorted(counts.items()))}")
    disabled_counts = _disabled_by_counts(entity_entries)
    report.fact(f"entity registry disabled_by: {dict(sorted(disabled_counts.items()))}")
    report.metric("retained_entity_domains", dict(sorted(counts.items())))
    report.metric("entity_registry_disabled_by", dict(sorted(disabled_counts.items())))
    verify_entity_registry_quality(config_dir, entity_entries, report)
    verify_platform_options_alignment(enabled_entries, expected_counts, report)


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


def _disabled_by_counts(entities: Iterable[Mapping[str, Any]]) -> Counter[str]:
    """Return disabled_by aggregate counts for Yeelight Pro registry entries."""
    counter: Counter[str] = Counter()
    for entity in entities:
        if entity.get("platform") != DOMAIN:
            continue
        disabled_by = entity.get("disabled_by")
        counter[str(disabled_by or "enabled")] += 1
    return counter
