"""Home Assistant config-entry storage verification helpers."""

from __future__ import annotations

import ast
import hashlib
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from .constants import SOURCE_COMPONENT_ROOT
from .report import VerificationReport

CONNECTION_MODE_CLOUD = "cloud"
CONNECTION_MODE_PRIVATE = "private"
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


def verify_config_entry_migration(
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


def verify_config_entry_unique_ids(
    entries: Iterable[Mapping[str, Any]],
    report: VerificationReport,
) -> None:
    """Verify stored entry unique ids keep region/account/house isolation."""
    invalid_count = 0
    cloud_count = 0
    private_count = 0
    for entry in entries:
        expected_unique_id = _expected_config_entry_unique_id(entry)
        if expected_unique_id is None:
            invalid_count += 1
            continue
        if expected_unique_id.startswith(f"{CONNECTION_MODE_CLOUD}:"):
            cloud_count += 1
        if expected_unique_id.startswith(f"{CONNECTION_MODE_PRIVATE}:"):
            private_count += 1
        if entry.get("unique_id") != expected_unique_id:
            invalid_count += 1

    if invalid_count:
        report.fail(
            "config entry unique_id isolation mismatch: "
            f"{invalid_count} enabled entry/entries"
        )
    else:
        report.fact(
            "config entry unique_id isolation: "
            f"cloud={cloud_count}, private={private_count}"
        )
    report.metric(
        "config_entry_unique_ids",
        {
            "cloud": cloud_count,
            "private": private_count,
            "invalid": invalid_count,
        },
    )


def _expected_config_entry_unique_id(entry: Mapping[str, Any]) -> str | None:
    """Return expected unique id without exposing account or house values."""
    data = entry.get("data")
    if not isinstance(data, Mapping):
        return None
    connection_mode = data.get("connection_mode")
    house_id = data.get("house_id")
    if connection_mode == CONNECTION_MODE_CLOUD:
        cloud_region = data.get("cloud_region")
        account_key = _account_key(data)
        if not _has_value(cloud_region) or not _has_value(house_id) or account_key is None:
            return None
        return f"{CONNECTION_MODE_CLOUD}:{cloud_region}:{account_key}:{house_id}"
    if connection_mode == CONNECTION_MODE_PRIVATE:
        private_domain = data.get("private_domain")
        if not _has_value(private_domain) or not _has_value(house_id):
            return None
        return f"{CONNECTION_MODE_PRIVATE}:{private_domain}:{house_id}"
    return None


def _account_key(data: Mapping[str, Any]) -> str | None:
    """Return strongest non-sensitive account key from stored entry data."""
    for key in ("account_user_id", "account_username", "oauth_client_id"):
        value = data.get(key)
        if _has_value(value):
            return str(value).strip()
    access_token = data.get("access_token")
    if isinstance(access_token, str) and access_token.strip():
        digest = hashlib.sha256(access_token.strip().encode("utf-8")).hexdigest()[:16]
        return f"token-{digest}"
    return None


def _has_value(value: Any) -> bool:
    """Return whether a storage value can participate in unique-id generation."""
    return value not in (None, "")


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
