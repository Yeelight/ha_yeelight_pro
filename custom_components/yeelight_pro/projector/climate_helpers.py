"""Climate value helpers for Yeelight Pro projections."""

from __future__ import annotations

from typing import Any, Mapping

from homeassistant.components.climate import HVACMode

from ..canonical.models import ComponentModel
from ..utils import to_int, to_str
from .common import state_value as projector_state_value

AC_MODE_TO_HVAC: dict[int, HVACMode] = {
    1: HVACMode.COOL,
    4: HVACMode.FAN_ONLY,
    8: HVACMode.HEAT,
}
HVAC_TO_AC_MODE: dict[HVACMode, int] = {
    mode: raw for raw, mode in AC_MODE_TO_HVAC.items()
}
AC_FAN_LABELS: dict[int, str] = {
    1: "高",
    2: "中",
    4: "低",
}
CLIMATE_PROPERTY_PROPS = frozenset({
    "acp",
    "acm",
    "actt",
    "acct",
    "acf",
    "p",
    "t",
    "tgt",
    "rfhp",
    "rfhct",
    "rfhtt",
})


def state_key(control_or_state_key: str | None) -> str | None:
    """Return state key from a plain or component-scoped control key."""
    if control_or_state_key is None:
        return None
    return control_or_state_key.split("-", 1)[1] if "-" in control_or_state_key else control_or_state_key


def climate_hvac_mode(
    state: Mapping[str, Any],
    *,
    power_key: str | None,
    mode_key: str | None,
) -> HVACMode:
    """Project Yeelight AC power/mode values to Home Assistant HVAC mode."""
    power = _bool(state_value(state, power_key), default=False) if power_key else False
    if not power:
        return HVACMode.OFF

    raw_mode = to_int(state_value(state, mode_key)) if mode_key else None
    if raw_mode in AC_MODE_TO_HVAC:
        return AC_MODE_TO_HVAC[raw_mode]
    return HVACMode.AUTO


def climate_hvac_modes(mode_key: str | None) -> list[HVACMode]:
    """Return supported HVAC modes for the projected climate entity."""
    modes = [HVACMode.OFF, HVACMode.AUTO]
    if mode_key is None:
        return modes
    return [*modes, HVACMode.COOL, HVACMode.FAN_ONLY, HVACMode.HEAT]


def climate_raw_mode_for_hvac(hvac_mode: HVACMode) -> int | None:
    """Return Yeelight raw acm value for a HA HVAC mode."""
    return HVAC_TO_AC_MODE.get(hvac_mode)


def climate_fan_mode(state: Mapping[str, Any], fan_key: str | None) -> str | None:
    """Project Yeelight AC fan speed to a Home Assistant fan mode label."""
    raw = to_int(state_value(state, fan_key)) if fan_key else None
    if raw is None:
        return None
    return climate_fan_label(raw)


def state_value(state: Mapping[str, Any], control_or_state_key: str | None) -> Any:
    """Return state value for either an indexed control key or its raw prop id."""
    return projector_state_value(state, control_or_state_key)


def climate_skip_reason(props: set[str], *, has_evidence: bool) -> str:
    """Return the stable skip reason for an invalid climate candidate."""
    if not CLIMATE_PROPERTY_PROPS & props:
        return "missing_climate_properties"
    if not has_evidence:
        return "missing_climate_capability_evidence"
    return "unknown"


def climate_fan_modes(
    schema_component: ComponentModel | None,
    *,
    fan_key: str | None,
) -> list[str]:
    """Return available fan mode labels from schema/range or documented defaults."""
    if fan_key is None:
        return []

    values = _schema_fan_values(schema_component)
    if not values:
        values = sorted(AC_FAN_LABELS)
    return [climate_fan_label(value) for value in values]


def climate_fan_mode_values(
    schema_component: ComponentModel | None,
) -> dict[str, int]:
    """Return label-to-raw fan speed values."""
    values = _schema_fan_values(schema_component)
    if not values:
        values = sorted(AC_FAN_LABELS)
    return {climate_fan_label(value): value for value in values}


def climate_raw_fan_for_mode(
    fan_mode: str,
    fan_mode_values: Mapping[str, int],
) -> int | None:
    """Return Yeelight raw acf value for a Home Assistant fan mode label."""
    label = to_str(fan_mode)
    if label is None:
        return None
    normalized = _normalize_label(label)
    for candidate, value in fan_mode_values.items():
        if normalized == _normalize_label(candidate):
            return value
    return None


def climate_fan_label(raw_value: int) -> str:
    """Return a stable label for a Yeelight AC fan-speed value."""
    return AC_FAN_LABELS.get(raw_value, f"风速 {raw_value}")


def _schema_fan_values(schema_component: ComponentModel | None) -> list[int]:
    """Return acf values declared by product schema metadata."""
    if schema_component is None:
        return []
    prop = next(
        (item for item in schema_component.properties if item.prop_id == "acf"),
        None,
    )
    if prop is None:
        return []

    value_list: list[int] = []
    for item in prop.value_list:
        raw_value = to_int(item.code)
        if raw_value is not None:
            value_list.append(raw_value)
    if value_list:
        return sorted(set(value_list))

    if prop.value_range is None:
        return []
    minimum = prop.value_range.min
    maximum = prop.value_range.max
    step = prop.value_range.step or 1
    if minimum is None or maximum is None or step <= 0 or maximum < minimum:
        return []
    return list(range(minimum, maximum + 1, step))


def _bool(value: Any, *, default: bool) -> bool:
    """Safely convert Yeelight truthy values."""
    if value is None:
        return default
    return bool(value)


def _normalize_label(value: str) -> str:
    """Normalize labels for command lookup."""
    return "".join(value.split()).lower()


__all__ = [
    "AC_FAN_LABELS",
    "AC_MODE_TO_HVAC",
    "CLIMATE_PROPERTY_PROPS",
    "HVAC_TO_AC_MODE",
    "climate_fan_mode",
    "climate_fan_mode_values",
    "climate_fan_modes",
    "climate_hvac_mode",
    "climate_hvac_modes",
    "climate_raw_fan_for_mode",
    "climate_raw_mode_for_hvac",
    "climate_skip_reason",
    "state_key",
    "state_value",
]
