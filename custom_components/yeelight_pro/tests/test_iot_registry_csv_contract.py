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


def test_registry_does_not_add_non_iot_device_categories() -> None:
    """fan/outlet 不是易来官方品类，不能进入 IoT category registry."""
    registry = iot_registry()
    categories = {item.category for item in registry.categories}

    assert "fan" not in categories
    assert "outlet" not in categories


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


def test_registry_covers_all_documented_component_identities() -> None:
    """CSV 组件即使没有变量别名，也必须按 id 和中文名进入 registry."""
    registry = iot_registry()
    missing: list[tuple[str, str]] = []

    for row in _csv_rows("基础信息_组件列表.csv"):
        component_id = row["id"].strip()
        component_name = row["组件名称"].strip()
        if not component_id or not component_name:
            continue
        component = registry.component_map.get(component_id)
        if component is None:
            missing.append((component_id, component_name))
            continue
        assert component.name == component_name
        assert registry.component_map.get(_component_key(component_name)) == component

    assert missing == []


def test_registry_component_set_matches_iot_component_csv() -> None:
    """OpenAPI registry 不能混入组件表以外的猜测组件."""
    registry = iot_registry()
    expected = {int(row["id"]) for row in _csv_rows("基础信息_组件列表.csv") if row["id"]}

    assert {component.component_id for component in registry.components} == expected


def test_registry_uses_csv_access_for_documented_properties() -> None:
    """registry 属性读写边界必须匹配易来属性表."""
    registry = iot_registry()
    csv_access = _property_access_by_prop()

    missing: list[str] = []
    mismatches: list[tuple[str, str, bool, bool]] = []
    for prop, access in csv_access.items():
        spec = registry.property_spec(prop)
        if spec is None:
            missing.append(prop)
            continue
        expected = (_csv_readable(access), _csv_writable(access))
        actual = (spec.readable, spec.writable)
        if actual != expected:
            mismatches.append((prop, access, spec.readable, spec.writable))

    assert missing == []
    assert mismatches == []


def test_registry_covers_iot_event_type_csv() -> None:
    """registry 事件 ID 必须覆盖易来事件类型表，不能借用错误 ID。"""
    registry = iot_registry()
    known_events = {event.normalized for event in registry.events}

    for row in _csv_rows("基础信息_事件类型.csv"):
        event_id = row["id"].strip()
        event_text = row["文本"].strip()
        if not event_id or not event_text:
            continue
        normalized_by_id = registry.normalize_event_type(int(event_id))
        normalized_by_text = registry.normalize_event_type(event_text)
        assert normalized_by_id in known_events
        assert normalized_by_text == normalized_by_id


def test_registry_keeps_documented_component_identity_without_name_guessing() -> None:
    """关键新增组件按 CSV 品类识别，不依赖用户设备名称."""
    registry = iot_registry()

    assert registry.component_map["runway panel"].category == "scene_panel"
    assert registry.component_map["75"].name == "智慧屏组件"
    assert registry.component_map["智慧屏组件"].component_id == 75
    assert registry.component_map["zonalshieldilluminanceradarsensor"].category == "light_sensor"
    assert registry.component_map["lift control"].category == "other"
    assert registry.component_platform_hint("zonalShieldIlluminanceRadarSensor") == "sensor"


def test_registry_keeps_high_risk_component_property_sets_from_csv() -> None:
    """组件属性必须保留规范化后的易来物模型事实."""
    registry = iot_registry()

    assert registry.component_map["wireless switch channel"].properties == (
        "l",
        "sbp",
        "slisaon",
        "slisaon_rdy",
        "mock",
        "name",
        "icon",
        "3rdPartySyncBitmask",
        "io",
        "run_speed",
        "run_speed_rdy",
        "li",
        "sp",
        "sdt",
    )
    assert registry.component_map["switch control"].properties == (
        "p",
        "slisaon",
        "bp",
        "slisaon_rdy",
        "3rdPartySyncBitmask",
        "name",
        "icon",
        "mock",
        "io",
        "jen",
        "jdef",
        "jtm",
    )
    assert registry.component_map["fresh air"].properties == (
        "3rdPartySyncBitmask",
        "vmcp",
        "vmcf",
        "name",
        "icon",
        "o",
        "io",
    )
    assert registry.component_map["human illuminance sensor"].properties == (
        "mv",
        "blp",
        "li",
        "sens_range",
        "lumi_setting",
        "delay_time",
        "name",
        "icon",
        "io",
        "3rdPartySyncBitmask",
        "luminance",
    )
    assert registry.component_map["temp control"].properties == (
        "p",
        "bhm",
        "do",
        "ve",
        "fa",
        "he",
        "t",
        "tgt",
        "3rdPartySyncBitmask",
        "name",
        "icon",
        "io",
        "sa",
        "ss",
        "rst",
        "dntm",
    )
    assert registry.component_map["zebra blinds"].properties == (
        "cp",
        "tp",
        "li",
        "rd",
        "open_type",
        "tra",
        "cra",
        "trs",
        "rs",
        "rrd",
        "rg",
        "3rdPartySyncBitmask",
        "name",
        "icon",
        "io",
        "run_speed",
    )


