"""Helpers for reconciling projected Yeelight Pro entities with HA's registry."""

from __future__ import annotations

import logging
from typing import Any, Mapping

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN
from .core.coordinator import YeelightProCoordinator
from .projector.binary_sensor import project_binary_sensors
from .projector.climate import project_climate
from .projector.cover import project_cover
from .projector.event import project_events
from .projector.fan import project_fans
from .projector.light import project_light
from .projector.lock import project_lock
from .projector.sensor import project_sensors
from .projector.switch import project_switches

_LOGGER = logging.getLogger(__name__)


def _iter_projected_unique_ids(device_payload: Mapping[str, Any]) -> set[str]:
    """Return all projected entity unique IDs for a single runtime device payload."""
    unique_ids: set[str] = set()

    light = project_light(device_payload, domain=DOMAIN)
    if light is not None:
        unique_ids.add(light.unique_id)

    for projection in project_fans(device_payload, domain=DOMAIN):
        unique_ids.add(projection.unique_id)

    cover = project_cover(device_payload, domain=DOMAIN)
    if cover is not None:
        unique_ids.add(cover.unique_id)

    climate = project_climate(device_payload, domain=DOMAIN)
    if climate is not None:
        unique_ids.add(climate.unique_id)

    lock = project_lock(device_payload, domain=DOMAIN)
    if lock is not None:
        unique_ids.add(lock.unique_id)

    for projection in project_switches(device_payload, domain=DOMAIN):
        unique_ids.add(projection.unique_id)

    for projection in project_sensors(device_payload, domain=DOMAIN):
        unique_ids.add(projection.unique_id)

    for projection in project_binary_sensors(device_payload, domain=DOMAIN):
        unique_ids.add(projection.unique_id)

    for projection in project_events(device_payload, domain=DOMAIN):
        unique_ids.add(projection.unique_id)

    return unique_ids


def collect_active_entity_unique_ids(
    coordinator: YeelightProCoordinator,
) -> set[str]:
    """Collect the active projected entity unique IDs for the current topology."""
    unique_ids: set[str] = set()
    for device_payload in coordinator.data.values():
        unique_ids.update(_iter_projected_unique_ids(device_payload))
    return unique_ids


async def async_reconcile_entity_registry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: YeelightProCoordinator,
) -> set[str]:
    """Remove stale entity-registry entries that no longer exist in current topology."""
    active_unique_ids = collect_active_entity_unique_ids(coordinator)
    entity_registry = er.async_get(hass)
    stale_entries = [
        registry_entry
        for registry_entry in er.async_entries_for_config_entry(entity_registry, entry.entry_id)
        if registry_entry.platform == DOMAIN
        and registry_entry.unique_id.startswith(f"{DOMAIN}_")
        and registry_entry.unique_id not in active_unique_ids
    ]

    for registry_entry in stale_entries:
        _LOGGER.info(
            "Removing stale Yeelight Pro entity %s (unique_id=%s)",
            registry_entry.entity_id,
            registry_entry.unique_id,
        )
        entity_registry.async_remove(registry_entry.entity_id)

    _LOGGER.info(
        "Reconciled Yeelight Pro entity registry for entry %s: active=%s removed=%s",
        entry.entry_id,
        len(active_unique_ids),
        len(stale_entries),
    )
    return active_unique_ids
