"""运行时模板选择 helper。"""

from __future__ import annotations

from typing import Any, Mapping

from ..core.device_runtime_capabilities import category_from_property_keys

FRESH_AIR_PROPS = frozenset({"vmcp", "vmcf"})


def runtime_property_ids_from_params(params: Mapping[str, Any]) -> set[str]:
    """Return property ids from direct and indexed runtime params."""
    return {str(prop).split("-", 1)[-1] for prop in params}


def runtime_template_key(
    template_key: str | None,
    params: Mapping[str, Any],
) -> str | None:
    """Return the most specific runtime template supported by property evidence."""
    props = runtime_property_ids_from_params(params)
    if props & FRESH_AIR_PROPS:
        return "fresh_air"
    category = category_from_property_keys(props, current_category=template_key)
    if category is not None and category != "other":
        return category
    return template_key


__all__ = [
    "runtime_property_ids_from_params",
    "runtime_template_key",
]
