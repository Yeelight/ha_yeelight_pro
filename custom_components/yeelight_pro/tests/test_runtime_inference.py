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


def test_runtime_inferred_product_model_does_not_use_user_device_name_as_model() -> None:
    """运行时型号名不能由用户自定义设备名推断。"""
    payload = {
        "model_id": "runtime-light",
        "name": "厨房烟雾传感器",
        "type": "light",
        "category": "light",
        "params": {"p": True, "l": 80},
    }

    product = RuntimeInferredProductModelBuilder().build(payload)

    assert product is not None
    assert product.product.model == "light"


def test_runtime_inferred_product_model_keeps_metadata_without_empty_template() -> None:
    """云端列表未带能力值时，只保留品类元数据，不生成假属性组件."""
    payload = {
        "model_id": "runtime-human-empty",
        "type": "light",
        "category": "human_sensor",
        "iot_category": "human_sensor",
        "params": {},
    }

    product = RuntimeInferredProductModelBuilder().build(payload)

    assert product is not None
    assert product.schema_version == "runtime-v1"
    assert product.product.category == "human_sensor"
    assert product.product.categories == ["human_sensor"]
    assert product.components == []


def test_runtime_inferred_product_model_blocks_empty_light_fallback() -> None:
    """粗 light 缺少能力证据时只保留品类元数据，不生成假灯组件。"""
    payload = {
        "model_id": "runtime-light-empty",
        "type": "light",
        "category": "light",
        "iot_category": "light",
        "params": {},
    }

    product = RuntimeInferredProductModelBuilder().build(payload)

    assert product is not None
    assert product.schema_version == "runtime-v1"
    assert product.product.category == "light"
    assert product.product.categories == ["light"]
    assert product.components == []


def test_runtime_inferred_product_model_ignores_generic_ha_platform_metadata() -> None:
    """HA 平台词 sensor/binary_sensor 不能伪装成易来物模型品类。"""
    product = RuntimeInferredProductModelBuilder().build({
        "model_id": "runtime-sensor-empty",
        "type": "sensor",
        "category": "sensor",
        "params": {},
    })

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


def test_runtime_inferred_contact_sensor_uses_registry_events_without_payload_events() -> None:
    """顶层 runtime 缺少 events 行时，门磁唯一官方组件应补齐事件入口。"""
    payload = {
        "model_id": "runtime-contact-events",
        "type": "binary_sensor",
        "category": "contact_sensor",
        "params": {"dc": True, "alm": False},
    }

    product = RuntimeInferredProductModelBuilder().build(payload)

    assert product is not None
    assert product.components[0].component_id == "contact_sensor"
    assert [event.semantic for event in product.components[0].events] == [
        "door_open",
        "door_close",
        "door_alarm",
        "door_normal",
    ]


def test_runtime_inferred_human_sensor_without_component_identity_does_not_guess_events() -> None:
    """人体大类缺少官方组件身份时，不用 category 猜测 motion 事件。"""
    payload = {
        "model_id": "runtime-human-events",
        "type": "binary_sensor",
        "category": "human_sensor",
        "params": {"mv": True},
    }

    product = RuntimeInferredProductModelBuilder().build(payload)

    assert product is not None
    assert product.components[0].component_id == "human_sensor"
    assert product.components[0].events == []


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
    assert component.category == "temp_control"
    assert component.capabilities == ["onoff", "speed"]
    assert {prop.prop_id for prop in component.properties} == {"vmcp", "vmcf"}


def test_runtime_builder_uses_product_catalog_when_only_pid_is_available() -> None:
    """云端只给 pid/category 时，应按易来产品构成生成产品名和组件轮廓."""
    product = RuntimeInferredProductModelBuilder().build({
        "device_id": "s21-double-switch",
        "pid": 854018,
        "category": "light",
        "params": {},
    })

    assert product is not None
    assert product.schema_version == "catalog-v1"
    assert product.product.model_id == "YL-854018"
    assert product.product.model == "公开产品（无线开关通道）"
    assert product.product.category == "relay_switch"
    assert [component.component_id for component in product.components[:2]] == [
        "basic",
        "backlight_indicator",
    ]
    switch_components = [
        component
        for component in product.components
        if component.category == "relay_switch"
    ]
    assert [component.component_id for component in switch_components] == [
        "switch_1",
        "switch_2",
    ]
    assert [component.index for component in switch_components] == [1, 2]
    assert all(
        {"sp", "l", "slisaon"}.issubset({prop.prop_id for prop in component.properties})
        for component in switch_components
    )


def test_runtime_builder_expands_documented_mixed_product_components() -> None:
    """多组件产品应按官方每组件数量展开，不把产品总数当作单类数量."""
    product = RuntimeInferredProductModelBuilder().build({
        "device_id": "s-series-scene-switch",
        "pid": 1509378,
        "category": "light",
        "params": {},
    })

    assert product is not None
    assert product.schema_version == "catalog-v1"
    assert product.product.category is None
    assert product.product.categories == ["scene_panel", "relay_switch"]
    assert sum(component.category == "scene_panel" for component in product.components) == 12
    assert sum(component.category == "relay_switch" for component in product.components) == 4
    assert [component.component_id for component in product.components[-4:]] == [
        "switch_1",
        "switch_2",
        "switch_3",
        "switch_4",
    ]
    assert "scene_panel" not in {component.component_id for component in product.components}


def test_runtime_builder_catalog_never_overrides_live_property_evidence() -> None:
    """属性能力与产品目录冲突时，运行时属性能力仍优先."""
    product = RuntimeInferredProductModelBuilder().build({
        "device_id": "misleading-catalog-row",
        "pid": 854018,
        "category": "light",
        "params": {"mv": True, "luminance": 188, "sens_range": 3},
    })

    assert product is not None
    assert product.product.model_id == "YL-854018"
    assert product.product.model == "照度传感器"
    runtime_component = product.components[-1]
    assert runtime_component.component_id == "light_sensor"
    assert runtime_component.category == "light_sensor"
    assert {"mv", "luminance", "sens_range"} & {
        prop.prop_id for prop in runtime_component.properties
    }


def test_runtime_builder_contact_capability_name_overrides_conflicting_catalog() -> None:
    """门磁能力与产品目录冲突时，设备型号显示能力类型而不是错误产品名."""
    product = RuntimeInferredProductModelBuilder().build({
        "device_id": "misleading-contact-row",
        "pid": 854018,
        "category": "light",
        "params": {"dc": False, "alm": True},
    })

    assert product is not None
    assert product.product.model_id == "YL-854018"
    assert product.product.model == "门磁传感器"
    assert [component.component_id for component in product.components] == [
        "contact_sensor"
    ]
