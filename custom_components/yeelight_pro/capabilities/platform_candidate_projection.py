"""Project Yeelight runtime payload capability evidence into HA platform candidates."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from ..utils import to_category, to_str
from .platform_contract_data import (
    AUXILIARY_BOOL_SWITCH_PROPS,
    CLIMATE_CANDIDATE_PROPS,
    COVER_TARGET_PROPS,
    FAN_CANDIDATE_PROPS,
    LIGHT_CONTROL_PROPS,
    PLATFORM_ORDER,
    PRIMARY_CATEGORY_CANDIDATES,
    READ_ONLY_BOOL_BINARY_PROPS,
    READ_ONLY_SENSOR_PROPS,
    RELAY_SWITCH_CONTROL_PROPS,
)
from .platform_contract_evidence import (
    capability_category,
    components,
    has_indexed_switch_control,
    has_light_capability_evidence,
    has_switch_capability_evidence,
    ignored_property_reason,
)
from .platform_contract_logging import (
    PlatformIgnoredTrace,
    PlatformCandidateTrace,
    ignored_trace,
    log_platform_candidates,
    platform_trace,
)
from .registry import (
    normalize_property_key,
    parse_component_property_key,
    property_spec,
)
from .sensor_safety import safe_registry_sensor_property


@dataclass(frozen=True, slots=True)
class PropertyEvidence:
    """Documented property metadata from registry or OpenAPI rows."""

    prop: str
    registry_backed: bool
    readable: bool
    writable: bool
    value_format: str
    has_value_range: bool
    has_value_list: bool


def platform_candidates_for_payload(payload: Mapping[str, Any]) -> tuple[str, ...]:
    """Return HA platform candidates implied by category, properties, and events."""
    candidates: list[str] = []
    traces: list[PlatformCandidateTrace] = []
    ignored: list[PlatformIgnoredTrace] = []
    category = _payload_category(payload)
    props = _property_evidence(payload)
    has_events = _has_events(payload)
    prop_names = set(props)
    has_indexed_switch = has_indexed_switch_control(payload, category)

    for prop, evidence in props.items():
        if prop in READ_ONLY_BOOL_BINARY_PROPS and _read_only(evidence):
            _add_candidate(
                candidates,
                traces,
                "binary_sensor",
                prop=prop,
                reason="read_only_bool_property",
            )
        elif _sensor_property_candidate(prop, evidence):
            _add_candidate(
                candidates,
                traces,
                "sensor",
                prop=prop,
                reason="read_only_sensor_property",
            )
        elif prop in COVER_TARGET_PROPS and evidence.writable:
            _add_candidate(
                candidates,
                traces,
                "cover",
                prop=prop,
                reason="writable_cover_property",
            )
        elif prop in CLIMATE_CANDIDATE_PROPS:
            _add_candidate(
                candidates,
                traces,
                "climate",
                prop=prop,
                reason="climate_property",
            )
        elif prop in FAN_CANDIDATE_PROPS:
            _add_candidate(
                candidates,
                traces,
                "fan",
                prop=prop,
                reason="fan_property",
            )
        elif (
            prop in RELAY_SWITCH_CONTROL_PROPS
            and has_switch_capability_evidence(category, prop_names, has_indexed_switch)
        ):
            _add_candidate(
                candidates,
                traces,
                "switch",
                prop=prop,
                reason="switch_capability_evidence",
            )
        elif prop in LIGHT_CONTROL_PROPS and has_light_capability_evidence(prop_names):
            _add_candidate(
                candidates,
                traces,
                "light",
                prop=prop,
                reason="light_capability_evidence",
            )
        elif _documented_writable_property(evidence) and prop in AUXILIARY_BOOL_SWITCH_PROPS:
            _add_candidate(
                candidates,
                traces,
                "switch",
                prop=prop,
                reason="documented_writable_bool_property",
            )
        elif _documented_writable_property(evidence) and evidence.has_value_list:
            _add_candidate(
                candidates,
                traces,
                "select",
                prop=prop,
                reason="documented_writable_enum_property",
            )
        elif _documented_writable_property(evidence) and _numeric_property(evidence):
            _add_candidate(
                candidates,
                traces,
                "number",
                prop=prop,
                reason="documented_writable_numeric_property",
            )
        else:
            ignored.append(
                ignored_trace(
                    prop,
                    reason=ignored_property_reason(
                        prop,
                        registry_backed=evidence.registry_backed,
                        readable=evidence.readable,
                        writable=evidence.writable,
                        category=category,
                        prop_names=prop_names,
                        has_indexed_switch=has_indexed_switch,
                    ),
                )
            )

    if has_events:
        _add_candidate(
            candidates,
            traces,
            "event",
            prop=None,
            reason="documented_event",
        )

    candidate_category = capability_category(payload, prop_names)
    ordered = _ordered_candidates(candidate_category, candidates)
    log_platform_candidates(
        payload,
        category=category,
        props=prop_names,
        has_events=has_events,
        has_indexed_switch=has_indexed_switch,
        capability_category=candidate_category,
        candidates=ordered,
        traces=tuple(traces),
        ignored=tuple(ignored),
    )
    return ordered


def _ordered_candidates(
    capability_category: str | None,
    candidates: list[str],
) -> tuple[str, ...]:
    """Return candidates in capability-priority order."""
    ordered: list[str] = []
    for platform in PRIMARY_CATEGORY_CANDIDATES.get(capability_category or "", ()):
        if platform in candidates:
            _extend(ordered, (platform,))
    for platform in PLATFORM_ORDER:
        if platform in candidates:
            _extend(ordered, (platform,))
    return tuple(ordered)


def _payload_category(payload: Mapping[str, Any]) -> str:
    return to_category(
        payload.get("effective_category")
        or payload.get("iot_category")
        or payload.get("category")
        or payload.get("type")
    )


def _property_evidence(payload: Mapping[str, Any]) -> dict[str, PropertyEvidence]:
    props: dict[str, PropertyEvidence] = {}
    params = payload.get("params")
    if isinstance(params, Mapping):
        for key in params:
            _merge_property_evidence(props, _prop_name(key), None)
    for prop in _properties(payload.get("properties")):
        _merge_property_evidence(props, _prop_name(_property_id(prop)), prop)
    for subdevice in _properties(payload.get("subDeviceList")):
        for prop in _properties(subdevice.get("properties")):
            _merge_property_evidence(props, _prop_name(_property_id(prop)), prop)
    product_model = payload.get("ha_product_model")
    if isinstance(product_model, Mapping):
        for component in components(product_model):
            for prop in _properties(component.get("properties")):
                _merge_property_evidence(props, _prop_name(_property_id(prop)), prop)
    props.pop("", None)
    return props


def _merge_property_evidence(
    props: dict[str, PropertyEvidence],
    prop: str,
    raw: Mapping[str, Any] | None,
) -> None:
    if not prop:
        return
    evidence = _property_evidence_for(prop, raw)
    current = props.get(prop)
    if current is None:
        props[prop] = evidence
        return
    props[prop] = PropertyEvidence(
        prop=prop,
        registry_backed=current.registry_backed or evidence.registry_backed,
        readable=current.readable or evidence.readable,
        writable=current.writable or evidence.writable,
        value_format=current.value_format or evidence.value_format,
        has_value_range=current.has_value_range or evidence.has_value_range,
        has_value_list=current.has_value_list or evidence.has_value_list,
    )


def _property_evidence_for(
    prop: str,
    raw: Mapping[str, Any] | None,
) -> PropertyEvidence:
    prop_spec = property_spec(prop)
    registry_backed = prop_spec is not None
    readable = bool(prop_spec is None or prop_spec.readable)
    writable = bool(prop_spec is not None and prop_spec.writable)
    value_format = to_category(getattr(prop_spec, "data_type", None))
    has_value_range = bool(getattr(prop_spec, "value_range", None))
    has_value_list = bool(getattr(prop_spec, "value_list", None))

    if raw is not None:
        raw_readable, raw_writable = _raw_access(raw)
        readable = readable or raw_readable
        writable = writable or raw_writable
        value_format = to_category(raw.get("format", raw.get("fomat"))) or value_format
        has_value_range = has_value_range or isinstance(raw.get("valueRange"), Mapping)
        has_value_list = has_value_list or bool(_properties(raw.get("valueList")))

    return PropertyEvidence(
        prop=prop,
        registry_backed=registry_backed,
        readable=readable,
        writable=writable,
        value_format=value_format,
        has_value_range=has_value_range,
        has_value_list=has_value_list,
    )


def _prop_name(value: Any) -> str:
    text = to_str(value)
    if not text:
        return ""
    try:
        return normalize_property_key(parse_component_property_key(text).prop_name) or ""
    except ValueError:
        return normalize_property_key(text) or ""


def _property_id(prop: Mapping[str, Any]) -> Any:
    return prop.get("prop_id", prop.get("propId", prop.get("propName")))


def _properties(value: Any) -> list[Mapping[str, Any]]:
    return [item for item in value or [] if isinstance(item, Mapping)]


def _read_only(evidence: PropertyEvidence) -> bool:
    return evidence.readable and not evidence.writable


def _sensor_property_candidate(prop: str, evidence: PropertyEvidence) -> bool:
    """Return true for documented read-only sensor platform evidence."""
    if not _read_only(evidence):
        return False
    if prop in READ_ONLY_SENSOR_PROPS:
        return True
    return safe_registry_sensor_property(prop, property_spec(prop))


def _raw_access(raw: Mapping[str, Any]) -> tuple[bool, bool]:
    operators = {
        to_category(item)
        for item in raw.get("operators") or []
        if to_category(item)
    }
    if operators & {"set", "toggle", "adjust"}:
        return True, True
    numeric_access = _int_value(raw.get("access"))
    if numeric_access is not None:
        return bool(numeric_access & 1), bool(numeric_access & 2)
    access = to_category(raw.get("access"))
    if not access:
        return True, False
    readable = "read" in access or "读" in access
    writable = "write" in access or "写" in access
    return readable, writable


def _numeric_property(evidence: PropertyEvidence) -> bool:
    return evidence.has_value_range


def _documented_writable_property(evidence: PropertyEvidence) -> bool:
    return evidence.registry_backed and evidence.writable


def _int_value(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _has_events(payload: Mapping[str, Any]) -> bool:
    if _properties(payload.get("events")):
        return True
    product_model = payload.get("ha_product_model")
    if not isinstance(product_model, Mapping):
        return False
    return any(_component_has_events(component) for component in components(product_model))


def _component_has_events(component: Mapping[str, Any]) -> bool:
    return bool(_properties(component.get("events")))


def _extend(candidates: list[str], values: Iterable[str]) -> None:
    for value in values:
        if value and value not in candidates:
            candidates.append(value)


def _add_candidate(
    candidates: list[str],
    traces: list[PlatformCandidateTrace],
    platform: str,
    *,
    prop: str | None,
    reason: str,
) -> None:
    traces.append(platform_trace(platform, prop=prop, reason=reason))
    _extend(candidates, (platform,))


__all__ = ["platform_candidates_for_payload"]
