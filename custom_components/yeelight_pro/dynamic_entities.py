"""Helpers for adding Yeelight Pro entities discovered after refresh."""
from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Callable, Iterable, Mapping
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import entity_registry as er

from .const import CONF_DEVICE_IMPORT_FILTER, DOMAIN
from .core.coordinator import YeelightProCoordinator
from .device_filter import matches_device_import_filter

EntityFactory = Callable[[YeelightProCoordinator], Iterable[Entity]]


def async_track_dynamic_entities(
    config_entry: ConfigEntry,
    coordinator: YeelightProCoordinator,
    async_add_entities: AddEntitiesCallback,
    entity_factory: EntityFactory,
    *,
    logger: logging.Logger,
    platform_name: str,
    entity_domain: str | None = None,
) -> None:
    """Add entities now and whenever coordinator refresh discovers new ones."""
    fallback_submitted_unique_ids: set[str] = set()
    last_topology_generation = _topology_generation(coordinator)
    entity_domain = entity_domain or _entity_domain(platform_name)

    @callback
    def _add_missing_entities() -> None:
        nonlocal last_topology_generation
        current_topology_generation = _topology_generation(coordinator)
        if (
            current_topology_generation is not None
            and current_topology_generation == last_topology_generation
        ):
            return
        last_topology_generation = current_topology_generation

        registry_entries = _registry_entries_by_unique_id(
            getattr(coordinator, "hass", None),
            config_entry,
            entity_domain,
        )
        batch_unique_ids: set[str] = set()
        new_entities: list[Entity] = []
        skip_counts: Counter[str] = Counter()
        candidate_count = 0
        for entity in entity_factory(coordinator):
            candidate_count += 1
            unique_id = _entity_unique_id(entity)
            if unique_id is None:
                logger.debug("Skipping %s entity without unique_id", platform_name)
                skip_counts["missing_unique_id"] += 1
                continue
            if unique_id in batch_unique_ids:
                skip_counts["duplicate_batch_unique_id"] += 1
                continue
            batch_unique_ids.add(unique_id)
            registry_entry = (
                None if registry_entries is None else registry_entries.get(unique_id)
            )
            if registry_entries is None:
                if unique_id in fallback_submitted_unique_ids:
                    skip_counts["already_submitted_without_registry"] += 1
                    continue
                fallback_submitted_unique_ids.add(unique_id)
            elif _registry_entry_owned_by_other_entry(registry_entry, config_entry):
                logger.debug(
                    "Skipping %s entity already owned by another config entry",
                    platform_name,
                )
                skip_counts["owned_by_other_config_entry"] += 1
                continue
            elif _should_skip_registered_entity(
                getattr(coordinator, "hass", None),
                registry_entry,
            ):
                skip_counts["registered_entity_active_or_disabled"] += 1
                continue
            elif registry_entry is None and not _matches_runtime_device_import_filter(
                coordinator,
                entity,
                unique_id,
            ):
                logger.debug(
                    "Skipping %s entity blocked by device import filter",
                    platform_name,
                )
                skip_counts["device_import_filter_blocked"] += 1
                continue
            new_entities.append(entity)

        _log_dynamic_entity_scan(
            logger,
            platform_name,
            candidate_count=candidate_count,
            added_count=len(new_entities),
            skip_counts=skip_counts,
            registry_available=registry_entries is not None,
            topology_generation=current_topology_generation,
        )
        if not new_entities:
            return

        async_add_entities(new_entities)
        logger.info("Added %s %s entities", len(new_entities), platform_name)

    last_topology_generation = None
    _add_missing_entities()
    config_entry.async_on_unload(coordinator.async_add_listener(_add_missing_entities))


def _log_dynamic_entity_scan(
    logger: logging.Logger,
    platform_name: str,
    *,
    candidate_count: int,
    added_count: int,
    skip_counts: Counter[str],
    registry_available: bool,
    topology_generation: int | None,
) -> None:
    """Log aggregate dynamic entity scan results without entity identifiers."""
    if not logger.isEnabledFor(logging.DEBUG):
        return
    logger.debug(
        "Dynamic Yeelight Pro entity scan: platform=%s candidates=%s added=%s "
        "skipped=%s registry_available=%s topology_generation=%s",
        platform_name,
        candidate_count,
        added_count,
        dict(sorted(skip_counts.items())),
        registry_available,
        topology_generation,
    )


def _entity_unique_id(entity: Entity) -> str | None:
    """Return an entity unique_id without requiring the entity to be added."""
    unique_id = getattr(entity, "unique_id", None)
    if isinstance(unique_id, str) and unique_id:
        return unique_id

    attr_unique_id = getattr(entity, "_attr_unique_id", None)
    if isinstance(attr_unique_id, str) and attr_unique_id:
        return attr_unique_id
    return None


def _topology_generation(coordinator: YeelightProCoordinator) -> int | None:
    """Return topology generation when the coordinator exposes it."""
    generation = getattr(coordinator, "topology_generation", None)
    return generation if isinstance(generation, int) else None


def _entity_domain(platform_name: str) -> str:
    """Normalize a platform display name to a HA entity domain."""
    return platform_name.strip().lower().replace(" ", "_")


def _registry_entries_by_unique_id(
    hass: HomeAssistant | None,
    config_entry: ConfigEntry,
    entity_domain: str,
) -> dict[str, er.RegistryEntry] | None:
    """Return Yeelight registry entries for this HA entity domain."""
    if hass is None:
        return None
    entity_registry = er.async_get(hass)
    entries = list(_registry_entries(entity_registry))
    if not entries:
        entries = er.async_entries_for_config_entry(
            entity_registry,
            config_entry.entry_id,
        )
    return {
        entry.unique_id: entry
        for entry in entries
        if entry.platform == DOMAIN and _registry_entry_domain(entry) == entity_domain
    }


