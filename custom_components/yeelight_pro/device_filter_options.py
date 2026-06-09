"""Options-flow helpers for Yeelight Pro device import filtering."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.helpers import selector

from .const import (
    CONF_DEVICE_IMPORT_FILTER,
    CONF_DEVICE_IMPORT_FILTER_ENABLED,
    CONF_DEVICE_IMPORT_FILTER_EXCLUDE_CATEGORIES,
    CONF_DEVICE_IMPORT_FILTER_EXCLUDE_DEVICES,
    CONF_DEVICE_IMPORT_FILTER_EXCLUDE_GATEWAYS,
    CONF_DEVICE_IMPORT_FILTER_EXCLUDE_PRODUCT_IDS,
    CONF_DEVICE_IMPORT_FILTER_EXCLUDE_ROOMS,
    CONF_DEVICE_IMPORT_FILTER_EXCLUDE_TYPES,
    CONF_DEVICE_IMPORT_FILTER_INCLUDE_CATEGORIES,
    CONF_DEVICE_IMPORT_FILTER_INCLUDE_DEVICES,
    CONF_DEVICE_IMPORT_FILTER_INCLUDE_GATEWAYS,
    CONF_DEVICE_IMPORT_FILTER_INCLUDE_PRODUCT_IDS,
    CONF_DEVICE_IMPORT_FILTER_INCLUDE_ROOMS,
    CONF_DEVICE_IMPORT_FILTER_INCLUDE_TYPES,
    CONF_DEVICE_IMPORT_FILTER_MODE,
)
from .device_filter import (
    canonical_device_import_filter,
    normalize_device_import_filter,
)

FILTER_MODE_ANY = "or"
FILTER_MODE_ALL = "and"

_FILTER_DIMENSION_FIELDS = (
    (
        "categories",
        CONF_DEVICE_IMPORT_FILTER_INCLUDE_CATEGORIES,
        CONF_DEVICE_IMPORT_FILTER_EXCLUDE_CATEGORIES,
    ),
    ("types", CONF_DEVICE_IMPORT_FILTER_INCLUDE_TYPES, CONF_DEVICE_IMPORT_FILTER_EXCLUDE_TYPES),
    ("rooms", CONF_DEVICE_IMPORT_FILTER_INCLUDE_ROOMS, CONF_DEVICE_IMPORT_FILTER_EXCLUDE_ROOMS),
    (
        "gateways",
        CONF_DEVICE_IMPORT_FILTER_INCLUDE_GATEWAYS,
        CONF_DEVICE_IMPORT_FILTER_EXCLUDE_GATEWAYS,
    ),
    (
        "product_ids",
        CONF_DEVICE_IMPORT_FILTER_INCLUDE_PRODUCT_IDS,
        CONF_DEVICE_IMPORT_FILTER_EXCLUDE_PRODUCT_IDS,
    ),
    (
        "devices",
        CONF_DEVICE_IMPORT_FILTER_INCLUDE_DEVICES,
        CONF_DEVICE_IMPORT_FILTER_EXCLUDE_DEVICES,
    ),
)
_FILTER_FORM_KEYS = tuple(
    key
    for _, include_key, exclude_key in _FILTER_DIMENSION_FIELDS
    for key in (include_key, exclude_key)
)


def device_filter_schema_fields(options: Mapping[str, Any]) -> dict[Any, Any]:
    """Return advanced manual device filter fields for the options form."""
    filter_config = _filter_config(options)
    normalized = normalize_device_import_filter(filter_config)
    return {
        vol.Required(
            CONF_DEVICE_IMPORT_FILTER_ENABLED,
            default=normalized.enabled,
        ): bool,
        vol.Required(
            CONF_DEVICE_IMPORT_FILTER_MODE,
            default=normalized.mode,
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[FILTER_MODE_ANY, FILTER_MODE_ALL],
                mode=selector.SelectSelectorMode.DROPDOWN,
                translation_key="device_import_filter_mode",
            )
        ),
        **{
            vol.Optional(
                include_key,
                default=_rules_text(filter_config, "include", dimension),
            ): str
            for dimension, include_key, _ in _FILTER_DIMENSION_FIELDS
        },
        **{
            vol.Optional(
                exclude_key,
                default=_rules_text(filter_config, "exclude", dimension),
            ): str
            for dimension, _, exclude_key in _FILTER_DIMENSION_FIELDS
        },
    }


def merge_device_import_filter(
    current_options: Mapping[str, Any],
    user_input: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the stored device-import filter config from options form input."""
    current = _filter_config(current_options)
    include: dict[str, list[str]] = {}
    exclude: dict[str, list[str]] = {}
    for dimension, include_key, exclude_key in _FILTER_DIMENSION_FIELDS:
        include_items = _items(user_input.get(
            include_key,
            _rules_text(current, "include", dimension),
        ))
        exclude_items = _items(user_input.get(
            exclude_key,
            _rules_text(current, "exclude", dimension),
        ))
        if include_items:
            include[dimension] = include_items
        if exclude_items:
            exclude[dimension] = exclude_items

    has_rules = bool(include or exclude)
    return canonical_device_import_filter({
        "enabled": (
            user_input.get(
                CONF_DEVICE_IMPORT_FILTER_ENABLED,
                normalize_device_import_filter(current).enabled,
            )
            if has_rules
            else False
        ),
        "mode": user_input.get(
            CONF_DEVICE_IMPORT_FILTER_MODE,
            normalize_device_import_filter(current).mode,
        ),
        "include": include,
        "exclude": exclude,
    })


def stored_device_import_filter_options(
    options: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Return canonical import filter from nested or legacy form-only options."""
    nested = _filter_config(options)
    has_form_keys = any(key in options for key in device_filter_form_keys())
    if not nested and not has_form_keys:
        return None
    if not has_form_keys:
        return canonical_device_import_filter(nested)
    return merge_device_import_filter(
        {CONF_DEVICE_IMPORT_FILTER: canonical_device_import_filter(nested)},
        options,
    )


def device_import_filter_changed(
    current_options: Mapping[str, Any],
    pending_options: Mapping[str, Any],
) -> bool:
    """Return whether the effective stored device filter changed."""
    current = normalize_device_import_filter(_filter_config(current_options))
    pending = normalize_device_import_filter(_filter_config(pending_options))
    return current != pending


def device_filter_form_keys() -> tuple[str, ...]:
    """Return all visible form-only keys used by the device filter UI."""
    return (
        CONF_DEVICE_IMPORT_FILTER_ENABLED,
        CONF_DEVICE_IMPORT_FILTER_MODE,
        *_FILTER_FORM_KEYS,
    )


def _filter_config(options: Mapping[str, Any]) -> Mapping[str, Any]:
    value = options.get(CONF_DEVICE_IMPORT_FILTER)
    return value if isinstance(value, Mapping) else {}


def _rules_text(
    filter_config: Mapping[str, Any],
    section: str,
    dimension: str,
) -> str:
    group = filter_config.get(section)
    if not isinstance(group, Mapping):
        return ""
    return ", ".join(sorted(_items(group.get(dimension))))


def _items(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw_items = value.split(",")
    elif isinstance(value, (list, tuple, set)):
        raw_items = list(value)
    else:
        raw_items = [value]
    items = [str(item).strip() for item in raw_items if str(item).strip()]
    return sorted(dict.fromkeys(items))
