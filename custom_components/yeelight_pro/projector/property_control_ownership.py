"""Main-entity ownership helpers for writable property controls."""

from __future__ import annotations

from ..canonical.models import ComponentInstanceModel
from .climate_helpers import CLIMATE_MAIN_ENTITY_PROPS
from .platform_evidence import component_has_climate_evidence, component_platform

MAIN_ENTITY_PROPS = frozenset({
    "p",
    "sp",
    "l",
    "ct",
    "c",
    "cp",
    "tp",
    "cra",
    "tra",
    "rs",
    "acp",
    "actt",
    "acct",
    "rfhp",
    "rfhct",
    "rfhtt",
    "tgt",
    "vmcp",
    "vmcf",
    "m",
    "lock",
    "locked",
    "lck",
})
MAIN_ENTITY_PROPS_BY_PLATFORM = {
    "climate": CLIMATE_MAIN_ENTITY_PROPS,
    "cover": frozenset({"cp", "cra", "rs", "tp", "tra"}),
    "fan": frozenset({"vmcp", "vmcf"}),
    "light": frozenset({"c", "ct", "l", "m", "p"}),
    "switch": frozenset({"p", "sp"}),
}


def is_main_entity_property(
    prop_id: str,
    component: ComponentInstanceModel | None,
) -> bool:
    """Return whether a property is already owned by a component main entity."""
    if component is None:
        return prop_id in MAIN_ENTITY_PROPS

    platform = component_platform(component)
    if platform in MAIN_ENTITY_PROPS_BY_PLATFORM:
        return prop_id in MAIN_ENTITY_PROPS_BY_PLATFORM[platform]
    category = (component.category or "").lower().replace("-", "_").replace(" ", "_")
    component_id = component.component_id.lower()
    if platform is None and (
        component_id.startswith("fresh_air")
        or (category == "temp_control" and prop_id in MAIN_ENTITY_PROPS_BY_PLATFORM["fan"])
    ):
        return prop_id in MAIN_ENTITY_PROPS_BY_PLATFORM["fan"]
    if platform is None and (
        component_has_climate_evidence(component)
        or category in {"air_conditioner", "temp_control"}
        or component_id.startswith(("air_conditioner", "climate"))
    ):
        return prop_id in MAIN_ENTITY_PROPS_BY_PLATFORM["climate"]
    if platform is None and _looks_like_relay_switch_component(component):
        return prop_id in MAIN_ENTITY_PROPS_BY_PLATFORM["switch"]
    return prop_id in MAIN_ENTITY_PROPS


def _looks_like_relay_switch_component(component: ComponentInstanceModel) -> bool:
    """Return true for canonical relay-switch channels with power control."""
    category = (component.category or "").lower()
    return category in {"relay_switch", "switch"}


__all__ = [
    "MAIN_ENTITY_PROPS",
    "MAIN_ENTITY_PROPS_BY_PLATFORM",
    "is_main_entity_property",
]
