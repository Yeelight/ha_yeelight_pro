"""Superseded stale entity detection for Yeelight Pro registry reconciliation."""

from __future__ import annotations

from homeassistant.helpers import entity_registry as er

from .const import DOMAIN
from .entity_candidate_types import EntityCandidate, EntityKey

_HELPER_DOMAINS = frozenset({"number", "select", "switch"})
_MAIN_ENTITY_PROPS_BY_PLATFORM = {
    "climate": frozenset({"acf", "acm", "acp", "acdfltr", "actt", "acct", "aco", "o"}),
    "cover": frozenset({"cp", "cra", "rs", "tp", "tra"}),
    "fan": frozenset({"vmcp", "vmcf"}),
    "light": frozenset({"c", "ct", "l", "m", "p"}),
    "switch": frozenset({"p", "sp"}),
}


def is_stale_helper_owned_by_active_main_entity(
    registry_entry: er.RegistryEntry,
    active_entity_candidates: dict[EntityKey, EntityCandidate],
) -> bool:
    """Return true for obsolete helper rows now represented by a main entity."""
    unique_id = getattr(registry_entry, "unique_id", None)
    if not isinstance(unique_id, str) or not unique_id.startswith(f"{DOMAIN}_"):
        return False
    helper_domain = unique_id.rsplit("_", 1)[-1]
    if helper_domain not in _HELPER_DOMAINS:
        return False

    for candidate in active_entity_candidates.values():
        for prop_id in _main_entity_owned_properties(candidate.platform):
            if not unique_id.endswith(f"_{prop_id}_{helper_domain}"):
                continue
            if unique_id in {
                f"{prefix}_{prop_id}_{helper_domain}"
                for prefix in _candidate_helper_prefixes(candidate)
            }:
                return True
    return False


def _candidate_helper_prefixes(candidate: EntityCandidate) -> set[str]:
    """Return possible old helper unique-id prefixes superseded by a candidate."""
    suffix = f"_{candidate.platform}"
    if not candidate.unique_id.endswith(suffix):
        return set()
    base = candidate.unique_id[: -len(suffix)]
    prefixes = {base}
    if candidate.component_id and not base.endswith(f"_{candidate.component_id}"):
        prefixes.add(f"{base}_{candidate.component_id}")
    return prefixes


def _main_entity_owned_properties(platform: str) -> frozenset[str]:
    """Return formerly-helper properties now owned by each main platform."""
    return _MAIN_ENTITY_PROPS_BY_PLATFORM.get(platform, frozenset())


__all__ = ["is_stale_helper_owned_by_active_main_entity"]
