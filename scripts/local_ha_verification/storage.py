"""Home Assistant storage verification."""

from __future__ import annotations

import ast
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from .constants import DOMAIN, SOURCE_COMPONENT_ROOT
from .options import verify_config_entry_options
from .platforms import verify_platform_options_alignment
from .report import VerificationReport
from .storage_helpers import read_json, safe_storage_items, sensitive_cache_hits, storage_path

REQUIRED_CONFIG_ENTRY_DATA_KEYS = {
    "access_token",
    "cloud_domain",
    "cloud_region",
    "connection_mode",
    "house_id",
    "private_domain",
}
OPTIONAL_CONFIG_ENTRY_DATA_KEYS = {
    "account_user_id",
    "account_username",
    "oauth_client_id",
    "refresh_token",
    "scan_login_device",
    "token_expires_in",
    "token_type",
}


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
    _verify_config_entry_migration(enabled_entries, report)
    verify_config_entry_options(enabled_entries, report)

    devices = [
        device
        for device in device_entries
        if _is_yeelight_device(device)
    ]
    if len(devices) != expected_devices:
        report.fail(f"device count mismatch: expected {expected_devices}, got {len(devices)}")
    else:
        report.fact(f"device registry entries: {len(devices)}")
    report.metric("devices", len(devices))

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


def _verify_config_entry_migration(
    entries: Iterable[Mapping[str, Any]],
    report: VerificationReport,
) -> None:
    """Verify installed Yeelight Pro config entries are migrated without raw output."""
    entry_list = list(entries)
    if not entry_list:
        return

    expected_version = _expected_entry_version()
    if expected_version is None:
        report.fail("entry migration version constants are not literal")
        return

    versions = Counter(
        (
            _int_or_zero(entry.get("version")),
            _int_or_zero(entry.get("minor_version")),
        )
        for entry in entry_list
    )
    if set(versions) != {expected_version}:
        report.fail(
            "config entry migration version mismatch: "
            f"expected {expected_version}, got {dict(sorted(versions.items()))}"
        )
    else:
        report.fact(
            "config entry versions: "
            f"{expected_version[0]}.{expected_version[1]} x {versions[expected_version]}"
        )
    report.metric("config_entry_versions", dict(sorted(versions.items())))

    missing_by_key = _missing_config_entry_keys(entry_list)
    if missing_by_key:
        report.fail(f"config entry data missing required keys: {missing_by_key}")
    else:
        report.fact(
            "config entry required data keys present: "
            f"{sorted(REQUIRED_CONFIG_ENTRY_DATA_KEYS)}"
        )
    optional_missing_by_key = _missing_config_entry_keys(
        entry_list,
        required_keys=OPTIONAL_CONFIG_ENTRY_DATA_KEYS,
    )
    if optional_missing_by_key:
        report.fact(f"config entry optional data keys absent: {optional_missing_by_key}")
    else:
        report.fact(
            "config entry optional data keys present: "
            f"{sorted(OPTIONAL_CONFIG_ENTRY_DATA_KEYS)}"
        )
    report.metric("optional_config_entry_missing_keys", optional_missing_by_key)


def _missing_config_entry_keys(
    entries: Iterable[Mapping[str, Any]],
    *,
    required_keys: set[str] = REQUIRED_CONFIG_ENTRY_DATA_KEYS,
) -> dict[str, int]:
    """Return required config-entry data keys missing from enabled entries."""
    missing_counter: Counter[str] = Counter()
    for entry in entries:
        data = entry.get("data")
        if not isinstance(data, Mapping):
            for key in required_keys:
                missing_counter[key] += 1
            continue
        for key in required_keys:
            if key not in data:
                missing_counter[key] += 1
    return dict(sorted(missing_counter.items()))


def _int_or_zero(value: Any) -> int:
    """Return an int value from HA storage version fields."""
    return value if isinstance(value, int) else 0


def _expected_entry_version() -> tuple[int, int] | None:
    """Read migration version constants without importing Home Assistant."""
    constants = _literal_module_ints(
        SOURCE_COMPONENT_ROOT / "entry_migration.py",
        {"ENTRY_VERSION", "ENTRY_MINOR_VERSION"},
    )
    version = constants.get("ENTRY_VERSION")
    minor_version = constants.get("ENTRY_MINOR_VERSION")
    if version is None or minor_version is None:
        return None
    return (version, minor_version)


def _literal_module_ints(path: Path, names: set[str]) -> dict[str, int]:
    """Return selected module-level integer constants from a Python source file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    values: dict[str, int] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not isinstance(node.value, ast.Constant) or not isinstance(node.value.value, int):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in names:
                values[target.id] = node.value.value
    return values


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
