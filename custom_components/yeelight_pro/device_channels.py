"""User-facing channel naming helpers for Yeelight Pro entities."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import re
from typing import Any

from .utils import to_str

_CHANNEL_LABELS = {
    1: "第 1 键",
    2: "第 2 键",
    3: "第 3 键",
    4: "第 4 键",
    5: "第 5 键",
    6: "第 6 键",
    7: "第 7 键",
    8: "第 8 键",
    9: "第 9 键",
    10: "第 10 键",
    11: "第 11 键",
    12: "第 12 键",
}
_POSITIONAL_CHANNEL_LABELS = {
    2: {
        1: "左键",
        2: "右键",
    },
    3: {
        1: "左键",
        2: "中键",
        3: "右键",
    },
}
_CHANNEL_NUMERAL_LABELS = {
    1: ("一键", "1键"),
    2: ("二键", "2键"),
    3: ("三键", "3键"),
    4: ("四键", "4键"),
    5: ("五键", "5键"),
    6: ("六键", "6键"),
    7: ("七键", "7键"),
    8: ("八键", "8键"),
    9: ("九键", "9键"),
    10: ("十键", "10键"),
    11: ("十一键", "11键"),
    12: ("十二键", "12键"),
}
_CHANNEL_NAME_KEYS = ("desc", "componentName", "component_name", "name")
_MODEL_NAME_KEYS = (
    "productName",
    "product_name",
    "modelName",
    "model_name",
    "model",
)
_INDEXED_SWITCH_KEY_RE = re.compile(r"^(?P<index>\d+)-(?:p|sp)$")
_COMPONENT_INDEX_SUFFIX_RE = re.compile(r"_(?P<index>\d+)$")
_CHANNEL_COUNT_TOKENS = (
    ("单键", 1),
    ("一键", 1),
    ("双键", 2),
    ("二键", 2),
    ("三键", 3),
    ("四键", 4),
    ("五键", 5),
    ("六键", 6),
    ("七键", 7),
    ("八键", 8),
    ("九键", 9),
    ("十键", 10),
    ("十一键", 11),
    ("十二键", 12),
    ("12情景", 12),
    ("十二情景", 12),
    ("1键", 1),
    ("2键", 2),
    ("3键", 3),
    ("4键", 4),
    ("5键", 5),
    ("6键", 6),
    ("7键", 7),
    ("8键", 8),
    ("9键", 9),
    ("10键", 10),
    ("11键", 11),
    ("12键", 12),
    ("1-gang", 1),
    ("2-gang", 2),
    ("3-gang", 3),
    ("4-gang", 4),
    ("5-gang", 5),
    ("6-gang", 6),
    ("7-gang", 7),
    ("8-gang", 8),
    ("9-gang", 9),
    ("10-gang", 10),
    ("11-gang", 11),
    ("12-gang", 12),
)


def channel_name_label(
    *,
    index: int | None,
    component: Any | None = None,
    device_payload: Mapping[str, Any] | None = None,
) -> str | None:
    """Return a readable sub-entity label for indexed controls."""
    inferred_index = index if index is not None else _component_index(component)
    explicit = _component_text(component, _CHANNEL_NAME_KEYS)
    has_positional_context = False
    if device_payload is not None:
        count = switch_channel_count_hint(device_payload)
        has_positional_context = count is not None
    else:
        count = None
    if explicit and not _looks_like_generated_channel_name(
        explicit,
        inferred_index,
        positional_context=has_positional_context,
    ):
        return explicit
    if inferred_index is None:
        return None
    if count is not None:
        label = _POSITIONAL_CHANNEL_LABELS.get(count, {}).get(inferred_index)
        if label is not None:
            return label
    return _CHANNEL_LABELS.get(inferred_index, f"第 {inferred_index} 键")


def switch_channel_count_hint(payload: Mapping[str, Any]) -> int | None:
    """Return product-name channel count hints such as 双键/三键."""
    text = " ".join(
        value
        for value in (
            _first_text(payload, ("name", "deviceName", "device_name", "n")),
            _first_text(payload, _MODEL_NAME_KEYS),
            _schema_text(payload),
        )
        if value
    ).lower()
    if not text:
        return None
    for token, count in _CHANNEL_COUNT_TOKENS:
        if token.lower() in text:
            return count
    if not (
        _looks_like_positionable_switch(text)
        or _runtime_indexes_have_positional_context(payload)
    ):
        return None
    return _runtime_switch_channel_count(payload)


def _runtime_switch_channel_count(payload: Mapping[str, Any]) -> int | None:
    """Infer switch channel count from Open API runtime metadata."""
    indexes: set[int] = set()
    params = payload.get("params")
    if isinstance(params, Mapping):
        indexes.update(_indexed_switch_key_indexes(params))
    indexes.update(_subdevice_indexes(payload.get("subDeviceList")))
    instance = payload.get("ha_device_instance")
    if isinstance(instance, Mapping):
        indexes.update(_component_indexes(instance.get("components")))
    if not indexes:
        return None
    ordered = sorted(indexes)
    if ordered != list(range(1, len(ordered) + 1)):
        return None
    return len(ordered) if len(ordered) <= 12 else None


def _looks_like_positionable_switch(text: str) -> bool:
    """Return true when indexed channels likely map to physical positions."""
    lowered = text.lower()
    if not lowered:
        return False
    if any(token in lowered for token in ("墙壁", "面板", "智能开关", "wall switch", "gang")):
        return True
    return "开关" in lowered and "继电器" not in lowered


def _runtime_indexes_have_positional_context(payload: Mapping[str, Any]) -> bool:
    """Return true when runtime metadata describes a physical key/panel device."""
    for subdevice in _iter_mappings(payload.get("subDeviceList")):
        category = " ".join(
            value
            for value in (
                _first_text(subdevice, ("category",)),
                _first_text(subdevice, _CHANNEL_NAME_KEYS),
            )
            if value
        ).lower()
        if any(
            token in category
            for token in (
                "button",
                "key",
                "panel",
                "scene_panel",
                "scene control",
                "switch",
                "按键",
                "按钮",
                "情景",
                "面板",
                "开关",
            )
        ):
            return True
    return False


def _indexed_switch_key_indexes(params: Mapping[Any, Any]) -> set[int]:
    """Return indexes from raw keys such as 1-p / 2-sp."""
    indexes: set[int] = set()
    for key in params:
        match = _INDEXED_SWITCH_KEY_RE.match(str(key))
        if match:
            indexes.add(int(match.group("index")))
    return indexes


def _subdevice_indexes(value: Any) -> set[int]:
    """Return Open API sub-device indexes when present."""
    indexes: set[int] = set()
    for item in _iter_mappings(value):
        index = item.get("index")
        if isinstance(index, int) and index > 0:
            indexes.add(index)
        elif isinstance(index, str) and index.isdecimal() and int(index) > 0:
            indexes.add(int(index))
    return indexes


def _component_indexes(value: Any) -> set[int]:
    """Return canonical component indexes for channel components."""
    indexes: set[int] = set()
    for item in _iter_mappings(value):
        component_id = to_str(item.get("component_id"))
        if component_id is None:
            continue
        text = component_id.strip().lower()
        if text.isdecimal():
            indexes.add(int(text))
            continue
        suffix_match = _COMPONENT_INDEX_SUFFIX_RE.search(text)
        if suffix_match:
            indexes.add(int(suffix_match.group("index")))
    return indexes


def _iter_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    """Yield mapping items from list-like runtime metadata."""
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


def _component_text(component: Any | None, keys: tuple[str, ...]) -> str | None:
    if component is None:
        return None
    for key in keys:
        value = (
            component.get(key)
            if isinstance(component, Mapping)
            else getattr(component, key, None)
        )
        if text := to_str(value):
            return text
    for key in ("component_id", "componentId", "id"):
        value = (
            component.get(key)
            if isinstance(component, Mapping)
            else getattr(component, key, None)
        )
        if text := to_str(value):
            return text
    return None


def _component_index(component: Any | None) -> int | None:
    """Return a numeric channel index from component metadata when available."""
    if component is None:
        return None
    for key in ("index", "component_index", "componentIndex"):
        value = (
            component.get(key)
            if isinstance(component, Mapping)
            else getattr(component, key, None)
        )
        if isinstance(value, int) and value > 0:
            return value
        if isinstance(value, str) and value.isdecimal() and int(value) > 0:
            return int(value)
    for key in ("component_id", "componentId", "id"):
        value = (
            component.get(key)
            if isinstance(component, Mapping)
            else getattr(component, key, None)
        )
        text = to_str(value)
        if text is None:
            continue
        indexes = _component_indexes([{"component_id": text}])
        if indexes:
            return min(indexes)
    return None


def _schema_text(payload: Mapping[str, Any]) -> str | None:
    schema = payload.get("product_schema")
    if not isinstance(schema, Mapping):
        return None
    return _first_text(
        schema,
        ("name", "productName", "product_name", "modelName", "model_name", "model"),
    )


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        if value := to_str(payload.get(key)):
            return value
    return None


def _looks_like_generated_channel_name(
    value: str,
    index: int | None,
    *,
    positional_context: bool = False,
) -> bool:
    """Return true for generated names that should be replaced."""
    text = value.strip().lower().replace("-", "_").replace(" ", "_")
    generated = {
        "button",
        "key",
        "relay_switch",
        "scene_button",
        "scene_control_button",
        "switch",
        "switch_control",
        "wireless_switch_channel",
        "开关",
        "按键",
        "情景按键",
    }
    if positional_context:
        generated.update({
            "wireless_switch_channel",
            "无线开关通道",
        })
    if index is not None:
        generated.update({
            str(index),
            f"air_conditioner_{index}",
            f"按键{index}",
            f"按键_{index}",
            f"第{index}键",
            f"第_{index}_键",
            f"键{index}",
            f"键_{index}",
            f"button_{index}",
            f"curtain_{index}",
            f"fan_{index}",
            f"human_sensor_{index}",
            f"key_{index}",
            f"switch_{index}",
            f"relay_switch_{index}",
            f"sensor_{index}",
            f"scene_button_{index}",
            f"scene_control_button_{index}",
            f"switch_control_{index}",
            f"wireless_switch_channel_{index}",
        })
        generated.update(
            label.strip().lower().replace("-", "_").replace(" ", "_")
            for label in _CHANNEL_NUMERAL_LABELS.get(index, ())
        )
    return text in generated


__all__ = ["channel_name_label", "switch_channel_count_hint"]
