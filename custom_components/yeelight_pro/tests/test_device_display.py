"""Device display helper tests."""

from __future__ import annotations

from custom_components.yeelight_pro.device_display import (
    channel_name_label,
    device_name_label,
    registry_model_value,
    device_type_label,
    suggested_entity_object_id,
    switch_channel_count_hint,
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
        "productName": "E20 射灯",
    }) == "E20 射灯"


def test_device_type_label_replaces_broad_categories() -> None:
    """粗 category 不应直接出现在 picker 括号类型中."""
    assert device_type_label({"category": "relay_switch"}) == "易来开关设备"
    assert device_type_label({"category": "light"}) == "易来照明设备"


def test_device_type_label_normalizes_cloud_category_aliases() -> None:
    """云端大小写/空格 category 不能直接污染设备类型展示."""
    assert device_type_label({"category": "Light"}) == "易来照明设备"
    assert device_type_label({"category": "Relay Switch"}) == "易来开关设备"
    assert device_type_label({"category": "relay-switch"}) == "易来开关设备"
    assert device_type_label({"category": "灯具"}) == "易来照明设备"
    assert device_type_label({"category": "继电器开关"}) == "易来开关设备"


def test_device_type_label_uses_iot_category_not_ha_sensor_platform() -> None:
    """传感器类摘要应显示易来设备品类，而不是 HA sensor/binary_sensor 平台词."""
    assert device_type_label({"category": "contact_sensor"}) == "门磁传感器"
    assert device_type_label({"category": "human_sensor"}) == "人体传感器"
    assert device_type_label({"category": "light_sensor"}) == "照度传感器"


def test_sensor_registry_models_require_category_or_property_evidence() -> None:
    """Registry model 不能只凭用户设备名推断传感器类型。"""
    assert not is_generic_model_label("人体传感器")
    assert registry_model_value({"name": "客厅人体传感器"}, "Yeelight Pro 设备") == "Yeelight Pro 设备"
    assert registry_model_value({"category": "human_sensor"}, "Yeelight Pro 设备") == "人体传感器"
    assert registry_model_value({"params": {"dc": True}}, "Yeelight Pro 设备") == "门磁传感器"


def test_friendly_specific_model_name_never_returns_broad_registry_model() -> None:
    """HA device registry 的 model 不能继续显示灯具/继电器开关等泛化词."""
    for payload in (
        {"category": "light", "name": "未识别灯具", "model": "灯具"},
        {"category": "relay_switch", "name": "未知开关", "model": "继电器开关"},
        {"category": "temp_control", "name": "温控器", "model": "温控设备"},
        {"category": "other", "name": "未知设备", "model": "易来设备"},
    ):
        assert not is_generic_model_label(friendly_specific_model_name(payload))


def test_device_type_label_uses_category_not_user_name() -> None:
    """设备类型展示不能被用户自定义名称改写。"""
    assert device_type_label({"category": "light", "name": "书房台灯"}) == "易来照明设备"
    assert device_type_label({"category": "relay_switch", "name": "厨房智能开关"}) == "易来开关设备"
    assert device_type_label({"category": "temp_control", "name": "卫生间暖风机"}) == "易来温控设备"


def test_device_type_label_omits_unknown_generic_device() -> None:
    """没有可推断型号或品类时，picker 只显示设备名/房间."""
    assert device_type_label({"name": "Unnamed"}) is None


def test_chinese_generic_model_labels_fall_back_to_category() -> None:
    """中文泛化型号不能触发设备名推断。"""
    assert device_type_label({"category": "light", "model": "灯具", "name": "卫生间镜前灯"}) == "易来照明设备"
    assert device_type_label({"category": "relay_switch", "model": "继电器开关", "name": "厨房智能开关"}) == "易来开关设备"


