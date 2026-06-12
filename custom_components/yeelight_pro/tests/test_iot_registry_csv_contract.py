"""CSV-backed Yeelight IoT registry contract tests."""

from __future__ import annotations

from custom_components.yeelight_pro.capabilities import iot_registry
from .iot_registry_csv_helpers import (
    IOT_DOCS,
    component_key,
    component_properties_from_iot_docs,
    csv_readable,
    csv_rows,
    csv_writable,
    property_access_by_prop,
)


def test_registry_categories_match_iot_category_csv() -> None:
    """registry 品类必须来自易来基础信息品类表."""
    registry = iot_registry()
    expected = {row["名称"] for row in csv_rows("基础信息_品类列表.csv")}

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

    for row in csv_rows("基础信息_组件列表.csv"):
        if not row["品类"] or not row["变量别名"]:
            continue
        component = registry.component_map.get(component_key(row["变量别名"]))
        if component is None:
            missing.append(row["变量别名"])
            continue
        assert component.category == row["品类"]

    assert missing == []


def test_registry_covers_all_documented_component_identities() -> None:
    """CSV 组件即使没有变量别名，也必须按 id 和中文名进入 registry."""
    registry = iot_registry()
    missing: list[tuple[str, str]] = []

    for row in csv_rows("基础信息_组件列表.csv"):
        component_id = row["id"].strip()
        component_name = row["组件名称"].strip()
        if not component_id or not component_name:
            continue
        component = registry.component_map.get(component_id)
        if component is None:
            missing.append((component_id, component_name))
            continue
        assert component.name == component_name
        assert registry.component_map.get(component_key(component_name)) == component

    assert missing == []


def test_registry_component_set_matches_iot_component_csv() -> None:
    """OpenAPI registry 不能混入组件表以外的猜测组件."""
    registry = iot_registry()
    expected = {int(row["id"]) for row in csv_rows("基础信息_组件列表.csv") if row["id"]}

    assert {component.component_id for component in registry.components} == expected


def test_registry_uses_csv_access_for_documented_properties() -> None:
    """registry 属性读写边界必须匹配易来属性表."""
    registry = iot_registry()
    csv_access = property_access_by_prop()

    missing: list[str] = []
    mismatches: list[tuple[str, str, bool, bool]] = []
    for prop, access in csv_access.items():
        spec = registry.property_spec(prop)
        if spec is None:
            missing.append(prop)
            continue
        expected = (csv_readable(access), csv_writable(access))
        actual = (spec.readable, spec.writable)
        if actual != expected:
            mismatches.append((prop, access, spec.readable, spec.writable))

    assert missing == []
    assert mismatches == []


def test_registry_covers_iot_event_type_csv() -> None:
    """registry 事件 ID 必须覆盖易来事件类型表，不能借用错误 ID。"""
    registry = iot_registry()
    known_events = {event.normalized for event in registry.events}

    for row in csv_rows("基础信息_事件类型.csv"):
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
    expected = component_properties_from_iot_docs()
    mismatches: list[tuple[str, tuple[str, ...], tuple[str, ...]]] = []

    for row in csv_rows("基础信息_组件列表.csv"):
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


def test_registry_property_components_are_derived_from_component_properties() -> None:
    """属性反向组件归属必须由官方组件属性集派生，避免双向事实漂移."""
    registry = iot_registry()
    expected: dict[str, list[str]] = {}
    for component in registry.components:
        for prop in component.properties:
            expected.setdefault(prop, []).append(component.alias)

    mismatches: list[tuple[str, tuple[str, ...], tuple[str, ...]]] = []
    for prop, component_aliases in expected.items():
        spec = registry.property_spec(prop)
        assert spec is not None
        expected_components = tuple(component_aliases)
        if spec.components != expected_components:
            mismatches.append((prop, expected_components, spec.components))

    assert mismatches == []
    cpt_spec = registry.property_spec("cpt")
    mv_spec = registry.property_spec("mv")
    assert cpt_spec is not None
    assert mv_spec is not None
    assert cpt_spec.components == ("basic",)
    assert mv_spec.components == (
        "human detection sensor",
        "human occupancy sensor",
        "human illuminance sensor",
        "human body infrared sensor",
        "dali human detection sensor",
        "zonalShieldIlluminanceRadarSensor",
    )


def test_registry_does_not_promote_undocumented_compatibility_props() -> None:
    """非易来 CSV/协议支撑的旧兼容属性不能进入官方 IoT registry."""
    registry = iot_registry()

    for prop in ("c_waf", "c_xy", "dir", "lv", "on"):
        assert registry.property_spec(prop) is None
        assert registry.property_capability(prop) is None


def test_registry_extra_properties_are_only_lan_documented_runtime_props() -> None:
    """CSV 外属性必须有易来协议资料支撑。"""
    registry = iot_registry()
    csv_props = set(property_access_by_prop())
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

