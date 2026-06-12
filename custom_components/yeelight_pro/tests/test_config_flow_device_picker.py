"""Config-flow real cloud device picker tests."""
from __future__ import annotations

from custom_components.yeelight_pro.config_flow_device_picker import (
    NO_DEVICE_SELECTED_SENTINEL,
    cloud_devices_schema,
    device_choices,
    device_import_filter_for_selected_devices,
    selected_device_ids_from_input,
)
from custom_components.yeelight_pro.const import (
    CONF_DEVICE_IMPORT_FILTER_INCLUDE_DEVICES,
)


def test_device_choices_normalize_open_api_rows() -> None:
    """真实设备 picker 应兼容开放平台字段别名并跳过无 ID 行."""
    choices = device_choices([
        {"deviceId": "dev-2", "deviceName": "Wall Switch", "category": "switch"},
        {"id": 1, "name": "Ceiling", "roomName": "Living"},
        {"name": "Missing ID"},
    ])

    assert [(item.device_id, item.label) for item in choices] == [
        ("1", "Ceiling (Living)"),
        ("dev-2", "Wall Switch"),
    ]


def test_device_choices_use_friendly_type_labels() -> None:
    """设备 picker 的括号类型应使用产品/品类事实，不显示裸 category."""
    choices = device_choices([
        {
            "id": "dev-1",
            "name": "三键智能开关",
            "category": "relay_switch",
            "model": "relay_switch",
            "pid": 854019,
            "roomName": "玄关",
        },
        {
            "id": "dev-2",
            "name": "客厅主灯",
            "category": "light",
            "productName": "E20 射灯",
            "roomName": "客厅",
        },
    ])

    labels = {item.device_id: item.label for item in choices}
    assert labels == {
        "dev-1": "三键智能开关 (Yeelight Pro S21 智能墙壁开关-三键 / 玄关)",
        "dev-2": "客厅主灯 (E20 射灯 / 客厅)",
    }
    assert "relay_switch" not in " ".join(labels.values())
    assert "(light" not in " ".join(labels.values()).lower()


def test_device_choices_use_openapi_room_aliases() -> None:
    """真实设备 picker 应显示 OpenAPI 房间/区域别名，不只依赖 roomName."""
    choices = device_choices([
        {
            "id": "dev-1",
            "deviceName": "厨房双键开关",
            "category": "relay_switch",
            "model": "relay_switch",
            "room": "厨房",
        },
        {
            "id": "dev-2",
            "deviceName": "过道筒灯",
            "category": "light",
            "model": "light",
            "areaName": "过道",
        },
    ])

    labels = {item.device_id: item.label for item in choices}
    assert labels == {
        "dev-1": "厨房双键开关 (继电器开关 / 厨房)",
        "dev-2": "过道筒灯 (灯具 / 过道)",
    }
    assert "relay_switch" not in " ".join(labels.values())
    assert "light" not in " ".join(labels.values())


def test_device_choices_use_runtime_capability_type_before_broad_category() -> None:
    """picker 有属性能力证据时，应显示具体设备类型而不是粗 category."""
    choices = device_choices([
        {
            "id": "dev-1",
            "name": "玄关门磁",
            "category": "light",
            "model": "light",
            "properties": [
                {"propId": "dc", "value": False, "format": "boolean"},
                {"propId": "alm", "value": False, "format": "boolean"},
            ],
            "roomName": "玄关",
        },
        {
            "id": "dev-2",
            "name": "墙壁开关",
            "category": "light",
            "model": "light",
            "subDeviceList": [
                {
                    "index": 1,
                    "category": "relay_switch",
                    "properties": [
                        {"propId": "p", "value": True, "operators": ["set"]},
                    ],
                },
            ],
            "roomName": "客厅",
        },
    ])

    labels = {item.device_id: item.label for item in choices}
    assert labels == {
        "dev-1": "玄关门磁 (门磁传感器 / 玄关)",
        "dev-2": "墙壁开关 (开关控制器 / 客厅)",
    }
    assert "灯具" not in " ".join(labels.values())


