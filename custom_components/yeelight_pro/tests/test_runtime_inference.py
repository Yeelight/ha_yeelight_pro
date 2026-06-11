"""Runtime product model inference regression tests."""
from __future__ import annotations

from custom_components.yeelight_pro.converter.product import (
    RuntimeInferredProductModelBuilder,
)


def test_runtime_inferred_product_model_handles_indexed_switches() -> None:
    """Runtime inference must split indexed switch params into components."""
    payload = {
        "model_id": "runtime-switch",
        "type": "switch",
        "category": "relay_switch",
        "params": {
            "1-p": True,
            "2-sp": False,
            "l": 80,
        },
    }

    product = RuntimeInferredProductModelBuilder().build(payload)

    assert product is not None
    assert product.schema_version == "runtime-v1"
    assert [component.component_id for component in product.components] == [
        "switch_1",
        "switch_2",
    ]
    assert product.components[0].properties[0].prop_id == "p"
    assert product.components[1].properties[0].prop_id == "sp"


def test_runtime_inferred_product_model_blocks_indexed_switches_for_non_switch_category() -> None:
    """非开关品类的 indexed p 不能被 runtime inference 拆成 switch 组件."""
    payload = {
        "model_id": "runtime-curtain",
        "type": "switch",
        "category": "curtain",
        "iot_category": "curtain",
        "params": {
            "1-p": True,
            "2-p": False,
            "cp": 40,
            "tp": 90,
        },
    }

    product = RuntimeInferredProductModelBuilder().build(payload)

    assert product is not None
    assert product.product.category == "curtain"
    assert [component.component_id for component in product.components] == ["curtain"]


def test_runtime_inferred_product_model_uses_iot_category_templates() -> None:
    """缺少官方 schema 时应按 Yeelight 品类模板生成组件."""
    payload = {
        "model_id": "runtime-contact",
        "type": "binary_sensor",
        "category": "contact_sensor",
        "iot_category": "contact_sensor",
        "params": {
            "dc": True,
            "alm": False,
            "bl": 90,
        },
    }

    product = RuntimeInferredProductModelBuilder().build(payload)

    assert product is not None
    assert product.product.category == "contact_sensor"
    assert product.components[0].component_id == "contact_sensor"
    assert [prop.prop_id for prop in product.components[0].properties] == [
        "dc",
        "alm",
        "bl",
    ]


def test_runtime_inferred_product_model_prefers_pid_model_id() -> None:
    """Open API 有 pid 时，设备详情不应显示 runtime-light 这类内部型号."""
    payload = {
        "model_id": "runtime-light",
        "pid": 201,
        "type": "light",
        "category": "light",
        "params": {"p": True, "l": 80},
    }

    product = RuntimeInferredProductModelBuilder().build(payload)

    assert product is not None
    assert product.product.model_id == "YL-201"


def test_runtime_inferred_product_model_keeps_category_template_without_params() -> None:
    """云端列表未带当前属性值时，明确品类仍应生成可恢复实体的 schema."""
    payload = {
        "model_id": "runtime-human-empty",
        "type": "light",
        "category": "human_sensor",
        "iot_category": "human_sensor",
        "params": {},
    }

    product = RuntimeInferredProductModelBuilder().build(payload)

    assert product is not None
    assert product.product.category == "human_sensor"
    assert product.components[0].component_id == "human_sensor"
    assert [prop.prop_id for prop in product.components[0].properties] == [
        "mv",
        "alm",
        "luminance",
        "bl",
    ]


def test_runtime_inferred_product_model_blocks_empty_light_fallback() -> None:
    """粗 light 缺少能力证据时不能凭 category 生成假灯 schema。"""
    payload = {
        "model_id": "runtime-light-empty",
        "type": "light",
        "category": "light",
        "iot_category": "light",
        "params": {},
    }

    product = RuntimeInferredProductModelBuilder().build(payload)

    assert product is None


def test_runtime_inferred_product_model_uses_safety_event_component_id() -> None:
    """明确告警事件能力应生成稳定事件组件，不依赖设备名称。"""
    payload = {
        "model_id": "runtime-event-only",
        "type": "light",
        "category": "other",
        "iot_category": "other",
        "params": {},
        "events": [
            {"id": 14, "name": "power.alarm"},
            {"id": 15, "name": "power.normal"},
        ],
    }

    product = RuntimeInferredProductModelBuilder().build(payload)

    assert product is not None
    assert product.product.category == "other"
    assert product.components[0].component_id == "safety_alarm"
    assert [event.semantic for event in product.components[0].events] == [
        "power_alarm",
        "power_normal",
    ]


def test_runtime_inferred_light_template_ranges_are_stable() -> None:
    """Runtime light fallback must keep Yeelight brightness and CT ranges stable."""
    payload = {
        "model_id": "runtime-light",
        "type": "light",
        "category": "light",
        "params": {
            "p": True,
            "l": 75,
            "ct": 4000,
        },
    }

    product = RuntimeInferredProductModelBuilder().build(payload)

    assert product is not None
    props = {prop.prop_id: prop for prop in product.components[0].properties}
    assert props["l"].value_range is not None
    assert props["l"].value_range.min == 1
    assert props["l"].value_range.max == 100
    assert props["l"].value_range.step == 1
    assert props["ct"].value_range is not None
    assert props["ct"].value_range.min == 2700
    assert props["ct"].value_range.max == 6500
    assert props["ct"].value_range.step is None


def test_runtime_builder_infers_fresh_air_component_from_documented_props() -> None:
    """vmcp/vmcf 应生成易来新风组件，而不是粗 temp_control/climate 组件."""
    product = RuntimeInferredProductModelBuilder().build({
        "device_id": "fresh-air-runtime",
        "category": "temp_control",
        "params": {"vmcp": True, "vmcf": 30},
    })

    assert product is not None
    assert product.product.category == "temp_control"
    [component] = product.components
    assert component.component_id == "fresh_air"
    assert component.name == "新风"
    assert component.category == "fresh air"
    assert component.capabilities == ["onoff", "speed"]
    assert {prop.prop_id for prop in component.properties} == {"vmcp", "vmcf"}
