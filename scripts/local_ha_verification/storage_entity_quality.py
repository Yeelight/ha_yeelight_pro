"""Entity-registry quality checks for local HA verification."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from .constants import DOMAIN
from .report import VerificationReport
from .storage_helpers import read_json, storage_path

UNFRIENDLY_PROPERTY_NAMES = frozenset({
    "default duration",
    "power on boot",
    "slisaon",
    "indicator switch",
    "run speed",
    "reverse direction",
    "open type",
    "ac remote controller",
    "ac deflector",
    "sense range",
    "luminance setting",
    "delay time",
    "switch power on boot",
    "device type after relay switch",
})


def verify_entity_registry_quality(
    config_dir: Path,
    entities: Iterable[Mapping[str, Any]],
    report: VerificationReport,
) -> None:
    """Verify Yeelight entities render as useful HA device-page groups."""
    entity_entries = list(entities)
    fail_enabled_legacy_scene_entities(entity_entries, report)
    _verify_entity_category_distribution(entity_entries, report)
    _verify_static_select_metadata(entity_entries, report)
    _verify_entity_friendly_names(entity_entries, report)
    _verify_entity_device_links(entity_entries, report)
    _verify_yeelight_restore_state(config_dir, entity_entries, report)


def fail_enabled_legacy_scene_entities(
    entities: Iterable[Mapping[str, Any]],
    report: VerificationReport,
) -> None:
    """Reject retained scene registry entries that still affect the UI."""
    enabled_scene_count = sum(
        1
        for entity in entities
        if entity.get("platform") == DOMAIN
        and entity_domain(entity) == "scene"
        and entity.get("disabled_by") in (None, "")
    )
    if enabled_scene_count:
        report.fail(
            "legacy native scene registry entries are still enabled; "
            "run yeelight_pro.cleanup_registry dry-run and confirm to disable stale entries: "
            f"{enabled_scene_count}"
        )


def entity_domain(entity: Mapping[str, Any]) -> str | None:
    """Return the HA entity domain from an entity registry item."""
    entity_id = entity.get("entity_id")
    if not isinstance(entity_id, str) or "." not in entity_id:
        return None
    return entity_id.split(".", 1)[0]


def source_device_id_from_unique_id(value: Any) -> str | None:
    """Extract source device id from Yeelight device-backed entity unique_id."""
    if not isinstance(value, str):
        return None
    prefix = f"{DOMAIN}_"
    if not value.startswith(prefix):
        return None
    suffix = value[len(prefix):]
    marker = "_device_"
    if marker in suffix:
        source_device_id = suffix.rsplit(marker, 1)[-1].split("_", 1)[0]
        return source_device_id if source_device_id.isdigit() else None
    if suffix.endswith(("_select_room", "_select_group", "_select_scene")):
        return None
    source_device_id = suffix.split("_", 1)[0]
    return source_device_id if source_device_id.isdigit() else None


def _verify_static_select_metadata(
    entities: Iterable[Mapping[str, Any]],
    report: VerificationReport,
) -> None:
    """Verify house-level selector entities keep user-facing names."""
    expected_metadata = {
        "select_room": ("当前房间", "active_room"),
        "select_group": ("当前灯组", "active_group"),
        "select_scene": ("当前场景", "active_scene"),
    }
    found: dict[str, tuple[str | None, str | None]] = {}
    for entity in entities:
        if entity.get("platform") != DOMAIN or entity_domain(entity) != "select":
            continue
        unique_id = entity.get("unique_id")
        if not isinstance(unique_id, str):
            continue
        selector = next(
            (key for key in expected_metadata if unique_id.endswith(key)),
            None,
        )
        if selector is None:
            continue
        found[selector] = (_entity_original_name(entity), _entity_translation_key(entity))

    missing = sorted(set(expected_metadata) - set(found))
    wrong = []
    for selector, (actual_name, actual_translation_key) in found.items():
        expected_name, expected_translation_key = expected_metadata[selector]
        if actual_name != expected_name and actual_translation_key != expected_translation_key:
            wrong.append(selector)
    if missing:
        report.fail(
            "house selector entity registry entries missing friendly metadata: "
            f"{len(missing)}/{len(expected_metadata)}"
        )
    if wrong:
        report.fail(
            "house selector entity registry entries have unfriendly names: "
            f"{len(wrong)}/{len(expected_metadata)}"
        )
    if not missing and not wrong:
        report.fact("house selector entity metadata: friendly names present")


def _verify_entity_category_distribution(
    entities: Iterable[Mapping[str, Any]],
    report: VerificationReport,
) -> None:
    """Verify HA device pages can separate config and diagnostic entities."""
    counts: Counter[str] = Counter()
    for entity in entities:
        if entity.get("platform") != DOMAIN:
            continue
        category = entity.get("entity_category")
        if isinstance(category, str) and category:
            counts[category] += 1
    missing = sorted({"config", "diagnostic"} - set(counts))
    if missing:
        report.fail(f"entity registry category distribution missing HA groups: {missing}")
    else:
        report.fact(f"entity registry categories: {dict(sorted(counts.items()))}")
    report.metric("entity_registry_categories", dict(sorted(counts.items())))


def _verify_entity_device_links(
    entities: Iterable[Mapping[str, Any]],
    report: VerificationReport,
) -> None:
    """Verify device-backed Yeelight entities are linked to HA devices."""
    device_backed_entries = [
        entity
        for entity in entities
        if entity.get("platform") == DOMAIN
        and source_device_id_from_unique_id(entity.get("unique_id"))
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


def _verify_entity_friendly_names(
    entities: Iterable[Mapping[str, Any]],
    report: VerificationReport,
) -> None:
    """Verify projected Yeelight entities do not keep raw numeric channel names."""
    checked = 0
    unfriendly = 0
    for entity in entities:
        if entity.get("platform") != DOMAIN:
            continue
        if entity.get("disabled_by") not in (None, ""):
            continue
        domain = entity_domain(entity)
        if domain not in {"button", "event", "light", "number", "select", "switch"}:
            continue
        checked += 1
        if _has_unfriendly_entity_name(entity):
            unfriendly += 1
    if unfriendly:
        report.fail(
            "entity registry entries still use raw channel/action/property names: "
            f"{unfriendly}/{checked}"
        )
    elif checked:
        report.fact(f"entity registry friendly action/control names: {checked} checked")
    report.metric("entity_friendly_names", {"checked": checked, "unfriendly": unfriendly})


def _verify_yeelight_restore_state(
    config_dir: Path,
    entities: Iterable[Mapping[str, Any]],
    report: VerificationReport,
) -> None:
    """Verify restored Yeelight runtime states are not broadly unavailable."""
    restore_path = storage_path(config_dir, "core.restore_state")
    if not restore_path.exists():
        report.fact("restore state storage not present yet")
        return
    try:
        restore_state = read_json(restore_path)
    except (OSError, ValueError) as err:
        report.fail(f"restore state storage could not be read: {type(err).__name__}")
        return

    yeelight_entity_ids = {
        entity_id
        for entity in entities
        if entity.get("platform") == DOMAIN
        and isinstance((entity_id := entity.get("entity_id")), str)
    }
    data = restore_state.get("data")
    restored_items = [
        item
        for item in (data if isinstance(data, list) else [])
        if isinstance(item, Mapping)
    ]
    yeelight_states = [
        item
        for item in restored_items
        if _restore_state_entity_id(item) in yeelight_entity_ids
    ]
    unavailable = sum(
        1 for item in yeelight_states if _restore_state_value(item) == "unavailable"
    )
    if unavailable:
        report.fail(
            "Yeelight Pro restored states are unavailable: "
            f"{unavailable}/{len(yeelight_states)}"
        )
    elif yeelight_states:
        report.fact(
            "Yeelight Pro restored states: "
            f"{len(yeelight_states)} present, 0 unavailable"
        )
    else:
        report.fact("Yeelight Pro restored states not present yet")
    report.metric(
        "yeelight_restore_state",
        {"restored": len(yeelight_states), "unavailable": unavailable},
    )


def _entity_original_name(entity: Mapping[str, Any]) -> str | None:
    """Return a stripped original name from an entity registry item."""
    value = entity.get("original_name")
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _entity_translation_key(entity: Mapping[str, Any]) -> str | None:
    """Return a stripped translation key from an entity registry item."""
    value = entity.get("translation_key")
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _has_unfriendly_entity_name(entity: Mapping[str, Any]) -> bool:
    """Return true for raw numeric labels that leak implementation channels."""
    for key in ("original_name", "name", "name_by_user"):
        value = entity.get(key)
        if not isinstance(value, str):
            continue
        text = value.strip()
        if _is_unfriendly_generated_name(text, entity_domain(entity)):
            return True
    return False


def _is_unfriendly_generated_name(text: str, domain: str | None) -> bool:
    """Return true for generated names that should be replaced by device-aware names."""
    normalized = text.replace(" ", "")
    normalized_words = " ".join(text.lower().replace("_", " ").split())
    if normalized_words in UNFRIENDLY_PROPERTY_NAMES:
        return True
    if any(
        normalized_words.endswith(f" {name}")
        for name in UNFRIENDLY_PROPERTY_NAMES
    ):
        return True
    if normalized.isdigit() or normalized in {"1", "2", "3", "4", "5", "6"}:
        return True
    if domain == "switch" and normalized in {
        "一键",
        "二键",
        "三键",
        "四键",
        "五键",
        "六键",
        "1键",
        "2键",
        "3键",
        "4键",
        "5键",
        "6键",
    }:
        return True
    return domain == "light" and normalized == "照明"


def _restore_state_entity_id(item: Mapping[str, Any]) -> str | None:
    """Return entity_id from a HA restore-state item."""
    state = item.get("state")
    if not isinstance(state, Mapping):
        return None
    entity_id = state.get("entity_id")
    return entity_id if isinstance(entity_id, str) else None


def _restore_state_value(item: Mapping[str, Any]) -> str | None:
    """Return state value from a HA restore-state item."""
    state = item.get("state")
    if not isinstance(state, Mapping):
        return None
    value = state.get("state")
    return value if isinstance(value, str) else None


__all__ = [
    "entity_domain",
    "fail_enabled_legacy_scene_entities",
    "source_device_id_from_unique_id",
    "verify_entity_registry_quality",
]