def test_cloud_devices_schema_uses_multi_select_options() -> None:
    """设备选择表单应使用 HA 原生多选 selector."""
    choices = device_choices([
        {"id": "dev-1", "name": "Light"},
        {"id": "dev-2", "name": "Curtain"},
    ])

    schema = cloud_devices_schema(choices, ["dev-1", "dev-2"]).schema
    field = next(iter(schema))
    device_selector = schema[field]

    assert field.schema == CONF_DEVICE_IMPORT_FILTER_INCLUDE_DEVICES
    assert field.default() == ["dev-1", "dev-2"]
    assert device_selector.selector_type == "select"
    assert device_selector.config["multiple"] is True
    assert device_selector.config["options"] == [
        {"value": "dev-2", "label": "Curtain"},
        {"value": "dev-1", "label": "Light"},
    ]


def test_device_choices_do_not_infer_type_from_user_name() -> None:
    """用户设备名不能作为 picker 类型证据。"""
    choices = device_choices([
        {
            "id": "dev-1",
            "name": "厨房烟雾传感器",
            "category": "light",
            "model": "light",
            "roomName": "厨房",
        }
    ])

    assert [(item.device_id, item.label) for item in choices] == [
        ("dev-1", "厨房烟雾传感器 (灯具 / 厨房)")
    ]


def test_selected_device_ids_default_to_all_devices() -> None:
    """首次展示设备 picker 时默认选择全部真实设备."""
    choices = device_choices([
        {"id": "dev-1", "name": "Light"},
        {"id": "dev-2", "name": "Curtain"},
    ])

    assert selected_device_ids_from_input(None, choices) == ["dev-2", "dev-1"]


def test_selected_device_ids_from_input_drops_unknown_choices() -> None:
    """表单提交值必须来自当前真实设备 choices。"""
    choices = device_choices([
        {"id": "dev-1", "name": "Light"},
        {"id": "dev-2", "name": "Curtain"},
    ])

    assert selected_device_ids_from_input(
        {CONF_DEVICE_IMPORT_FILTER_INCLUDE_DEVICES: ["dev-1", "unknown-device"]},
        choices,
    ) == ["dev-1"]


def test_selected_device_filter_is_disabled_for_all_or_empty_house() -> None:
    """全选或空家庭不应启用无意义过滤规则."""
    choices = device_choices([
        {"id": "dev-1", "name": "Light"},
        {"id": "dev-2", "name": "Curtain"},
    ])

    assert device_import_filter_for_selected_devices(
        ["dev-1", "dev-2"],
        choices,
    ) == {"enabled": False, "mode": "or", "include": {}, "exclude": {}}
    assert device_import_filter_for_selected_devices(
        [],
        (),
    ) == {"enabled": False, "mode": "or", "include": {}, "exclude": {}}


def test_selected_device_filter_includes_only_selected_devices() -> None:
    """取消部分设备后应写入 devices include 过滤规则."""
    choices = device_choices([
        {"id": "dev-1", "name": "Light"},
        {"id": "dev-2", "name": "Curtain"},
    ])

    assert device_import_filter_for_selected_devices(["dev-1"], choices) == {
        "enabled": True,
        "mode": "or",
        "include": {"devices": ["dev-1"]},
        "exclude": {},
    }


def test_selected_device_filter_drops_unknown_selected_ids() -> None:
    """表单提交中的未知设备 ID 不应写入持久化 import filter。"""
    choices = device_choices([
        {"id": "dev-1", "name": "Light"},
        {"id": "dev-2", "name": "Curtain"},
    ])

    assert device_import_filter_for_selected_devices(
        ["dev-1", "dev-secret"],
        choices,
    ) == {
        "enabled": True,
        "mode": "or",
        "include": {"devices": ["dev-1"]},
        "exclude": {},
    }


def test_selected_device_filter_preserves_import_none_intent() -> None:
    """全取消时应显式保存不会匹配真实设备的 include 规则."""
    choices = device_choices([
        {"id": "dev-1", "name": "Light"},
        {"id": "dev-2", "name": "Curtain"},
    ])

    assert device_import_filter_for_selected_devices([], choices) == {
        "enabled": True,
        "mode": "or",
        "include": {"devices": [NO_DEVICE_SELECTED_SENTINEL]},
        "exclude": {},
    }
