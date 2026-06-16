"""Device display helper tests."""

from __future__ import annotations

from custom_components.yeelight_pro.device_display import (
    device_name_label,
    registry_model_value,
    device_type_label,
    suggested_entity_object_id,
)
from custom_components.yeelight_pro.core.device_classification import (
    friendly_model_id,
    friendly_specific_model_name,
    infer_iot_category,
    is_generic_model_label,
)


def test_device_type_label_prefers_specific_product_model() -> None:
    """设备类型摘要应优先使用官方产品型号/名称."""
    assert device_type_label({
        "category": "light",
        "model": "light",
        "productName": "公开测试射灯",
    }) == "公开测试射灯"


def test_device_type_label_replaces_broad_categories() -> None:
    """粗 category 只能作为最终大类兜底，不包装成伪具体型号."""
    assert device_type_label({"category": "relay_switch"}) == "继电器开关"
    assert device_type_label({"category": "light"}) == "灯具"


def test_device_type_label_normalizes_cloud_category_aliases() -> None:
    """云端大小写/空格 category 不能直接污染设备类型展示."""
    assert device_type_label({"category": "Light"}) == "灯具"
    assert device_type_label({"category": "Relay Switch"}) == "继电器开关"
    assert device_type_label({"category": "relay-switch"}) == "继电器开关"
    assert device_type_label({"category": "灯具"}) == "灯具"
    assert device_type_label({"category": "继电器开关"}) == "继电器开关"


def test_device_type_label_uses_iot_category_not_ha_sensor_platform() -> None:
    """传感器类摘要应显示易来设备品类，而不是 HA sensor/binary_sensor 平台词."""
    assert device_type_label({"category": "contact_sensor"}) == "门磁传感器"
    assert device_type_label({"category": "human_sensor"}) == "人体传感器"
    assert device_type_label({"category": "light_sensor"}) == "照度传感器"


def test_sensor_registry_models_require_category_or_property_evidence() -> None:
    """Registry model 不能只凭用户设备名推断传感器类型。"""
    assert not is_generic_model_label("人体传感器")
    assert registry_model_value({"name": "客厅人体传感器"}, "Yeelight Pro 设备") is None
    assert registry_model_value({"category": "human_sensor"}, "Yeelight Pro 设备") == "人体传感器"
    assert registry_model_value({"params": {"dc": True}}, "Yeelight Pro 设备") == "门磁传感器"


def test_friendly_specific_model_name_exposes_only_specific_evidence() -> None:
    """specific helper 不负责把大类包装成伪具体型号."""
    for payload in (
        {"category": "light", "name": "未识别灯具", "model": "灯具"},
        {"category": "relay_switch", "name": "未知开关", "model": "继电器开关"},
        {"category": "temp_control", "name": "温控器", "model": "温控设备"},
        {"category": "other", "name": "未知设备", "model": "易来设备"},
    ):
        assert friendly_specific_model_name(payload) == ""


def test_device_type_label_uses_category_not_user_name() -> None:
    """设备类型展示不能被用户自定义名称改写。"""
    assert device_type_label({"category": "light", "name": "书房台灯"}) == "灯具"
    assert device_type_label({"category": "relay_switch", "name": "厨房智能开关"}) == "继电器开关"
    assert device_type_label({"category": "temp_control", "name": "卫生间暖风机"}) == "温控设备"


def test_device_type_label_omits_unknown_generic_device() -> None:
    """没有可推断型号或品类时，picker 只显示设备名/房间."""
    assert device_type_label({"name": "Unnamed"}) is None


def test_chinese_generic_model_labels_fall_back_to_category() -> None:
    """中文泛化型号不能触发设备名推断。"""
    assert device_type_label({"category": "light", "model": "灯具", "name": "卫生间镜前灯"}) == "灯具"
    assert device_type_label({"category": "relay_switch", "model": "继电器开关", "name": "厨房智能开关"}) == "继电器开关"


def test_generic_ha_platform_category_does_not_become_iot_category() -> None:
    """HA 平台词 sensor 不能被当作易来 IoT 设备品类展示."""
    for payload in (
        {"category": "sensor", "name": "主卧温湿度传感器"},
        {"category": "binary_sensor", "name": "主卧人体传感器"},
        {"category": "switch", "name": "厨房智能开关"},
        {"category": "传感器", "name": "主卧人体传感器"},
    ):
        assert infer_iot_category(payload) is None
        assert device_type_label(payload) is None


def test_safety_sensor_name_does_not_affect_display_type() -> None:
    """设备名不能把 light 大类显示成烟雾传感器类型。"""
    payload = {"category": "light", "name": "厨房烟雾传感器"}

    assert infer_iot_category(payload) == "light"
    assert device_type_label(payload) == "灯具"


def test_friendly_model_id_replaces_runtime_category_when_pid_exists() -> None:
    """已有 runtime-* 内部型号时，HA 设备详情应优先显示稳定产品 ID."""
    assert friendly_model_id({"model_id": "runtime-light", "pid": 201}) == "YL-201"
    assert friendly_model_id({"model_id": "YL-Explicit", "pid": 201}) == "YL-Explicit"


def test_device_name_label_uses_open_api_aliases() -> None:
    """设备名称应兼容 Open API 字段别名."""
    assert device_name_label({"deviceName": "玄关开关"}, "dev-1") == "玄关开关"
    assert device_name_label({}, "dev-2") == "Device dev-2"


def test_suggested_entity_object_id_uses_friendly_device_name() -> None:
    """主实体 object_id 建议应来自真实设备名，而不是技术 unique_id."""
    assert suggested_entity_object_id(
        {"device_id": "304784333", "name": "厨房操作台灯"},
        entity_name=None,
    ) == "厨房操作台灯"
    assert suggested_entity_object_id(
        {"device_id": "304784336", "name": "厨房智能开关"},
        entity_name="左键",
    ) == "厨房智能开关 左键"
    assert suggested_entity_object_id(
        {"device_id": "304784333", "name": "厨房操作台灯"},
        entity_name="照明",
    ) == "厨房操作台灯"
    assert suggested_entity_object_id(
        {"device_id": "304784333", "name": "彩光灯"},
        entity_name="彩光灯 默认渐变时长",
    ) == "彩光灯 默认渐变时长"

