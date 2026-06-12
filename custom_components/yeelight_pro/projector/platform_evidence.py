"""Documented Yeelight IoT platform evidence helpers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..canonical.models import ComponentInstanceModel, ComponentModel
from ..capabilities.platform_contract_data import (
    CLIMATE_CANDIDATE_PROPS,
    COVER_TARGET_PROPS,
    FAN_CANDIDATE_PROPS,
    LIGHT_CONTROL_PROPS,
    RELAY_SWITCH_CONTROL_PROPS,
)
from ..capabilities.registry import component_platform_hint, platform_for_category
from ..core.device_runtime_capabilities import normalize_iot_category
from ..utils import to_category

_COVER_POSITION_PROPS = frozenset({"cp", "rs", *COVER_TARGET_PROPS})
_SWITCH_CONTROL_PROPS = frozenset({"p", "sp"})


def payload_category(device_payload: Mapping[str, Any]) -> str:
    """Return normalized effective IoT category for a runtime payload."""
    return to_category(
        device_payload.get("effective_category")
        or device_payload.get("iot_category")
        or device_payload.get("category")
    )


def payload_platform(device_payload: Mapping[str, Any]) -> str | None:
    """Return documented HA platform for a payload category."""
    category = payload_category(device_payload)
    return platform_for_category(category)


def component_platform(
    component: ComponentInstanceModel,
    product_component: ComponentModel | None = None,
) -> str | None:
    """Return documented HA platform for a component without using labels."""
    values: list[Any] = [
        component.component_id,
        component.category,
    ]
    if product_component is not None:
        values.extend(
            (
                product_component.component_id,
                product_component.category,
            )
        )

    for value in values:
        direct = component_platform_hint(value)
        if direct:
            return direct
        category = normalize_iot_category(value)
        if not category:
            continue
        platform = platform_for_category(category)
        if platform:
            return platform
    return None


def component_category(
    component: ComponentInstanceModel,
    product_component: ComponentModel | None = None,
) -> str:
    """Return documented IoT category for a component when available."""
    for value in (
        component.category,
        product_component.category if product_component is not None else None,
    ):
        category = normalize_iot_category(value)
        if category:
            return category
    return ""


def component_prop_ids(
    component: ComponentInstanceModel,
    product_component: ComponentModel | None = None,
) -> set[str]:
    """Return state and schema property ids for component capability checks."""
    prop_ids = {str(prop) for prop in component.state}
    if product_component is not None:
        prop_ids.update(prop.prop_id for prop in product_component.properties)
    return prop_ids


def component_has_light_evidence(
    component: ComponentInstanceModel,
    product_component: ComponentModel | None = None,
) -> bool:
    """Return true when official category or properties identify a light."""
    platform = component_platform(component, product_component)
    props = component_prop_ids(component, product_component)
    return platform == "light" or (
        component_category(component, product_component) == "light"
        and bool(props & LIGHT_CONTROL_PROPS)
    )


def component_has_switch_evidence(
    component: ComponentInstanceModel,
    product_component: ComponentModel | None = None,
) -> bool:
    """Return true when official category or properties identify a relay switch."""
    platform = component_platform(component, product_component)
    props = component_prop_ids(component, product_component)
    if platform == "event":
        return False
    return platform == "switch" or (
        component_category(component, product_component) == "relay_switch"
        and bool(props & _SWITCH_CONTROL_PROPS)
    )


def component_has_cover_evidence(
    component: ComponentInstanceModel,
    product_component: ComponentModel | None = None,
) -> bool:
    """Return true when official category or properties identify a curtain."""
    platform = component_platform(component, product_component)
    props = component_prop_ids(component, product_component)
    return platform == "cover" or (
        component_category(component, product_component) == "curtain"
        and bool(props & _COVER_POSITION_PROPS)
    )


def component_has_climate_evidence(
    component: ComponentInstanceModel,
    product_component: ComponentModel | None = None,
) -> bool:
    """Return true when official properties identify a climate component."""
    props = component_prop_ids(component, product_component)
    if props & FAN_CANDIDATE_PROPS and not props & CLIMATE_CANDIDATE_PROPS:
        return False
    return component_platform(component, product_component) == "climate" or bool(
        props & CLIMATE_CANDIDATE_PROPS
    )


def component_has_fan_evidence(
    component: ComponentInstanceModel,
    product_component: ComponentModel | None = None,
) -> bool:
    """Return true when official fresh-air properties identify a fan."""
    props = component_prop_ids(component, product_component)
    return bool(props & FAN_CANDIDATE_PROPS)


def payload_has_light_evidence(
    device_payload: Mapping[str, Any],
    state: Mapping[str, Any],
) -> bool:
    """Return true when payload category and state support light projection."""
    return payload_category(device_payload) == "light" and bool(
        set(state) & LIGHT_CONTROL_PROPS
    )


def payload_has_cover_evidence(
    device_payload: Mapping[str, Any],
    state: Mapping[str, Any],
) -> bool:
    """Return true when payload category and state support cover projection."""
    return payload_category(device_payload) == "curtain" and bool(
        set(state) & _COVER_POSITION_PROPS
    )


def payload_has_climate_evidence(
    device_payload: Mapping[str, Any],
    state: Mapping[str, Any],
) -> bool:
    """Return true when payload category and state support climate projection."""
    props = set(state)
    return payload_category(device_payload) == "temp_control" and bool(
        props & CLIMATE_CANDIDATE_PROPS
    )


def payload_has_switch_evidence(
    device_payload: Mapping[str, Any],
    state: Mapping[str, Any],
) -> bool:
    """Return true when payload category and state support switch projection."""
    category = payload_category(device_payload)
    if category != "relay_switch":
        return False
    return bool(set(state) & RELAY_SWITCH_CONTROL_PROPS)


__all__ = [
    "component_category",
    "component_has_climate_evidence",
    "component_has_cover_evidence",
    "component_has_fan_evidence",
    "component_has_light_evidence",
    "component_has_switch_evidence",
    "component_platform",
    "component_prop_ids",
    "payload_category",
    "payload_has_climate_evidence",
    "payload_has_cover_evidence",
    "payload_has_light_evidence",
    "payload_has_switch_evidence",
    "payload_platform",
]
