"""Yeelight IoT 产品构成目录 contract tests."""

from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

from custom_components.yeelight_pro.capabilities import iot_registry
from custom_components.yeelight_pro.capabilities.product_catalog import (
    csv_product_catalog,
    md_only_product_catalog,
)
from custom_components.yeelight_pro.capabilities.product_catalog_data import (
    IOT_PRODUCT_SPECS,
)


IOT_DOCS = Path(__file__).resolve().parents[3] / "docs" / "iot"


def test_registry_product_catalog_matches_iot_product_csv() -> None:
    """产品构成目录必须覆盖易来产品构成表中的全部 pid."""
    registry = iot_registry()
    expected = {
        _product_pid(row["pid"]): row
        for row in _csv_rows("基础信息_产品构成.csv")
        if row["pid"].strip()
    }

    assert {item.pid for item in IOT_PRODUCT_SPECS} == set(expected)
    assert set(csv_product_catalog()) == set(expected)
    assert len(csv_product_catalog()) == 112
    assert set(md_only_product_catalog()) == {17000012, 17000013}
    assert set(registry.product_catalog) == set(expected) | {17000012, 17000013}
    assert len(registry.product_catalog) == 114

    public_switch = registry.product_spec(854018)
    assert public_switch is not None
    assert public_switch.name == "公开产品（无线开关通道）"
    assert public_switch.normal_components == ("无线开关通道",)
    assert public_switch.normal_component_count == "2"

    dali_gateway = registry.product_spec("1.7000001e+07")
    assert dali_gateway is not None
    assert dali_gateway.pid == 17000001
    assert dali_gateway.bridge_protocols == ("dali协议",)


def test_registry_product_catalog_includes_lan_markdown_only_products() -> None:
    """LAN 协议 Markdown 补充 PID 应进入运行时 fallback，但不污染 CSV 主表."""
    registry = iot_registry()

    sky_light = registry.product_spec(17000012)
    assert sky_light is not None
    assert sky_light.name == "公开产品（色温灯、人在传感器）"
    assert sky_light.normal_components == ("色温灯", "人在传感器")

    chandelier = registry.product_spec(17000013)
    assert chandelier is not None
    assert chandelier.name == "公开产品（色温灯、彩光灯、TOF传感器）"
    assert chandelier.normal_components == ("色温灯", "彩光灯", "TOF传感器")

    assert 17000012 not in csv_product_catalog()
    assert 17000013 not in csv_product_catalog()


def test_registry_product_catalog_uses_public_sanitized_names() -> None:
    """公开目录只保留组件/品类级名称，不能携带商业备注."""
    registry = iot_registry()

    for row in _csv_rows("基础信息_产品构成.csv"):
        pid = _product_pid(row["pid"])
        if pid is None:
            continue
        product = registry.product_spec(pid)
        assert product is not None
        assert product.name == row["产品名称"]
        assert product.name.startswith("公开产品（")
        assert row["备注"] == ""


def test_registry_product_catalog_components_and_protocols_are_documented() -> None:
    """产品构成里的组件和协议必须能回到组件/协议 registry."""
    registry = iot_registry()
    missing_components: list[tuple[int, str]] = []
    missing_protocols: list[tuple[int, str]] = []

    for row in _csv_rows("基础信息_产品构成.csv"):
        pid = _product_pid(row["pid"])
        if pid is None:
            continue
        product = registry.product_spec(pid)
        assert product is not None
        for component_name in _csv_list(row["普通组件"]):
            if component_name and registry.component_map.get(_component_key(component_name)) is None:
                missing_components.append((pid, component_name))
        for protocol in (row["连接协议"], *_csv_list(row["支持的桥协议"])):
            if protocol and registry.protocol(protocol) is None:
                missing_protocols.append((pid, protocol))

    assert missing_components == []
    assert missing_protocols == []


def test_registry_product_catalog_expands_fixed_component_counts() -> None:
    """单组件多通道产品应按普通组件数目展开，动态数目不猜测."""
    registry = iot_registry()

    assert [component.name for component in registry.product_components(854018)] == [
        "无线开关通道",
        "无线开关通道",
    ]
    assert registry.product_category_candidates(854018) == ("relay_switch",)
    assert len(registry.product_components(657408)) == 1
    assert registry.product_components(657408)[0].name == "未定义子设备"
    assert registry.product_protocols(17000007)[0].key == "direct"
    assert {item.key for item in registry.product_protocols(17000007)} == {
        "direct",
        "mesh",
        "matter",
    }