def _registry_entries(entity_registry: er.EntityRegistry) -> Iterable[er.RegistryEntry]:
    """Return all known registry entries when HA exposes a global index."""
    entries = getattr(entity_registry, "entities", None)
    values = getattr(entries, "values", None)
    if callable(values):
        return values()
    return ()


def _registry_entry_owned_by_other_entry(
    registry_entry: er.RegistryEntry | None,
    config_entry: ConfigEntry,
) -> bool:
    """Return true when an existing entity belongs to another config entry."""
    if registry_entry is None:
        return False
    owner_entry_id = getattr(registry_entry, "config_entry_id", None)
    if not isinstance(owner_entry_id, str) or not owner_entry_id:
        return False
    return owner_entry_id != config_entry.entry_id


def _should_skip_registered_entity(
    hass: HomeAssistant | None,
    registry_entry: er.RegistryEntry | None,
) -> bool:
    """Return true when HA registry/runtime already owns this entity."""
    if registry_entry is None:
        return False
    if _registry_entry_disabled_by_user(registry_entry):
        return True
    disabled_by = getattr(registry_entry, "disabled_by", None)
    if _registry_entry_disabled_by_integration(registry_entry):
        _restore_integration_disabled_entry(hass, registry_entry)
    elif disabled_by is not None:
        return True
    entity_id = getattr(registry_entry, "entity_id", None)
    states = getattr(hass, "states", None)
    state_get = getattr(states, "get", None)
    if not isinstance(entity_id, str) or not callable(state_get):
        return False
    state = state_get(entity_id)
    if state is None:
        return False
    if _runtime_state_is_restored(state):
        return False
    return True


def _runtime_state_is_restored(state: Any) -> bool:
    """Return true when HA only restored an entity from registry history."""
    attributes = getattr(state, "attributes", None)
    return isinstance(attributes, Mapping) and attributes.get("restored") is True


def _registry_entry_disabled_by_user(registry_entry: er.RegistryEntry) -> bool:
    """Return whether the registry entry was explicitly disabled by the user."""
    return getattr(registry_entry, "disabled_by", None) in {
        er.RegistryEntryDisabler.USER,
        "user",
    }


def _registry_entry_disabled_by_integration(registry_entry: er.RegistryEntry) -> bool:
    """Return whether the registry entry was automatically disabled by this integration."""
    return getattr(registry_entry, "disabled_by", None) in {
        er.RegistryEntryDisabler.INTEGRATION,
        "integration",
    }


def _restore_integration_disabled_entry(
    hass: HomeAssistant | None,
    registry_entry: er.RegistryEntry,
) -> None:
    """Re-enable entries disabled by this integration when the entity is active again."""
    if not _registry_entry_disabled_by_integration(registry_entry):
        return
    entity_id = getattr(registry_entry, "entity_id", None)
    if hass is None or not isinstance(entity_id, str):
        return
    er.async_get(hass).async_update_entity(entity_id, disabled_by=None)


def _registry_entry_domain(registry_entry: Any) -> str | None:
    """Return the HA entity domain for a registry entry."""
    domain = getattr(registry_entry, "domain", None)
    if isinstance(domain, str) and domain:
        return domain
    entity_id = getattr(registry_entry, "entity_id", "")
    if isinstance(entity_id, str) and "." in entity_id:
        return entity_id.split(".", 1)[0]
    return None


def _matches_runtime_device_import_filter(
    coordinator: YeelightProCoordinator,
    entity: Entity,
    unique_id: str,
) -> bool:
    """Return true when an entity is allowed by the runtime device filter."""
    filter_config = _runtime_device_import_filter(coordinator)
    if not filter_config:
        return True

    device_payload = _entity_device_payload(coordinator, entity, unique_id)
    if device_payload is None:
        return True
    return matches_device_import_filter(device_payload, filter_config)


def _runtime_device_import_filter(
    coordinator: YeelightProCoordinator,
) -> Mapping[str, Any] | None:
    """Return configured device import filter when available."""
    options = getattr(coordinator, "options", None)
    if not isinstance(options, Mapping):
        return None
    filter_config = options.get(CONF_DEVICE_IMPORT_FILTER)
    return filter_config if isinstance(filter_config, Mapping) else None


def _entity_device_payload(
    coordinator: YeelightProCoordinator,
    entity: Entity,
    unique_id: str,
) -> dict[str, Any] | None:
    """Return source device payload for device-backed entities."""
    device_id = _entity_device_id(entity, unique_id)
    if device_id is None:
        return None

    get_device = getattr(coordinator, "get_device", None)
    if callable(get_device):
        device = get_device(device_id)
        if isinstance(device, dict):
            return device

    data = getattr(coordinator, "data", None)
    if isinstance(data, dict):
        device = data.get(device_id) or data.get(str(device_id))
        if isinstance(device, dict):
            return device
    return None


def _entity_device_id(entity: Entity, unique_id: str) -> int | None:
    """Return Yeelight source device id from entity metadata when possible."""
    raw_device_id = getattr(
        entity,
        "_device_id",
        getattr(entity, "_source_device_id", None),
    )
    if isinstance(raw_device_id, int):
        return raw_device_id
    if isinstance(raw_device_id, str) and raw_device_id.isdigit():
        return int(raw_device_id)

    prefix = f"{DOMAIN}_"
    if not unique_id.startswith(prefix):
        return None
    remainder = unique_id[len(prefix):]
    first_part = remainder.split("_", 1)[0]
    return int(first_part) if first_part.isdigit() else None
