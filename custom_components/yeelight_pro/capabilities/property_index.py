"""Derived property membership indexes for Yeelight IoT registry."""

from __future__ import annotations

from dataclasses import replace

from .models import IoTComponentSpec, IoTPropertySpec


def enrich_property_component_memberships(
    properties: tuple[IoTPropertySpec, ...],
    components: tuple[IoTComponentSpec, ...],
) -> tuple[IoTPropertySpec, ...]:
    """Return properties with components derived from official component specs."""
    memberships = _property_memberships(components)
    enriched: list[IoTPropertySpec] = []
    for prop in properties:
        component_aliases = memberships.get(prop.prop)
        if component_aliases:
            enriched.append(replace(prop, components=component_aliases))
        else:
            enriched.append(prop)
    return tuple(enriched)


def _property_memberships(
    components: tuple[IoTComponentSpec, ...],
) -> dict[str, tuple[str, ...]]:
    """Build prop -> component aliases from component property declarations."""
    buckets: dict[str, list[str]] = {}
    for component in components:
        for prop in component.properties:
            aliases = buckets.setdefault(prop, [])
            if component.alias not in aliases:
                aliases.append(component.alias)
    return {prop: tuple(aliases) for prop, aliases in buckets.items()}


__all__ = ["enrich_property_component_memberships"]
