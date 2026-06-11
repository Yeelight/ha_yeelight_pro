"""Home Assistant platform mapping contract for Yeelight IoT payloads."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

from ..utils import to_category, to_str
from .ha_core_platforms import HA_CORE_PLATFORMS
from .platform_contract_data import (
    CLIMATE_CANDIDATE_PROPS,
    COVER_TARGET_PROPS,
    DEFAULT_UNSUPPORTED_EVIDENCE,
    LIGHT_CONTROL_PROPS,
    PLATFORM_ORDER,
    PRIMARY_CATEGORY_CANDIDATES,
    PRIMARY_PLATFORM_CONTRACT_ROWS,
    READ_ONLY_BOOL_BINARY_PROPS,
    READ_ONLY_SENSOR_PROPS,
    RELAY_SWITCH_CONTROL_PROPS,
    WRITABLE_NUMERIC_FORMATS,
)
from .registry import parse_component_property_key, property_spec

PlatformSupportStatus = Literal["supported", "experimental", "unsupported"]
PlatformSummaryStatus = Literal["supported", "diagnostic", "unsupported"]


@dataclass(frozen=True, slots=True)
class PlatformContract:
    """One Home Assistant platform mapping decision."""

    platform: str
    status: PlatformSupportStatus
    evidence: str


@dataclass(frozen=True, slots=True)
class PropertyEvidence:
    """Documented property metadata from registry or OpenAPI rows."""

    prop: str
    readable: bool
    writable: bool
    value_format: str
    has_value_range: bool
    has_value_list: bool


_PRIMARY_PLATFORM_CONTRACTS: tuple[PlatformContract, ...] = tuple(
    PlatformContract(platform, status, evidence)
    for platform, status, evidence in PRIMARY_PLATFORM_CONTRACT_ROWS
)
PLATFORM_CONTRACTS: tuple[PlatformContract, ...] = (
    _PRIMARY_PLATFORM_CONTRACTS
    + tuple(
        PlatformContract(platform, "unsupported", DEFAULT_UNSUPPORTED_EVIDENCE)
        for platform in sorted(
            HA_CORE_PLATFORMS - {item.platform for item in _PRIMARY_PLATFORM_CONTRACTS}
        )
    )
)


def platform_contracts() -> tuple[PlatformContract, ...]:
    """Return the fixed HA platform mapping support matrix."""
    return PLATFORM_CONTRACTS


def platform_candidates_for_payload(payload: Mapping[str, Any]) -> tuple[str, ...]:
    """Return HA platform candidates implied by category, properties, and events."""
    candidates: list[str] = []
    category = _payload_category(payload)
    props = _property_evidence(payload)
    has_events = _has_events(payload)

    if _should_use_category_fallback(category, props, has_events):
        _extend(candidates, PRIMARY_CATEGORY_CANDIDATES.get(category, ()))

    for prop, evidence in props.items():
        if prop in READ_ONLY_BOOL_BINARY_PROPS and _read_only(evidence):
            _extend(candidates, ("binary_sensor",))
        elif prop in READ_ONLY_SENSOR_PROPS and _read_only(evidence):
            _extend(candidates, ("sensor",))
        elif prop in COVER_TARGET_PROPS and evidence.writable:
            _extend(candidates, ("cover",))
        elif prop in CLIMATE_CANDIDATE_PROPS:
            _extend(candidates, ("climate",))
        elif prop in RELAY_SWITCH_CONTROL_PROPS and category == "relay_switch":
            _extend(candidates, ("switch",))
        elif prop in LIGHT_CONTROL_PROPS and category == "light":
            _extend(candidates, ("light",))
        elif evidence.writable and evidence.has_value_list:
            _extend(candidates, ("select",))
        elif evidence.writable and _numeric_property(evidence):
            _extend(candidates, ("number",))

    if has_events:
        _extend(candidates, ("event",))

    return tuple(platform for platform in PLATFORM_ORDER if platform in candidates)


def primary_platform_for_payload(payload: Mapping[str, Any]) -> str | None:
    """Return the first supported primary candidate for a runtime payload."""
    candidates = platform_candidates_for_payload(payload)
    return candidates[0] if candidates else None


def platform_mapping_summary() -> tuple[dict[str, str], ...]:
    """Return a JSON-safe support matrix for diagnostics or tests."""
    return tuple(
        {
            "platform": item.platform,
            "status": _support_status(item.status),
            "reason": item.evidence,
        }
        for item in PLATFORM_CONTRACTS
    )


def _support_status(status: str) -> PlatformSummaryStatus:
    if status == "experimental":
        return "diagnostic"
    if status == "unsupported":
        return "unsupported"
    return "supported"


def _should_use_category_fallback(
    category: str,
    props: Mapping[str, PropertyEvidence],
    has_events: bool,
) -> bool:
    """Return true when category identity is the best available platform evidence."""
    if category == "light":
        return not props and not has_events
    if category in {"relay_switch", "switch"}:
        return not props and not has_events
    return True


def _payload_category(payload: Mapping[str, Any]) -> str:
    return to_category(
        payload.get("iot_category")
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
        for component in _components(product_model):
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
        return parse_component_property_key(text).prop_name
    except ValueError:
        return text


def _property_id(prop: Mapping[str, Any]) -> Any:
    return prop.get("prop_id", prop.get("propId", prop.get("propName")))


def _properties(value: Any) -> list[Mapping[str, Any]]:
    return [item for item in value or [] if isinstance(item, Mapping)]


def _read_only(evidence: PropertyEvidence) -> bool:
    return evidence.readable and not evidence.writable


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


def _has_light_property_evidence(props: Mapping[str, PropertyEvidence]) -> bool:
    return any(
        prop in LIGHT_CONTROL_PROPS and evidence.writable
        for prop, evidence in props.items()
    )


def _numeric_property(evidence: PropertyEvidence) -> bool:
    return evidence.has_value_range or evidence.value_format in WRITABLE_NUMERIC_FORMATS


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
    return any(_component_has_events(component) for component in _components(product_model))


def _components(product_model: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    return _properties(product_model.get("components"))


def _component_has_events(component: Mapping[str, Any]) -> bool:
    return bool(_properties(component.get("events")))


def _extend(candidates: list[str], values: Iterable[str]) -> None:
    for value in values:
        if value and value not in candidates:
            candidates.append(value)


__all__ = [
    "HA_CORE_PLATFORMS",
    "PLATFORM_CONTRACTS",
    "PlatformContract",
    "PlatformSummaryStatus",
    "PlatformSupportStatus",
    "platform_candidates_for_payload",
    "platform_contracts",
    "platform_mapping_summary",
    "primary_platform_for_payload",
]
