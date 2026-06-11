"""Static HA platform contract data for Yeelight IoT payloads."""

from __future__ import annotations

from typing import Literal

PlatformSupportStatusValue = Literal["supported", "experimental", "unsupported"]

READ_ONLY_BOOL_BINARY_PROPS = frozenset({
    "aco",
    "alm",
    "bc",
    "bcg",
    "dc",
    "mv",
    "rs",
    "run_speed_rdy",
    "slisaon_rdy",
    "trs",
})
READ_ONLY_SENSOR_PROPS = frozenset({
    "acd",
    "ap",
    "ae",
    "bl",
    "blp",
    "ch_num",
    "cpt",
    "acct",
    "cra",
    "curp",
    "ebl",
    "ep",
    "esv",
    "esvf",
    "fm",
    "fv",
    "h",
    "iec",
    "lc",
    "lf",
    "li",
    "level",
    "lsc",
    "lsot",
    "lsv",
    "luminance",
    "o",
    "ocp",
    "ot",
    "pf",
    "pl",
    "rd",
    "rt",
    "rfhct",
    "st",
    "sys_s",
    "t",
    "temp",
})
WRITABLE_NUMERIC_FORMATS = frozenset(
    {"int", "integer", "uint8", "uint16", "uint32", "float", "double", "number"}
)
PRIMARY_CATEGORY_CANDIDATES: dict[str, tuple[str, ...]] = {
    "light": ("light",),
    "contact_sensor": ("binary_sensor",),
    "human_sensor": ("binary_sensor", "sensor"),
    "light_sensor": ("sensor",),
    "curtain": ("cover",),
    "temp_control": ("climate",),
    "relay_switch": ("switch",),
    "scene_panel": ("event",),
    "knob_switch": ("event",),
    "other": (),
    "gateway": (),
}
PLATFORM_ORDER = (
    "light",
    "binary_sensor",
    "sensor",
    "event",
    "cover",
    "climate",
    "switch",
    "fan",
    "button",
    "select",
    "number",
    "text",
)
LIGHT_CONTROL_PROPS = frozenset({"p", "l", "ct", "c"})
RELAY_SWITCH_CONTROL_PROPS = frozenset({
    "l",
    "li",
    "mock",
    "p",
    "run_speed",
    "sbp",
    "slisaon",
    "sp",
})
COVER_TARGET_PROPS = frozenset({"tp"})
CLIMATE_CANDIDATE_PROPS = frozenset({
    "acp",
    "acm",
    "actt",
    "acct",
    "acf",
    "acdfltr",
    "bhm",
    "do",
    "fa",
    "he",
    "rfhp",
    "rfhct",
    "rfhtt",
    "sa",
    "tgt",
    "ve",
})
FAN_CANDIDATE_PROPS = frozenset({"vmcp", "vmcf"})

PRIMARY_PLATFORM_CONTRACT_ROWS: tuple[
    tuple[str, PlatformSupportStatusValue, str],
    ...,
] = (
    ("light", "supported", "light p/l/ct/c properties"),
    ("switch", "supported", "relay_switch p/sp properties"),
    ("sensor", "supported", "readable telemetry properties"),
    ("binary_sensor", "supported", "mv/dc/alm state properties"),
    ("event", "supported", "documented device events and WebSocket event frames"),
    ("button", "supported", "scene execution action shortcut"),
    ("select", "supported", "house-level room/group/scene selector helpers"),
    ("number", "supported", "group l/ct property controls"),
    ("cover", "supported", "curtain cp/tp properties"),
    ("climate", "supported", "temp_control ac*/rfh*/tgt properties"),
    ("fan", "supported", "fresh-air and fan-speed properties"),
    (
        "lock",
        "unsupported",
        "no documented Yeelight door-lock device or action contract",
    ),
    (
        "vacuum",
        "unsupported",
        "no documented Yeelight cleaning device or action contract",
    ),
    ("scene", "unsupported", "cloud scene execution uses button/select action entities"),
    ("text", "unsupported", "no documented writable text semantics"),
    ("notify", "unsupported", "no documented notification target/service"),
    ("media_player", "unsupported", "no documented playback/media properties"),
    ("humidifier", "unsupported", "no dedicated humidifier property model"),
    ("water_heater", "unsupported", "covered by temp_control climate when documented"),
    ("valve", "unsupported", "no documented valve property model"),
    ("alarm_control_panel", "unsupported", "no alarm panel arm/disarm contract"),
    ("device_tracker", "unsupported", "no presence/location device tracker semantics"),
    ("update", "unsupported", "no firmware update runtime contract"),
    (
        "remote",
        "unsupported",
        "rmt/acrc are management/config properties without a documented HA remote command set",
    ),
    ("siren", "unsupported", "blink is a transient LAN action, not a persistent siren entity"),
    ("camera", "unsupported", "no documented camera stream/snapshot contract"),
)
DEFAULT_UNSUPPORTED_EVIDENCE = "no documented Yeelight property, event, or action contract"

__all__ = [
    "CLIMATE_CANDIDATE_PROPS",
    "COVER_TARGET_PROPS",
    "DEFAULT_UNSUPPORTED_EVIDENCE",
    "FAN_CANDIDATE_PROPS",
    "LIGHT_CONTROL_PROPS",
    "PLATFORM_ORDER",
    "PRIMARY_CATEGORY_CANDIDATES",
    "PRIMARY_PLATFORM_CONTRACT_ROWS",
    "READ_ONLY_BOOL_BINARY_PROPS",
    "READ_ONLY_SENSOR_PROPS",
    "RELAY_SWITCH_CONTROL_PROPS",
    "WRITABLE_NUMERIC_FORMATS",
]