def test_generic_ha_platform_category_does_not_become_iot_category() -> None:
    """HA 平台词 sensor 不能被当作易来 IoT 设备品类展示."""
    for payload in (
        {"category": "sensor", "name": "主卧温湿度传感器"},
        {"category": "binary_sensor", "name": "主卧人体传感器"},
        {"category": "传感器", "name": "主卧人体传感器"},
    ):
        assert infer_iot_category(payload) is None
        assert device_type_label(payload) is None


def test_safety_sensor_name_does_not_affect_display_type() -> None:
    """设备名不能把 light 大类显示成烟雾传感器类型。"""
    payload = {"category": "light", "name": "厨房烟雾传感器"}

    assert infer_iot_category(payload) == "light"
    assert device_type_label(payload) == "易来照明设备"


def test_friendly_model_id_replaces_runtime_category_when_pid_exists() -> None:
    """已有 runtime-* 内部型号时，HA 设备详情应优先显示稳定产品 ID."""
    assert friendly_model_id({"model_id": "runtime-light", "pid": 201}) == "YL-201"
    assert friendly_model_id({"model_id": "YL-Explicit", "pid": 201}) == "YL-Explicit"


def test_channel_name_label_humanizes_indexed_switch_channels() -> None:
    """多键开关通道名应使用友好中文名称."""
    assert channel_name_label(index=1) == "第 1 键"
    assert channel_name_label(index=2) == "第 2 键"
    assert channel_name_label(index=7) == "第 7 键"
    assert channel_name_label(index=8) == "第 8 键"
    assert channel_name_label(index=12) == "第 12 键"


def test_channel_name_label_uses_positional_names_for_known_switches() -> None:
    """双键/三键墙壁开关应显示左中右，而不是 1/2/3 或一键二键."""
    assert channel_name_label(
        index=1,
        device_payload={"name": "厨房双键开关"},
    ) == "左键"
    assert channel_name_label(
        index=2,
        device_payload={"name": "厨房双键开关"},
    ) == "右键"
    assert channel_name_label(
        index=2,
        device_payload={"name": "玄关三键智能开关"},
    ) == "中键"
    assert channel_name_label(
        index=3,
        device_payload={"name": "玄关三键智能开关"},
    ) == "右键"


def test_channel_name_label_preserves_real_component_name() -> None:
    """官方组件名如左键/右键应优先于索引 fallback."""
    assert channel_name_label(index=1, component={"name": "左键"}) == "左键"
    assert channel_name_label(index=2, component={"name": "switch_2"}) == "第 2 键"
    assert channel_name_label(index=3, component={"name": "3"}) == "第 3 键"
    assert channel_name_label(index=4, component={"name": "按键4"}) == "第 4 键"
    assert channel_name_label(index=1, component={"name": "一键"}) == "第 1 键"
    assert channel_name_label(index=2, component={"name": "二键"}) == "第 2 键"


def test_channel_name_label_humanizes_generated_component_ids() -> None:
    """button/key/scene_button 等组件 ID 不应直接显示成 1/2/3."""
    assert channel_name_label(index=None, component={"component_id": "button_1"}) == "第 1 键"
    assert channel_name_label(index=None, component={"component_id": "key_2"}) == "第 2 键"
    assert (
        channel_name_label(index=None, component={"component_id": "scene_button_3"})
        == "第 3 键"
    )
    assert channel_name_label(
        index=None,
        component={"component_id": "scene_control_button_2"},
        device_payload={"name": "玄关三键情景面板"},
    ) == "中键"


def test_channel_name_label_humanizes_indexed_component_suffixes() -> None:
    """fan_1/curtain_1 等带索引组件 ID 不应直接暴露到实体名称."""
    for component_id in (
        "air_conditioner_1",
        "curtain_1",
        "fan_1",
        "human_sensor_1",
        "sensor_1",
    ):
        assert channel_name_label(
            index=None,
            component={"component_id": component_id},
            device_payload={"name": "厨房双键开关"},
        ) == "左键"


