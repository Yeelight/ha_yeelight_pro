"""Registry-backed runtime category inference helpers."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Iterable

from ..capabilities.registry import iot_registry, is_iot_category, parse_component_property_key
from ..utils import to_str
from .device_classification_categories import CATEGORY_ALIASES

GENERIC_REGISTRY_PROPS = frozenset({
    "",
    "3rdPartySyncBitmask",
    "icon",
    "io",
    "mock",
    "name",
    "o",
    "online",
})
REGISTRY_CATEGORY_PRIORITY = (
    "contact_sensor",
    "light_sensor",
    "human_sensor",
    "curtain",
    "temp_control",
    "scene_panel",
    "knob_switch",
    "gateway",
    "other",
    "relay_switch",
    "light",
)


def registry_category_from_property_keys(
    keys: Iterable[str],
    *,
    current_category: Any = None,
) -> str | None:
    """Infer an IoT category from documented component/property membership."""
    props = {normalized_prop_name(key) for key in keys}
    props.difference_update(GENERIC_REGISTRY_PROPS)
    props.discard("")
    if not props:
        return None

    category = normalize_registry_category(current_category)
    scores, exclusive = _score_categories(props)
    if not scores:
        return None

    winner = _best_category(scores, exclusive)
    if winner is None:
        return _current_category_when_supported(category, scores)
    if category == winner:
        return winner

    current_score = scores.get(category or "", 0.0)
    winner_score = scores[winner]
    if current_score and winner_score <= current_score and not exclusive.get(winner):
        return category
    if exclusive.get(winner) or winner_score >= 1.0:
        return winner
    return _current_category_when_supported(category, scores)


def categories_for_property(prop: Any) -> frozenset[str]:
    """Return documented component categories that expose a property."""
    prop_name = normalized_prop_name(prop)
    return _property_category_index().get(prop_name, frozenset())


def normalized_prop_name(value: Any) -> str:
    """Normalize indexed component property keys such as ``1-p`` to ``p``."""
    text = to_str(value)
    if not text:
        return ""
    try:
        return parse_component_property_key(text).prop_name
    except ValueError:
        return text


def normalize_registry_category(value: Any) -> str | None:
    """Normalize category labels without using user-facing device names."""
    text = to_str(value)
    if text is None:
        return None
    normalized = text.strip().lower().replace("_", " ").replace("-", " ")
    return CATEGORY_ALIASES.get(normalized, normalized.replace(" ", "_"))


def _score_categories(props: set[str]) -> tuple[dict[str, float], dict[str, set[str]]]:
    scores: dict[str, float] = {}
    exclusive: dict[str, set[str]] = {}
    for prop in props:
        categories = categories_for_property(prop)
        if not categories:
            continue
        weight = 1.0 / len(categories)
        for category in categories:
            scores[category] = scores.get(category, 0.0) + weight
        if len(categories) == 1:
            category = next(iter(categories))
            exclusive.setdefault(category, set()).add(prop)
    return scores, exclusive


def _best_category(scores: dict[str, float], exclusive: dict[str, set[str]]) -> str | None:
    ranked = sorted(
        scores,
        key=lambda item: (
            scores[item],
            len(exclusive.get(item, ())),
            -REGISTRY_CATEGORY_PRIORITY.index(item)
            if item in REGISTRY_CATEGORY_PRIORITY
            else -len(REGISTRY_CATEGORY_PRIORITY),
        ),
        reverse=True,
    )
    if not ranked:
        return None
    first = ranked[0]
    if len(ranked) == 1:
        return first
    second = ranked[1]
    if scores[first] > scores[second]:
        return first
    return None


def _current_category_when_supported(
    category: str | None,
    scores: dict[str, float],
) -> str | None:
    if category and category in scores and is_iot_category(category):
        return category
    return None


@lru_cache(maxsize=1)
def _property_category_index() -> dict[str, frozenset[str]]:
    registry = iot_registry()
    indexed: dict[str, set[str]] = {}

    for component in registry.components:
        if not component.category or not is_iot_category(component.category):
            continue
        for prop in component.properties:
            prop_name = normalized_prop_name(prop)
            if prop_name not in GENERIC_REGISTRY_PROPS:
                indexed.setdefault(prop_name, set()).add(component.category)

    for spec in registry.properties:
        for component_name in spec.components:
            mapped_component = registry.component_map.get(_component_key(component_name))
            if mapped_component is None or not mapped_component.category:
                continue
            if is_iot_category(mapped_component.category):
                indexed.setdefault(spec.prop, set()).add(mapped_component.category)

    return {prop: frozenset(categories) for prop, categories in indexed.items()}


def _component_key(value: Any) -> str:
    text = to_str(value)
    if not text:
        return ""
    return " ".join(text.lower().replace("_", " ").replace("-", " ").split())


__all__ = [
    "categories_for_property",
    "normalize_registry_category",
    "normalized_prop_name",
    "registry_category_from_property_keys",
]