def test_registry_product_catalog_exposes_only_safe_global_components() -> None:
    """产品目录只投影有 HA 安全语义的全局组件，不暴露网络密钥类组件."""
    registry = iot_registry()

    assert [
        component.alias
        for component in registry.product_projectable_global_components(8522496)
    ] == ["basic", "battery"]
    assert [
        component.alias
        for component in registry.product_projectable_global_components(657408)
    ] == ["basic", "HVAC gateway"]


def test_registry_product_catalog_expands_documented_mixed_component_counts() -> None:
    """多普通组件产品只按官方明确的每组件数量展开."""
    registry = iot_registry()

    s_switch = registry.product_components(1509378)
    assert [component.name for component in s_switch].count("情景按键") == 12
    assert [component.name for component in s_switch].count("无线开关通道") == 4
    assert len(s_switch) == 16

    smart_screen = registry.product_components(17000007)
    assert [component.name for component in smart_screen] == [
        "网关",
        "音乐组件",
        "开关",
        "开关",
    ]

    dali_input = registry.product_components(17000005)
    assert [component.name for component in dali_input] == [
        "dali情景按键",
        "dali人感传感器",
        "dali光感传感器",
    ]


def test_registry_product_model_from_catalog_keeps_mixed_component_identity() -> None:
    """产品模型组件 ID 应体现易来组件身份，不能退化成 HA 平台词."""
    registry = iot_registry()

    contact_model = registry.product_model_from_catalog(8522496)
    assert contact_model is not None
    assert [
        component.component_id for component in contact_model.components
    ] == ["basic", "battery", "contact_sensor"]
    assert "mesh" not in {component.component_id for component in contact_model.components}

    s_switch_model = registry.product_model_from_catalog(1509378)
    assert s_switch_model is not None
    assert s_switch_model.product.category is None
    assert s_switch_model.product.categories == ["scene_panel", "relay_switch"]
    assert [
        component.component_id for component in s_switch_model.components[:3]
    ] == [
        "basic",
        "backlight_indicator",
        "scene_panel_1",
    ]
    assert [
        component.component_id for component in s_switch_model.components[-4:]
    ] == [
        "switch_1",
        "switch_2",
        "switch_3",
        "switch_4",
    ]
    assert sum(component.category == "scene_panel" for component in s_switch_model.components) == 12
    assert sum(component.category == "relay_switch" for component in s_switch_model.components) == 4

    smart_screen_model = registry.product_model_from_catalog(17000007)
    assert smart_screen_model is not None
    assert smart_screen_model.product.categories == ["gateway", "other", "relay_switch"]
    assert [component.component_id for component in smart_screen_model.components] == [
        "basic",
        "gateway",
        "other",
        "switch_1",
        "switch_2",
    ]

    sky_light_model = registry.product_model_from_catalog(17000012)
    assert sky_light_model is not None
    assert sky_light_model.product.categories == ["light", "human_sensor"]
    assert [component.component_id for component in sky_light_model.components] == [
        "light",
        "human_sensor",
    ]

    chandelier_model = registry.product_model_from_catalog(17000013)
    assert chandelier_model is not None
    assert chandelier_model.product.categories == ["light", "other"]
    assert [component.component_id for component in chandelier_model.components] == [
        "light_1",
        "light_2",
        "other",
    ]
    tof_component = chandelier_model.components[-1]
    assert [event.name for event in tof_component.events] == ["handwave"]


def test_registry_product_model_uses_iot_property_display_names() -> None:
    """产品目录生成的 canonical 属性名应使用易来中文描述."""
    registry = iot_registry()

    model = registry.product_model_from_catalog(262146)
    assert model is not None
    component = next(
        item
        for item in model.components
        if any(prop.prop_id == "dd" for prop in item.properties)
    )
    labels = {prop.prop_id: prop.name for prop in component.properties}
    semantics = {prop.prop_id: prop.semantic for prop in component.properties}

    assert labels["dd"] == "默认渐变时长"
    assert labels["bp"] == "上电后状态"
    assert labels["slisaon"] == "是否开启闪断"
    assert semantics["dd"] == "default duration"


def _csv_rows(name: str) -> list[dict[str, str]]:
    with (IOT_DOCS / name).open(newline="", encoding="utf-8-sig") as csv_file:
        return list(csv.DictReader(csv_file))


def _component_key(value: str) -> str:
    return value.lower().replace("_", " ").replace("-", " ").strip()


def _csv_list(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _product_pid(value: str) -> int | None:
    text = value.strip()
    if not text:
        return None
    try:
        return int(Decimal(text))
    except (InvalidOperation, ValueError):
        return None
