"""Projection reverse-lookup helpers for private-house coverage audits."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from custom_components.yeelight_pro.capabilities.registry import (
    property_spec,
)
from custom_components.yeelight_pro.projector.binary_sensor import (
    BINARY_SENSOR_SPECS,
)
from custom_components.yeelight_pro.projector.event_input import (
    is_event_input_component_context,
)
from custom_components.yeelight_pro.projector.property_control_ownership import (
    MAIN_ENTITY_PROPS_BY_PLATFORM,
    is_main_entity_property,
)
from custom_components.yeelight_pro.projector.sensor_metadata import (
    REGISTRY_SENSOR_PROPS,
    SENSOR_LABELS,
)
from scripts.private_house_audit.projection_runtime import (
    device_category,
    device_name,
    instance_components_by_id,
    model_property_ids,
    online,
    runtime_property_keys,
    safe_param_keys,
    schema_gap_reason,
    stable_digest,
)

_PROJECTED_DIAGNOSTIC_PROPS = frozenset({
    "o",
    *BINARY_SENSOR_SPECS,
    *REGISTRY_SENSOR_PROPS,
})
_EVENT_INPUT_OWNED_PROPS = frozenset({"p", "m"})
_AUDIT_METADATA_ONLY_PROPS = frozenset({
    "3rdPartySyncBitmask",
    "c_n_c",
    "cfg",
    "component_num_config",
    "dev_alarm",
    "fblck",
    "fbnum",
    "icon",
    "io",
    "io_type",
    "life",
    "name",
    "run_power",
    "support_fblck",
})
_AUDIT_RUNTIME_BACKED_CONFIG_PROPS = frozenset({
    "cpt",
    "fv",
    "lc",
    "li",
})


def _init_component_prop_map() -> dict[str, frozenset[str]]:
    """Build component_id -> possible property ids for audit reverse lookup."""
    grouped: dict[str, set[str]] = defaultdict(set)
    for prop_id, (component_id, _label) in SENSOR_LABELS.items():
        grouped[str(component_id)].add(str(prop_id))
    for prop_id, spec in BINARY_SENSOR_SPECS.items():
        component_id = str(spec["component_id"])
        grouped[component_id].add(str(prop_id))
        grouped[f"_{component_id}"].add(str(prop_id))
    grouped["internal_temperature"].add("temp")
    grouped["online_status"].add("o")
    grouped["tilt_route_calibrated"].add("trs")
    return {key: frozenset(values) for key, values in grouped.items()}


_EXPLICIT_COMPONENT_PROP_MAP = _init_component_prop_map()


def projected_component_ids(candidates: Sequence[Any]) -> list[str]:
    """Return stable projected component ids from entity candidates."""
    return sorted(
        {
            str(candidate.component_id)
            for candidate in candidates
            if getattr(candidate, "component_id", None)
        }
    )


def projected_property_keys(
    payload: Mapping[str, Any],
    candidates: Sequence[Any],
) -> set[tuple[str, str]]:
    """Infer component/property pairs represented by projected entity ids."""
    keys: set[tuple[str, str]] = set()
    instance_components = instance_components_by_id(payload)
    declared_property_ids = model_property_ids(payload)
    for candidate in candidates:
        component_id = getattr(candidate, "component_id", None)
        if not isinstance(component_id, str) or not component_id:
            continue
        _add_main_entity_projected_keys(
            keys,
            candidate.platform,
            component_id,
            instance_components,
        )
        _add_helper_projected_keys(keys, component_id, declared_property_ids)
    return keys


def unprojected_property_samples(
    properties: Sequence[Mapping[str, Any]],
    projected_keys: set[tuple[str, str]],
    *,
    runtime_keys: set[tuple[str, str]] | frozenset[tuple[str, str]] = frozenset(),
    limit: int = 12,
) -> list[dict[str, Any]]:
    """Return schema properties that do not appear directly represented."""
    samples: list[dict[str, Any]] = []
    for prop in properties:
        component_id = str(prop.get("component_id") or "")
        component_category = str(prop.get("component_category") or "")
        prop_id = str(prop.get("prop_id") or "")
        if not _is_trusted_audit_property(prop):
            continue
        if _is_event_input_owned_property(component_category, component_id, prop_id):
            continue
        if _is_metadata_only_property(prop, runtime_keys):
            continue
        if (component_id, prop_id) in projected_keys or ("", prop_id) in projected_keys:
            continue
        samples.append(dict(prop))
        if len(samples) >= limit:
            break
    return samples


def _is_trusted_audit_property(prop: Mapping[str, Any]) -> bool:
    """Return true for properties backed by docs/iot or an actual product schema."""
    if bool(prop.get("documented")) or bool(prop.get("schema_property")):
        return True
    return property_spec(prop.get("prop_id")) is not None


def _is_metadata_only_property(
    prop: Mapping[str, Any],
    runtime_keys: set[tuple[str, str]] | frozenset[tuple[str, str]],
) -> bool:
    """Return true for documented metadata that should not imply a HA entity."""
    prop_id = str(prop.get("prop_id") or "")
    if prop_id in _AUDIT_METADATA_ONLY_PROPS:
        return True
    if prop_id not in _AUDIT_RUNTIME_BACKED_CONFIG_PROPS:
        return _is_unprojectable_config_property(prop)
    component_id = str(prop.get("component_id") or "")
    return not _has_runtime_key(component_id, prop_id, runtime_keys)


def _is_unprojectable_config_property(prop: Mapping[str, Any]) -> bool:
    """Return true for config properties without a stable HA control shape."""
    if bool(prop.get("schema_property")):
        return False
    if str(prop.get("type") or "").lower() != "config":
        return False
    if str(prop.get("component_category") or "") == "gateway":
        return True
    prop_id = str(prop.get("prop_id") or "")
    spec = property_spec(prop_id)
    if spec is None:
        return True
    if spec.capability is not None or spec.value_range is not None or spec.value_list:
        return False
    return spec.data_type.strip().lower() not in {"bool", "boolean"}


def _has_runtime_key(
    component_id: str,
    prop_id: str,
    runtime_keys: set[tuple[str, str]] | frozenset[tuple[str, str]],
) -> bool:
    return (component_id, prop_id) in runtime_keys or ("", prop_id) in runtime_keys


def unprojected_event_samples(
    events: Sequence[Mapping[str, Any]],
    projected_component_ids_value: Sequence[str],
    *,
    limit: int = 12,
) -> list[dict[str, Any]]:
    """Return event-capable components with no obvious event entity."""
    projected = set(projected_component_ids_value)
    samples: list[dict[str, Any]] = []
    for event in events:
        component_id = str(event.get("component_id") or "")
        if component_id in projected or any(item.startswith(component_id) for item in projected):
            continue
        samples.append(dict(event))
        if len(samples) >= limit:
            break
    return samples


def _add_main_entity_projected_keys(
    keys: set[tuple[str, str]],
    platform: str,
    component_id: str,
    instance_components: Mapping[str, Mapping[str, Any]],
) -> None:
    """Mark schema properties already represented by HA main entities."""
    if platform not in {"binary_sensor", "climate", "cover", "fan", "light", "switch"}:
        return
    component_payload = instance_components.get(component_id)
    component = (
        _component_instance_from_payload(component_payload)
        if component_payload is not None
        else None
    )
    for prop_id in MAIN_ENTITY_PROPS_BY_PLATFORM.get(platform, ()):
        if component is None or is_main_entity_property(prop_id, component):
            keys.add((component_id, prop_id))
            keys.add(("", prop_id))


def _add_helper_projected_keys(
    keys: set[tuple[str, str]],
    component_id: str,
    model_property_ids: frozenset[str],
) -> None:
    """Mark schema properties represented by generated helper controls/sensors."""
    parts = component_id.split("_")
    if len(parts) >= 3 and parts[-1] in {"number", "select", "switch"}:
        component, prop = _split_helper_control_component(
            component_id,
            parts,
            model_property_ids,
        )
        keys.add((component, prop))
        keys.add(("", prop))
    for prop_id in _EXPLICIT_COMPONENT_PROP_MAP.get(component_id, ()):
        keys.add(("", prop_id))
    for suffix, prop_ids in _EXPLICIT_COMPONENT_PROP_MAP.items():
        if not suffix.startswith("_") or not component_id.endswith(suffix):
            continue
        for prop_id in prop_ids:
            keys.add(("", prop_id))
    for prop_id in _PROJECTED_DIAGNOSTIC_PROPS:
        if component_id == prop_id or component_id.endswith(f"_{prop_id}"):
            keys.add(("", prop_id))


def _split_helper_control_component(
    component_id: str,
    parts: Sequence[str],
    model_property_ids: frozenset[str],
) -> tuple[str, str]:
    """Return component and property from helper entity component_id."""
    for index in range(len(parts) - 2, 0, -1):
        prop = "_".join(parts[index:-1])
        if (
            prop in model_property_ids
            or prop in _PROJECTED_DIAGNOSTIC_PROPS
            or property_spec(prop) is not None
        ):
            return "_".join(parts[:index]), prop
    return "_".join(parts[:-2]), parts[-2]


def _component_instance_from_payload(
    payload: Mapping[str, Any],
) -> Any:
    """Build a ComponentInstanceModel only when needed by ownership helpers."""
    from custom_components.yeelight_pro.canonical.models import (  # noqa: PLC0415
        ComponentInstanceModel,
    )

    return ComponentInstanceModel.from_dict(dict(payload))


def _is_event_input_owned_property(
    component_category: str,
    component_id: str,
    prop_id: str,
) -> bool:
    """Return true for event-input state props represented by event entities."""
    return prop_id in _EVENT_INPUT_OWNED_PROPS and is_event_input_component_context(
        component_category,
        component_id,
    )


# Backward-compatible private names used by existing audit tests.
_projected_property_keys = projected_property_keys
_unprojected_property_samples = unprojected_property_samples


__all__ = [
    "_projected_property_keys",
    "_unprojected_property_samples",
    "device_category",
    "device_name",
    "online",
    "projected_component_ids",
    "projected_property_keys",
    "runtime_property_keys",
    "safe_param_keys",
    "schema_gap_reason",
    "stable_digest",
    "unprojected_event_samples",
    "unprojected_property_samples",
]
