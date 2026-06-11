"""CSV-backed Yeelight IoT registry contract tests."""

from __future__ import annotations

import csv
from pathlib import Path

from custom_components.yeelight_pro.capabilities import iot_registry


IOT_DOCS = Path(__file__).resolve().parents[3] / "docs" / "iot"


def test_registry_categories_match_iot_category_csv() -> None:
    """registry 品类必须来自易来基础信息品类表."""
    registry = iot_registry()
    expected = {row["名称"] for row in _csv_rows("基础信息_品类列表.csv")}

    assert {item.category for item in registry.categories} == expected


def test_registry_covers_all_documented_categorized_components() -> None:
    """带品类的普通/全局组件必须可被 registry 识别."""
    registry = iot_registry()
    missing: list[str] = []

    for row in _csv_rows("基础信息_组件列表.csv"):
        if not row["品类"] or not row["变量别名"]:
            continue
        component = registry.component_map.get(_component_key(row["变量别名"]))
        if component is None:
            missing.append(row["变量别名"])
            continue
        assert component.category == row["品类"]

    assert missing == []


def test_registry_uses_csv_access_for_documented_properties() -> None:
    """registry 属性读写边界必须匹配易来属性表."""
    registry = iot_registry()
    csv_access = _property_access_by_prop()

    for prop in (
        "3rdPartySyncBitmask",
        "height",
        "keys_visible",
        "lumi_setting",
        "mp_keys",
        "name",
        "ntOn",
        "sens_range",
        "sens_shield",
        "vol",
        "weather_hidden",
    ):
        spec = registry.property_spec(prop)
        assert spec is not None
        assert spec.readable is _csv_readable(csv_access[prop])
        assert spec.writable is _csv_writable(csv_access[prop])


def test_registry_keeps_documented_component_identity_without_name_guessing() -> None:
    """关键新增组件按 CSV 品类识别，不依赖用户设备名称."""
    registry = iot_registry()

    assert registry.component_map["runway panel"].category == "scene_panel"
    assert registry.component_map["zonalshieldilluminanceradarsensor"].category == "light_sensor"
    assert registry.component_map["lift control"].category == "other"
    assert registry.component_platform_hint("zonalShieldIlluminanceRadarSensor") == "binary_sensor"


def _csv_rows(name: str) -> list[dict[str, str]]:
    with (IOT_DOCS / name).open(newline="", encoding="utf-8-sig") as csv_file:
        return list(csv.DictReader(csv_file))


def _component_key(value: str) -> str:
    return value.lower().replace("_", " ").replace("-", " ").strip()


def _property_access_by_prop() -> dict[str, str]:
    access: dict[str, str] = {}
    for name in ("基础组件_属性.csv", "基础信息_属性.csv"):
        for row in _csv_rows(name):
            prop = (row.get("缩写") or row.get("属性名称") or "").strip()
            if prop:
                access[prop] = row.get("权限", "")
    return access


def _csv_readable(value: str) -> bool:
    lowered = value.lower()
    return "read" in lowered or "读" in value


def _csv_writable(value: str) -> bool:
    lowered = value.lower()
    return "write" in lowered or "写" in value
