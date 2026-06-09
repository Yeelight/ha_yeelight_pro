"""Explicit stale entity cleanup helpers for Yeelight Pro."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
from collections.abc import Mapping
from typing import Any, Protocol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .const import DOMAIN
from .entity_candidates import EntityCandidateCoordinator, EntityKey
from .ha_device_registry import active_device_identifiers

_LAST_CLEANUP_AUDIT = "_yeelight_pro_last_entity_registry_cleanup_audit"


class RegistryCleanupCoordinator(EntityCandidateCoordinator, Protocol):
    """Cleanup helpers need entity candidates plus device-registry topology."""

    def get_gateway_devices(self) -> Mapping[Any, Mapping[str, Any]]:
        """Return normalized gateway payloads for active device detection."""


@dataclass(frozen=True, slots=True)
class EntityRegistryCleanupAudit:
    """Aggregate cleanup audit result without registry identifiers."""

    audit_id: str
    status: str
    stale_entities: int
    stale_devices: int
    disabled_entities: int
    skipped_entities: int
    entity_domains: dict[str, int]

    def as_diagnostics(self) -> dict[str, Any]:
        """Return a diagnostics-safe aggregate payload."""
        return {
            "audit_id": self.audit_id,
            "status": self.status,
            "stale_entities": self.stale_entities,
            "stale_devices": self.stale_devices,
            "disabled_entities": self.disabled_entities,
            "skipped_entities": self.skipped_entities,
            "entity_domains": dict(self.entity_domains),
        }


@dataclass(frozen=True, slots=True)
class EntityRegistryCleanupPreview:
    """Dry-run result for explicit stale entity cleanup."""

    audit_id: str
    stale_entity_count: int
    stale_device_count: int
    entity_domains: dict[str, int]
    entries: tuple[er.RegistryEntry, ...]

    def as_service_response(self) -> dict[str, Any]:
        """Return a response payload safe for HA service callers."""
        return {
            "audit_id": self.audit_id,
            "stale_entities": self.stale_entity_count,
            "stale_devices": self.stale_device_count,
            "entity_domains": dict(self.entity_domains),
            "action": "dry_run",
        }


async def async_preview_stale_registry_cleanup(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: RegistryCleanupCoordinator,
) -> EntityRegistryCleanupPreview:
    """Build an explicit dry-run preview for stale registry cleanup."""
    from .entity_lifecycle import collect_active_entity_keys

    active_entity_keys = collect_active_entity_keys(coordinator)
    _registry_entries, stale_entries = _collect_registry_entries(
        hass,
        entry,
        active_entity_keys,
    )
    stale_devices = _stale_device_keys(hass, entry, coordinator)
    entries = tuple(
        registry_entry
        for _key, registry_entry in sorted(stale_entries.items(), key=lambda item: item[0])
    )
    preview = EntityRegistryCleanupPreview(
        audit_id=_cleanup_audit_id(entry, stale_entries, stale_devices),
        stale_entity_count=len(entries),
        stale_device_count=len(stale_devices),
        entity_domains=_domain_counts(entries),
        entries=entries,
    )
    _record_cleanup_audit(
        coordinator,
        audit_id=preview.audit_id,
        status="dry_run",
        stale_entities=preview.stale_entity_count,
        stale_devices=preview.stale_device_count,
        disabled_entities=0,
        skipped_entities=0,
        entity_domains=preview.entity_domains,
    )
    return preview


async def async_disable_stale_registry_entities(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: RegistryCleanupCoordinator,
    *,
    audit_id: str,
) -> EntityRegistryCleanupAudit:
    """Disable stale entity registry entries after matching a dry-run audit."""
    previous_audit = getattr(coordinator, _LAST_CLEANUP_AUDIT, None)
    preview = await async_preview_stale_registry_cleanup(hass, entry, coordinator)
    if not _audit_matches(previous_audit, audit_id, preview.audit_id):
        _record_cleanup_audit(
            coordinator,
            audit_id=preview.audit_id,
            status="rejected",
            stale_entities=preview.stale_entity_count,
            stale_devices=preview.stale_device_count,
            disabled_entities=0,
            skipped_entities=preview.stale_entity_count,
            entity_domains=preview.entity_domains,
        )
        raise ValueError("cleanup audit id does not match the current dry-run result")

    disabled = 0
    skipped = 0
    entity_registry = er.async_get(hass)
    for registry_entry in preview.entries:
        if getattr(registry_entry, "disabled_by", None) is not None:
            skipped += 1
            continue
        entity_registry.async_update_entity(
            registry_entry.entity_id,
            disabled_by=er.RegistryEntryDisabler.INTEGRATION,
        )
        disabled += 1

    audit = _record_cleanup_audit(
        coordinator,
        audit_id=preview.audit_id,
        status="confirmed",
        stale_entities=preview.stale_entity_count,
        stale_devices=preview.stale_device_count,
        disabled_entities=disabled,
        skipped_entities=skipped,
        entity_domains=preview.entity_domains,
    )
    from .entity_lifecycle import _pending_stale_entity_keys

    _pending_stale_entity_keys(coordinator).difference_update(_entry_keys(preview.entries))
    return audit


def entity_registry_cleanup_diagnostics(
    coordinator: Any,
) -> dict[str, Any] | None:
    """Return the last aggregate cleanup audit without registry identifiers."""
    audit = getattr(coordinator, _LAST_CLEANUP_AUDIT, None)
    return audit.as_diagnostics() if isinstance(audit, EntityRegistryCleanupAudit) else None


def _collect_registry_entries(
    hass: HomeAssistant,
    entry: ConfigEntry,
    active_entity_keys: set[EntityKey],
) -> tuple[list[er.RegistryEntry], dict[EntityKey, er.RegistryEntry]]:
    """Collect owned registry entries and stale candidates."""
    from .entity_lifecycle import _registry_entry_disabled_by_user, _registry_entry_domain

    entity_registry = er.async_get(hass)
    registry_entries: list[er.RegistryEntry] = []
    stale_entries: dict[EntityKey, er.RegistryEntry] = {}
    for registry_entry in er.async_entries_for_config_entry(entity_registry, entry.entry_id):
        registry_domain = _registry_entry_domain(registry_entry)
        if (
            registry_domain is None
            or registry_entry.platform != DOMAIN
            or not registry_entry.unique_id.startswith(f"{DOMAIN}_")
        ):
            continue
        registry_entries.append(registry_entry)
        registry_key = (registry_domain, registry_entry.unique_id)
        if registry_key not in active_entity_keys and not _registry_entry_disabled_by_user(
            registry_entry
        ):
            stale_entries[registry_key] = registry_entry
    return (registry_entries, stale_entries)


def _audit_matches(
    previous_audit: Any,
    audit_id: str,
    current_audit_id: str,
) -> bool:
    """Return true when confirm matches the last dry-run and current result."""
    return (
        isinstance(previous_audit, EntityRegistryCleanupAudit)
        and previous_audit.status == "dry_run"
        and previous_audit.audit_id == audit_id
        and audit_id == current_audit_id
    )


def _cleanup_audit_id(
    entry: ConfigEntry,
    stale_entries: dict[EntityKey, er.RegistryEntry],
    stale_device_keys: set[tuple[str, ...]],
) -> str:
    """Build a deterministic audit id for the current stale registry set."""
    digest = sha256(str(entry.entry_id).encode())
    for key in sorted(stale_device_keys):
        digest.update(f"|device:{':'.join(key)}".encode())
    for domain, unique_id in sorted(stale_entries):
        digest.update(f"|{domain}:{unique_id}".encode())
    return digest.hexdigest()[:16]


def _domain_counts(entries: tuple[er.RegistryEntry, ...]) -> dict[str, int]:
    """Return aggregate domain counts for stale registry entries."""
    from .entity_lifecycle import _registry_entry_domain

    counts = Counter(
        domain
        for item in entries
        if (domain := _registry_entry_domain(item)) is not None
    )
    return dict(sorted(counts.items()))


def _entry_keys(entries: tuple[er.RegistryEntry, ...]) -> set[EntityKey]:
    """Return domain-scoped keys for registry entries with a domain."""
    from .entity_lifecycle import _registry_entry_domain

    return {
        (domain, item.unique_id)
        for item in entries
        if (domain := _registry_entry_domain(item)) is not None
    }


def _stale_device_keys(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: RegistryCleanupCoordinator,
) -> set[tuple[str, ...]]:
    """Return deterministic keys for stale Yeelight Pro device entries."""
    device_registry = dr.async_get(hass)
    active_identifiers = active_device_identifiers(coordinator)
    stale_keys: set[tuple[str, ...]] = set()
    for device_entry in dr.async_entries_for_config_entry(device_registry, entry.entry_id):
        yeelight_identifiers = {
            identifier
            for identifier in getattr(device_entry, "identifiers", set())
            if identifier[0] == DOMAIN
        }
        if not yeelight_identifiers or yeelight_identifiers & active_identifiers:
            continue
        stale_keys.add(tuple(
            f"{domain}:{identifier}"
            for domain, identifier in sorted(yeelight_identifiers)
        ))
    return stale_keys


def _record_cleanup_audit(
    coordinator: Any,
    *,
    audit_id: str,
    status: str,
    stale_entities: int,
    stale_devices: int,
    disabled_entities: int,
    skipped_entities: int,
    entity_domains: dict[str, int],
) -> EntityRegistryCleanupAudit:
    """Persist the last cleanup audit summary on the coordinator."""
    audit = EntityRegistryCleanupAudit(
        audit_id=audit_id,
        status=status,
        stale_entities=stale_entities,
        stale_devices=stale_devices,
        disabled_entities=disabled_entities,
        skipped_entities=skipped_entities,
        entity_domains=dict(entity_domains),
    )
    setattr(coordinator, _LAST_CLEANUP_AUDIT, audit)
    return audit