def test_registry_component_properties_match_iot_csv_and_property_memberships() -> None:
    """registry 组件属性集必须匹配组件表和属性表的联合事实."""
    registry = iot_registry()
    expected = _component_properties_from_iot_docs()
    mismatches: list[tuple[str, tuple[str, ...], tuple[str, ...]]] = []

    for row in _csv_rows("基础信息_组件列表.csv"):
        component_id = row["id"].strip()
        if not component_id:
            continue
        component = registry.component_map.get(component_id)
        assert component is not None
        expected_props = expected.get(component_id, ())
        if component.properties != expected_props:
            mismatches.append(
                (
                    component.alias,
                    expected_props,
                    component.properties,
                )
            )

    assert mismatches == []


def test_registry_does_not_promote_undocumented_compatibility_props() -> None:
    """非易来 CSV/协议支撑的旧兼容属性不能进入官方 IoT registry."""
    registry = iot_registry()

    for prop in ("c_waf", "c_xy", "dir", "lv", "on"):
        assert registry.property_spec(prop) is None
        assert registry.property_capability(prop) is None


def test_registry_extra_properties_are_only_lan_documented_runtime_props() -> None:
    """CSV 外属性必须有易来协议资料支撑。"""
    registry = iot_registry()
    csv_props = set(_property_access_by_prop())
    extras = sorted({item.prop for item in registry.properties} - csv_props)
    lan_doc = (IOT_DOCS / "Yeelight Pro局域网协议.md").read_text(encoding="utf-8")

    assert extras == ["h", "level"]
    assert "### 2\\.11 温湿度传感器" in lan_doc
    assert "|h|湿度值" in lan_doc
    assert "|level|- 光感档位定义" in lan_doc
    capability = registry.property_capability("h")
    assert capability is not None
    assert capability.device_class == "humidity"
    level = registry.property_spec("level")
    assert level is not None
    assert level.readable is True
    assert level.writable is False


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


def _component_properties_from_iot_docs() -> dict[str, tuple[str, ...]]:
    """Return component properties normalized from Yeelight CSV sources."""
    rows = _csv_rows("基础信息_组件列表.csv")
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
        for row in _csv_rows(name):
            prop = _property_alias(row.get("缩写") or row.get("属性名称"), property_names)
            for component_name in _split_csv_list(
                row.get("组件", "") or row.get("父记录", "")
            ):
                component_id = component_ids_by_name.get(
                    _normalized_component_name(component_name)
                )
                if component_id is None:
                    continue
                _append_unique(properties.setdefault(component_id, []), prop)

    return {
        component_id: tuple(prop for prop in props if prop)
        for component_id, props in properties.items()
    }


def _component_names_by_id(rows: list[dict[str, str]]) -> dict[str, set[str]]:
    """Return normalized component lookup names by id."""
    names: dict[str, set[str]] = {}
    for row in rows:
        component_id = row["id"].strip()
        if not component_id:
            continue
        values = {row.get("组件名称", ""), row.get("变量别名", "")}
        names[component_id] = {
            normalized
            for value in values
            if (normalized := _normalized_component_name(value))
        }
    return names


def _property_name_aliases() -> dict[str, str]:
    """Return CSV property display names mapped to canonical abbreviations."""
    aliases = {
        "connectivity protocols type": "cpt",
        "localtoken": "ltk",
        "run power": "run_power",
        "support relay": "support_rl",
    }
    for name in ("基础信息_属性.csv", "基础组件_属性.csv"):
        for row in _csv_rows(name):
            prop_name = row.get("属性名称", "").strip()
            prop_alias = (row.get("缩写") or prop_name).strip()
            if not prop_name or not prop_alias:
                continue
            aliases[_normalized_component_name(prop_name)] = prop_alias
            aliases[_normalized_component_name(prop_alias)] = prop_alias
    return aliases


def _property_alias(value: str | None, aliases: dict[str, str]) -> str:
    if not value:
        return ""
    text = value.strip()
    return aliases.get(_normalized_component_name(text), text)


def _split_csv_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _append_unique(values: list[str], value: str) -> None:
    if value and value not in values:
        values.append(value)


def _normalized_component_name(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(value.strip().lower().replace("_", " ").replace("-", " ").split())


def _csv_readable(value: str) -> bool:
    lowered = value.lower()
    return "read" in lowered or "读" in value


def _csv_writable(value: str) -> bool:
    lowered = value.lower()
    return "write" in lowered or "写" in value