def test_channel_name_label_replaces_generated_chinese_names_for_known_switches() -> None:
    """云端一键/二键/三键这类生成名应按真实开关路数换成方位名."""
    assert channel_name_label(
        index=1,
        component={"name": "一键"},
        device_payload={"name": "厨房双键开关"},
    ) == "左键"
    assert channel_name_label(
        index=2,
        component={"desc": "二键"},
        device_payload={"name": "厨房双键开关"},
    ) == "右键"
    assert channel_name_label(
        index=3,
        component={"name": "三键"},
        device_payload={"name": "玄关三键智能开关"},
    ) == "右键"
    assert channel_name_label(
        index=1,
        component={"name": "无线开关通道"},
        device_payload={"name": "厨房双键开关"},
    ) == "左键"
    assert channel_name_label(
        index=2,
        component={"desc": "无线开关通道"},
        device_payload={"name": "厨房双键开关"},
    ) == "右键"


def test_channel_name_label_infers_positions_from_runtime_channels() -> None:
    """设备名不含双键/三键时，应从运行时多路通道推断方位名."""
    payload = {
        "name": "墙壁开关1",
        "params": {"1-p": True, "2-p": False, "3-p": True},
    }

    assert switch_channel_count_hint(payload) == 3
    assert channel_name_label(
        index=1,
        component={"name": "一键"},
        device_payload=payload,
    ) == "左键"
    assert channel_name_label(
        index=2,
        component={"name": "二键"},
        device_payload=payload,
    ) == "中键"
    assert channel_name_label(
        index=3,
        component={"name": "三键"},
        device_payload=payload,
    ) == "右键"


def test_channel_name_label_infers_positions_from_openapi_subdevices() -> None:
    """OpenAPI 子设备已证明多按键时，不应再显示 1/2/3 或第 N 键."""
    payload = {
        "name": "按键",
        "subDeviceList": [
            {"index": 1, "name": "scene control button", "category": "scene_panel"},
            {"index": 2, "name": "scene control button", "category": "scene_panel"},
            {"index": 3, "name": "scene control button", "category": "scene_panel"},
        ],
    }

    assert switch_channel_count_hint(payload) == 3
    assert channel_name_label(
        index=1,
        component={"name": "1"},
        device_payload=payload,
    ) == "左键"
    assert channel_name_label(
        index=2,
        component={"name": "2"},
        device_payload=payload,
    ) == "中键"
    assert channel_name_label(
        index=3,
        component={"name": "3"},
        device_payload=payload,
    ) == "右键"


def test_channel_name_label_does_not_position_generic_relays() -> None:
    """纯多路继电器没有物理左右语义时，仍使用第 N 键."""
    payload = {
        "name": "多路继电器",
        "params": {"1-p": True, "2-sp": False},
    }

    assert switch_channel_count_hint(payload) is None
    assert channel_name_label(index=1, device_payload=payload) == "第 1 键"
    assert channel_name_label(index=2, device_payload=payload) == "第 2 键"


def test_explicit_switch_channel_count_overrides_stale_runtime_channels() -> None:
    """设备名明确双键时，运行时残留第三路不能阻止 stale 清理."""
    payload = {
        "name": "厨房双键开关",
        "params": {"1-p": True, "2-p": False, "3-p": True},
    }

    assert switch_channel_count_hint(payload) == 2
    assert channel_name_label(index=1, device_payload=payload) == "左键"
    assert channel_name_label(index=2, device_payload=payload) == "右键"


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


def test_switch_channel_count_hint_from_friendly_product_name() -> None:
    """设备名/型号里的双键三键应作为通道路数约束."""
    assert switch_channel_count_hint({"name": "厨房双键开关"}) == 2
    assert switch_channel_count_hint({"productName": "三键智能开关"}) == 3
    assert switch_channel_count_hint({"name": "Yeelight Pro S20系列8键情景开关"}) == 8
    assert switch_channel_count_hint({"name": "S系列情景开关", "model": "4开关，12情景按键"}) == 12
    assert switch_channel_count_hint({"name": "普通继电器"}) is None
