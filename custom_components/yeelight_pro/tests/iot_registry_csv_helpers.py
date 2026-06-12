"""Shared CSV helpers for Yeelight IoT registry contract tests."""

from __future__ import annotations

import csv
from pathlib import Path

IOT_DOCS = Path(__file__).resolve().parents[3] / "docs" / "iot"


def csv_rows(name: str) -> list[dict[str, str]]:
    """Read one Yeelight IoT source CSV as dictionaries."""
    with (IOT_DOCS / name).open(newline="", encoding="utf-8-sig") as csv_file:
        return list(csv.DictReader(csv_file))


def component_key(value: str) -> str:
    """Normalize component lookup keys like the registry does."""
    return value.lower().replace("_", " ").replace("-", " ").strip()


def property_access_by_prop() -> dict[str, str]:
    """Return documented property access flags by canonical prop id."""
    access: dict[str, str] = {}
    for name in ("基础组件_属性.csv", "基础信息_属性.csv"):
        for row in csv_rows(name):
            prop = (row.get("缩写") or row.get("属性名称") or "").strip()
            if prop:
                access[prop] = row.get("权限", "")
    return access


def component_properties_from_iot_docs() -> dict[str, tuple[str, ...]]:
    """Return component properties normalized from Yeelight CSV sources."""
    rows = csv_rows("基础信息_组件列表.csv")
    component_names = _component_names_by_id(rows)
    property_names = _property_name_aliases()
    properties: dict[str, list[str]] = {
        row["id"].strip(): [
            _property_alias(item, property_names)
            for item in _split_csv_list(row.get("属性", ""))
        ]
        for row in rows
        if row["id"].strip()
    }
    component_ids_by_name = {
        name: component_id
        for component_id, names in component_names.items()
        for name in names
    }

    for name in ("基础信息_属性.csv", "基础组件_属性.csv"):
        for row in csv_rows(name):
            prop = _property_alias(row.get("缩写") or row.get("属性名称"), property_names)
            for component_name in _split_csv_list(row.get("组件", "") or row.get("父记录", "")):
                component_id = component_ids_by_name.get(
                    normalized_component_name(component_name)
                )
                if component_id is not None:
                    _append_unique(properties.setdefault(component_id, []), prop)

    return {
        component_id: tuple(prop for prop in props if prop)
        for component_id, props in properties.items()
    }


def csv_readable(value: str) -> bool:
    """Return whether CSV permission text declares read access."""
    lowered = value.lower()
    return "read" in lowered or "读" in value


def csv_writable(value: str) -> bool:
    """Return whether CSV permission text declares write access."""
    lowered = value.lower()
    return "write" in lowered or "写" in value


def normalized_component_name(value: str | None) -> str:
    """Normalize component/property display names for CSV joins."""
    if value is None:
        return ""
    return " ".join(value.strip().lower().replace("_", " ").replace("-", " ").split())


def _component_names_by_id(rows: list[dict[str, str]]) -> dict[str, set[str]]:
    names: dict[str, set[str]] = {}
    for row in rows:
        component_id = row["id"].strip()
        if not component_id:
            continue
        values = {row.get("组件名称", ""), row.get("变量别名", "")}
        names[component_id] = {
            normalized
            for value in values
            if (normalized := normalized_component_name(value))
        }
    return names


def _property_name_aliases() -> dict[str, str]:
    aliases = {
        "connectivity protocols type": "cpt",
        "localtoken": "ltk",
        "run power": "run_power",
        "support relay": "support_rl",
    }
    for name in ("基础信息_属性.csv", "基础组件_属性.csv"):
        for row in csv_rows(name):
            prop_name = row.get("属性名称", "").strip()
            prop_alias = (row.get("缩写") or prop_name).strip()
            if prop_name and prop_alias:
                aliases[normalized_component_name(prop_name)] = prop_alias
                aliases[normalized_component_name(prop_alias)] = prop_alias
    return aliases


def _property_alias(value: str | None, aliases: dict[str, str]) -> str:
    if not value:
        return ""
    text = value.strip()
    return aliases.get(normalized_component_name(text), text)


def _split_csv_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _append_unique(values: list[str], value: str) -> None:
    if value and value not in values:
        values.append(value)


__all__ = [
    "IOT_DOCS",
    "component_key",
    "component_properties_from_iot_docs",
    "csv_readable",
    "csv_rows",
    "csv_writable",
    "property_access_by_prop",
]
