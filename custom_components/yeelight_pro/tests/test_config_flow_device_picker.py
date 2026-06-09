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
        ("dev-2", "Wall Switch (switch)"),
    ]


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


def test_selected_device_ids_default_to_all_devices() -> None:
    """首次展示设备 picker 时默认选择全部真实设备."""
    choices = device_choices([
        {"id": "dev-1", "name": "Light"},
        {"id": "dev-2", "name": "Curtain"},
    ])

    assert selected_device_ids_from_input(None, choices) == ["dev-2", "dev-1"]


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
