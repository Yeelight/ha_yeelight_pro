"""Runtime device payload model-name refinement tests."""

from __future__ import annotations

from custom_components.yeelight_pro.core.device_payload import DevicePayloadBuilder


def test_runtime_metadata_refines_broad_model_labels_from_device_names() -> None:
    """云端只给 broad model/category 时，HA 设备型号仍应尽量友好具体."""
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

    assert data[501]["device_info"]["model"] == "台灯"
    assert data[502]["device_info"]["model"] == "吊灯"
    assert data[503]["device_info"]["model"] == "感应夜灯"
    assert data[504]["device_info"]["model"] == "智能开关"
    assert data[505]["device_info"]["model"] == "暖风机"


def test_runtime_metadata_refines_chinese_generic_model_labels() -> None:
    """云端已回填中文泛化型号时，HA 设备详情仍应显示具体品类。"""
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

    assert data[601]["device_info"]["model"] == "镜前灯"
    assert data[602]["device_info"]["model"] == "操作台灯"
    assert data[603]["device_info"]["model"] == "衣柜灯"
    assert data[604]["device_info"]["model"] == "智能开关"
