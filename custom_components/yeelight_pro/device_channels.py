"""User-facing channel naming helpers for Yeelight Pro entities."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import re
from typing import Any

from .device_channel_catalog import (
    is_channel_component_name,
    is_input_channel_component_name,
    payload_product_spec,
    product_catalog_channel_count,
    product_channel_count,
)
from .device_channel_generated_names import (
    generated_channel_name_index,
    looks_like_generated_channel_name,
)
from .device_channel_semantics import (
    component_text,
    is_channel_component,
    uses_output_channel_label,
)
from .utils import to_str

_CHANNEL_LABELS = {
    1: "按键 1",
    2: "按键 2",
    3: "按键 3",
    4: "按键 4",
    5: "按键 5",
    6: "按键 6",
    7: "按键 7",
    8: "按键 8",
    9: "按键 9",
    10: "按键 10",
    11: "按键 11",
    12: "按键 12",
}
_OUTPUT_CHANNEL_LABELS = {
    1: "回路 1",
    2: "回路 2",
    3: "回路 3",
    4: "回路 4",
    5: "回路 5",
    6: "回路 6",
    7: "回路 7",
    8: "回路 8",
    9: "回路 9",
    10: "回路 10",
    11: "回路 11",
    12: "回路 12",
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
_CHANNEL_NAME_KEYS = ("desc", "componentName", "component_name", "name")
_COMPONENT_INDEX_SUFFIX_RE = re.compile(r"_(?P<index>\d+)$")


def channel_name_label(
    *,
    index: int | None,
    component: Any | None = None,
    device_payload: Mapping[str, Any] | None = None,
) -> str | None:
    """Return a readable sub-entity label for indexed controls."""
    inferred_index = index if index is not None else _component_index(component)
    explicit = component_text(component, _CHANNEL_NAME_KEYS)
    has_positional_context = False
    if device_payload is not None:
        count = switch_channel_count_hint(device_payload)
        has_positional_context = count is not None
    else:
        count = None
    if inferred_index is None and count == 1 and _is_documented_channel_component(component):
        inferred_index = 1
    if inferred_index is None and explicit:
        inferred_index = generated_channel_name_index(explicit)
    if (
        component is not None
        and not is_channel_component(component)
        and not _non_channel_component_uses_channel_label(
            explicit,
            inferred_index,
            positional_context=has_positional_context,
        )
    ):
        return None
    if explicit and not looks_like_generated_channel_name(
        explicit,
        inferred_index,
        positional_context=has_positional_context,
    ):
        return explicit
    if inferred_index is None:
        return None
    uses_output_label = _uses_output_channel_label(component, device_payload)
    if count is not None:
        label = _POSITIONAL_CHANNEL_LABELS.get(count, {}).get(inferred_index)
        if label is not None:
            return label
    labels = _OUTPUT_CHANNEL_LABELS if uses_output_label else _CHANNEL_LABELS
    prefix = "回路" if labels is _OUTPUT_CHANNEL_LABELS else "按键"
    return labels.get(inferred_index, f"{prefix} {inferred_index}")


def _non_channel_component_uses_channel_label(
    explicit: str | None,
    index: int | None,
    *,
    positional_context: bool,
) -> bool:
    """Allow generated key names without treating every indexed component as a key."""
    if explicit is None:
        return False
    if _is_positional_channel_label(explicit):
        return True
    if generated_channel_name_index(explicit) is not None:
        return True
    if explicit.strip().isdecimal():
        return True
    return looks_like_generated_channel_name(
        explicit,
        index,
        positional_context=positional_context,
    )


def _is_positional_channel_label(value: str) -> bool:
    return value.strip() in {"左键", "中键", "右键"}


def switch_channel_count_hint(payload: Mapping[str, Any]) -> int | None:
    """Return switch channel count from official product or runtime capability evidence."""
    if count := product_catalog_channel_count(payload):
        return count
    if count := _runtime_switch_channel_count(payload):
        return count
    return None


def _uses_output_channel_label(
    component: Any | None,
    payload: Mapping[str, Any] | None,
) -> bool:
    """Resolve input-vs-output naming with product catalog evidence first."""
    if payload is not None and _product_catalog_prefers_input_channels(payload):
        return False
    return uses_output_channel_label(component, payload)


def _product_catalog_prefers_input_channels(payload: Mapping[str, Any]) -> bool:
    """Return true when official composition identifies channels as input keys."""
    spec = payload_product_spec(payload)
    if spec is None:
        return False
    count = product_channel_count(spec)
    if count is not None and count < 4:
        return False
    components = tuple(spec.normal_components)
    counted_components = tuple(name for name, _count in spec.normal_component_counts)
    if counted_components:
        components = (*components, *counted_components)
    channel_components = [
        component
        for component in components
        if is_channel_component_name(component)
    ]
    return bool(channel_components) and all(
        is_input_channel_component_name(component)
        for component in channel_components
    )


def _is_documented_channel_component(component: Any | None) -> bool:
    """Return true for official input/output channel components."""
    if component is None:
        return False
    values = (
        component_text(component, ("component_id", "componentId", "id")),
        component_text(component, ("name", "componentName", "component_name", "desc")),
        component_text(component, ("category",)),
    )
    return any(is_channel_component_name(value) for value in values if value)


def _runtime_switch_channel_count(payload: Mapping[str, Any]) -> int | None:
    """Infer switch channel count from Open API runtime metadata."""
    indexes: set[int] = set()
    indexes.update(_subdevice_indexes(payload.get("subDeviceList")))
    if not _runtime_only_product_model(payload):
        instance = payload.get("ha_device_instance")
        if isinstance(instance, Mapping):
            indexes.update(_component_indexes(instance.get("components")))
    if not indexes:
        return None
    ordered = sorted(indexes)
    if ordered != list(range(1, len(ordered) + 1)):
        return None
    return len(ordered) if len(ordered) <= 12 else None


def _subdevice_indexes(value: Any) -> set[int]:
    """Return Open API sub-device indexes when present."""
    indexes: set[int] = set()
    for item in _iter_mappings(value):
        if not _is_documented_channel_component(item):
            continue
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
        if not _is_documented_channel_component(item) and not is_channel_component(item):
            continue
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


def _runtime_only_product_model(payload: Mapping[str, Any]) -> bool:
    """Return true when canonical components were inferred only from raw runtime params."""
    product_model = payload.get("ha_product_model")
    return (
        isinstance(product_model, Mapping)
        and to_str(product_model.get("schema_version")) == "runtime-v1"
        and not isinstance(payload.get("subDeviceList"), list)
    )


def _iter_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    """Yield mapping items from list-like runtime metadata."""
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


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
        if is_channel_component(component):
            if text.isdecimal() and int(text) > 0:
                return int(text)
            match = _COMPONENT_INDEX_SUFFIX_RE.search(text.strip().lower())
            if match:
                return int(match.group("index"))
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


__all__ = ["channel_name_label", "switch_channel_count_hint"]
