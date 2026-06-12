"""Runtime device payload model-name refinement tests."""

from __future__ import annotations

from custom_components.yeelight_pro.core.device_payload import DevicePayloadBuilder


def test_runtime_metadata_refines_models_from_capabilities_not_names() -> None:
    """用户设备名不能决定类型，但属性能力可以映射到易来组件名。"""
    builder = DevicePayloadBuilder()

    data, _gateways = builder.build_runtime_payloads(
        devices=[
            {
                "id": 501,
                "name": "书房台灯",
                "category": "light",
                "model": "light",
                "pid": 5010,
                "properties": [{"propId": "p", "value": True}],
            },
            {
                "id": 502,
                "name": "餐厅吊灯",
                "category": "light",
                "model": "light",
                "pid": 5020,
                "properties": [{"propId": "p", "value": True}],
            },
            {
                "id": 503,
                "name": "玄关感应夜灯",
                "category": "light",
                "model": "light",
                "pid": 5030,
                "properties": [{"propId": "p", "value": True}],
            },
            {
                "id": 504,
                "name": "厨房智能开关",
                "category": "relay_switch",
                "model": "relay_switch",
                "pid": 5040,
                "properties": [{"propId": "p", "value": True}],
            },
            {
                "id": 505,
                "name": "卫生间暖风机",
                "category": "temp_control",
                "model": "temp_control",
                "pid": 5050,
                "properties": [{"propId": "acp", "value": True}],
            },
        ],
        gateways=[],
        product_schemas={},
        apply_runtime_overrides=lambda payload: payload,
    )

    assert data[501]["device_info"]["model"] == "开关灯"
    assert data[502]["device_info"]["model"] == "开关灯"
    assert data[503]["device_info"]["model"] == "开关灯"
    assert data[504]["device_info"]["model"] == "开关控制器"
    assert data[505]["device_info"]["model"] == "温控设备"


def test_runtime_metadata_replaces_chinese_generic_model_labels_from_capabilities() -> None:
    """中文泛化型号应按能力映射，不从用户设备名猜具体类型。"""
    builder = DevicePayloadBuilder()

    data, _gateways = builder.build_runtime_payloads(
        devices=[
            {
                "id": 601,
                "name": "卫生间镜前灯",
                "category": "light",
                "model": "灯具",
                "pid": 6010,
                "properties": [{"propId": "p", "value": True}],
            },
            {
                "id": 602,
                "name": "厨房操作台灯",
                "category": "light",
                "model": "灯具",
                "pid": 6020,
                "properties": [{"propId": "p", "value": True}],
            },
            {
                "id": 603,
                "name": "主卧衣柜灯",
                "category": "light",
                "model": "灯具",
                "pid": 6030,
                "properties": [{"propId": "p", "value": True}],
            },
            {
                "id": 604,
                "name": "厨房智能开关",
                "category": "relay_switch",
                "model": "继电器开关",
                "pid": 6040,
                "properties": [{"propId": "p", "value": True}],
            },
        ],
        gateways=[],
        product_schemas={},
        apply_runtime_overrides=lambda payload: payload,
    )

    assert data[601]["device_info"]["model"] == "开关灯"
    assert data[602]["device_info"]["model"] == "开关灯"
    assert data[603]["device_info"]["model"] == "开关灯"
    assert data[604]["device_info"]["model"] == "开关控制器"


def test_runtime_metadata_uses_property_capability_over_conflicting_category() -> None:
    """属性能力与 category 冲突时，设备详情型号以能力为准。"""
    builder = DevicePayloadBuilder()

    data, _gateways = builder.build_runtime_payloads(
        devices=[
            {
                "id": 701,
                "name": "玄关自定义设备",
                "category": "light",
                "model": "light",
                "pid": 7010,
                "properties": [
                    {"propId": "dc", "value": False, "format": "boolean"},
                    {"propId": "alm", "value": False, "format": "boolean"},
                ],
            }
        ],
        gateways=[],
        product_schemas={},
        apply_runtime_overrides=lambda payload: payload,
    )

    assert data[701]["iot_category"] == "contact_sensor"
    assert data[701]["device_info"]["model"] == "门磁传感器"
