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
    "house_name",
    "private_domain",
}
OPTIONAL_CONFIG_ENTRY_DATA_KEYS = {
    "account_user_id",
    "account_username",
    "open_api_client_id",
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


def verify_config_entry_titles(
    entries: Iterable[Mapping[str, Any]],
    report: VerificationReport,
) -> None:
    """Verify stored entry titles are descriptive without exposing secrets."""
    invalid_count = 0
    placeholder_count = 0
    cloud_count = 0
    private_count = 0
    for entry in entries:
        expected_title = _expected_config_entry_title(entry)
        if expected_title is None:
            invalid_count += 1
            continue
        if _has_house_placeholder_name(entry):
            placeholder_count += 1
        if expected_title.startswith("Yeelight Pro Cloud"):
            cloud_count += 1
        if expected_title.startswith("Yeelight Pro Private"):
            private_count += 1
        if entry.get("title") != expected_title:
            invalid_count += 1

    if invalid_count or placeholder_count:
        report.fail(
            "config entry title or house name mismatch: "
            f"invalid={invalid_count}, placeholders={placeholder_count}"
        )
    else:
        report.fact(
            "config entry titles: "
            f"cloud={cloud_count}, private={private_count}"
        )
    report.metric(
        "config_entry_titles",
        {
            "cloud": cloud_count,
            "private": private_count,
            "invalid": invalid_count,
        },
    )


def _expected_config_entry_title(entry: Mapping[str, Any]) -> str | None:
    """Return expected user-visible title without exposing token or device values."""
    data = entry.get("data")
    if not isinstance(data, Mapping):
        return None
    connection_mode = data.get("connection_mode")
    house_id = data.get("house_id")
    if connection_mode == CONNECTION_MODE_CLOUD:
        cloud_region = data.get("cloud_region")
        if not _has_value(cloud_region) or not _has_value(house_id):
            return None
        account_label = _account_title_label(data)
        region_label = _region_title_label(cloud_region)
        parts = [
            part
            for part in (account_label, region_label, _house_title_label(data))
            if part
        ]
        return f"Yeelight Pro Cloud ({' · '.join(parts)})"
    if connection_mode == CONNECTION_MODE_PRIVATE:
        private_domain = data.get("private_domain")
        if not _has_value(private_domain) or not _has_value(house_id):
            return None
        return f"Yeelight Pro Private ({private_domain} · {_house_title_label(data)})"
    return None


def _house_title_label(data: Mapping[str, Any]) -> str:
    """Return stored friendly house name, never a raw house id."""
    house_name = data.get("house_name")
    if _has_value(house_name) and not _is_house_placeholder_name(house_name):
        return str(house_name).strip()
    return "易来家庭"


def _has_house_placeholder_name(entry: Mapping[str, Any]) -> bool:
    """Return whether title or stored data still uses generated house labels."""
    title = entry.get("title")
    data = entry.get("data")
    if _is_house_placeholder_name(title):
        return True
    if isinstance(data, Mapping):
        return _is_house_placeholder_name(data.get("house_name"))
    return False


def _is_house_placeholder_name(value: Any) -> bool:
    """Return true for labels such as House 123 or Yeelight Pro 123."""
    if not _has_value(value):
        return False
    text = str(value).strip().lower()
    parts = text.replace("(", " ").replace(")", " ").replace("·", " ").split()
    for index, part in enumerate(parts[:-1]):
        if part in {"house", "home", "project"} and _looks_like_identifier(parts[index + 1]):
            return True
        if (
            part == "yeelight"
            and index + 2 < len(parts)
            and parts[index + 1] == "pro"
            and _looks_like_identifier(parts[index + 2])
        ):
            return True
    return False


def has_generated_house_placeholder(value: Any) -> bool:
    """Return true for generated house labels in storage values."""
    return _is_house_placeholder_name(value)


def _looks_like_identifier(value: str) -> bool:
    """Return whether a title token looks like a generated id."""
    token = value.strip(",:;[]{}")
    return token.isdecimal() or any(char.isdigit() for char in token)


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
    for key in ("account_user_id", "account_username", "open_api_client_id"):
        value = data.get(key)
        if _has_value(value):
            return str(value).strip()
    access_token = data.get("access_token")
    if isinstance(access_token, str) and access_token.strip():
        digest = hashlib.sha256(access_token.strip().encode("utf-8")).hexdigest()[:16]
        return f"token-{digest}"
    return None


def _account_title_label(data: Mapping[str, Any]) -> str:
    """Return user-facing account label without exposing token fingerprints."""
    username = data.get("account_username")
    if _has_value(username):
        return str(username).strip()
    account_user_id = data.get("account_user_id")
    if _has_value(account_user_id):
        return f"UID {str(account_user_id).strip()}"
    return ""


def _region_title_label(value: Any) -> str:
    """Return a compact user-facing region label."""
    region = str(value).strip().lower()
    if region == "de":
        return "EU"
    return region.upper() or "CN"


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
