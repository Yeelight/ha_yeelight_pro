"""Yeelight IoT property display-name contract tests."""

from __future__ import annotations

import csv
from pathlib import Path

from custom_components.yeelight_pro.capabilities import iot_registry
from custom_components.yeelight_pro.capabilities.models import IOT_PROPERTY_DESCRIPTIONS


IOT_DOCS = Path(__file__).resolve().parents[3] / "docs" / "iot"


def test_property_descriptions_match_iot_csv() -> None:
    """内置属性描述必须与易来 CSV 保持一致."""
    expected = _property_descriptions_by_prop()

    assert dict(IOT_PROPERTY_DESCRIPTIONS) == expected


def test_registry_uses_csv_descriptions_for_property_display_names() -> None:
    """registry 属性展示名必须来自易来属性表描述，而不是英文内部名."""
    registry = iot_registry()
    descriptions = _property_descriptions_by_prop()

    for prop in ("dd", "bp", "slisaon", "li", "run_speed"):
        spec = registry.property_spec(prop)
        assert spec is not None
        assert spec.description == descriptions[prop]
        assert spec.display_name == _display_description(descriptions[prop])
        assert spec.display_name != spec.full_name


def _property_descriptions_by_prop() -> dict[str, str]:
    descriptions: dict[str, str] = {}
    for name in ("基础组件_属性.csv", "基础信息_属性.csv"):
        for row in _csv_rows(name):
            prop = (row.get("缩写") or row.get("属性名称") or "").strip()
            description = row.get("描述", "").strip()
            if prop and description:
                descriptions[prop] = description
    return descriptions


def _csv_rows(name: str) -> list[dict[str, str]]:
    with (IOT_DOCS / name).open(newline="", encoding="utf-8-sig") as csv_file:
        return list(csv.DictReader(csv_file))


def _display_description(value: str) -> str:
    text = value.strip()
    for separator in ("（", "(", "，", ",", "；", ";", "：", ":"):
        text = text.split(separator, 1)[0].strip()
    return text or value
