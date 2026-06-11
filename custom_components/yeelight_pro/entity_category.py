"""Home Assistant entity category helpers for Yeelight Pro projections."""

from __future__ import annotations

from typing import Any

from homeassistant.const import EntityCategory

from .capabilities.registry import parse_component_property_key, property_spec

ENTITY_CATEGORY_CONFIG = "config"
ENTITY_CATEGORY_DIAGNOSTIC = "diagnostic"

CONFIG_PROPERTIES = frozenset({
    "acrc",
    "blp",
    "bp",
    "dd",
    "dim_curve",
    "dpt",
    "fade_rate",
    "ep",
    "hys",
    "hys_min",
    "keys_visible",
    "lc",
    "li",
    "max_level",
    "min_level",
    "nightMode",
    "ntOn",
    "open_type",
    "rd",
    "rg",
    "rrd",
    "rst",
    "rt",
    "run_speed",
    "sa",
    "slisaon",
    "ss",
    "st",
    "temp_hidden",
    "time_hidden",
    "weather_hidden",
})
DIAGNOSTIC_PROPERTIES = frozenset({
    "ae",
    "ap",
    "acd",
    "bc",
    "bcg",
    "bl",
    "ch_num",
    "cpt",
    "cra",
    "curp",
    "ebl",
    "esv",
    "esvf",
    "fm",
    "fv",
    "iec",
    "lf",
    "lsc",
    "lsot",
    "lsv",
    "o",
    "ocp",
    "ot",
    "pf",
    "pl",
    "rs",
    "run_speed_rdy",
    "slisaon_rdy",
    "sys_s",
    "trs",
})


def entity_category_for_property(prop: Any) -> str | None:
    """Return the HA entity category implied by a Yeelight property."""
    prop_name = _base_prop_name(prop)
    if prop_name in CONFIG_PROPERTIES:
        return ENTITY_CATEGORY_CONFIG
    if prop_name in DIAGNOSTIC_PROPERTIES:
        return ENTITY_CATEGORY_DIAGNOSTIC

    spec = property_spec(prop_name)
    if spec is None:
        return None
    if spec.category == "config":
        return ENTITY_CATEGORY_CONFIG if spec.writable else ENTITY_CATEGORY_DIAGNOSTIC
    if spec.handler == "gateway":
        return ENTITY_CATEGORY_DIAGNOSTIC
    return None


def ha_entity_category(value: str | None) -> EntityCategory | None:
    """Convert internal category text to Home Assistant's enum."""
    if value == ENTITY_CATEGORY_CONFIG:
        return EntityCategory.CONFIG
    if value == ENTITY_CATEGORY_DIAGNOSTIC:
        return EntityCategory.DIAGNOSTIC
    return None


def _base_prop_name(value: Any) -> str:
    """Return the property id without an optional component index."""
    try:
        return parse_component_property_key(value).prop_name
    except ValueError:
        return str(value).strip()


__all__ = [
    "ENTITY_CATEGORY_CONFIG",
    "ENTITY_CATEGORY_DIAGNOSTIC",
    "entity_category_for_property",
    "ha_entity_category",
]
