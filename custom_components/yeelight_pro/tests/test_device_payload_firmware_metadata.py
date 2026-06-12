"""Device firmware metadata projection tests."""

from __future__ import annotations

from custom_components.yeelight_pro.core.device_metadata import build_fallback_device_info
from custom_components.yeelight_pro.core.device_payload import DevicePayloadBuilder


def test_runtime_metadata_uses_official_fv_property_as_sw_version() -> None:
    """基础组件 fv 应同步为 HA 设备固件版本 metadata."""
    builder = DevicePayloadBuilder()

    data, _gateways = builder.build_runtime_payloads(
        devices=[
            {
                "id": 304784340,
                "name": "客厅筒灯 2",
                "category": "light",
                "pid": 200,
                "roomId": 397,
                "properties": [
                    {"propId": "p", "value": True},
                    {"propId": "l", "value": 70},
                    {"propId": "fv", "value": "1.2.80"},
                ],
            }
        ],
        gateways=[],
        product_schemas={},
        apply_runtime_overrides=lambda payload: payload,
        rooms=[{"id": "397", "name": "客厅"}],
    )

    device_info = data[304784340]["ha_device_instance"]["device_info"]
    assert device_info["sw_version"] == "1.2.80"


def test_runtime_metadata_uses_indexed_fv_param_as_sw_version() -> None:
    """局域网/组件化 key 里的 0-fv 也应作为官方固件版本处理."""
    builder = DevicePayloadBuilder()

    data, _gateways = builder.build_runtime_payloads(
        devices=[
            {
                "id": 304784341,
                "name": "客厅筒灯 3",
                "category": "light",
                "pid": 200,
                "roomId": 397,
                "params": {"p": True, "l": 70, "0-fv": "1.3.0"},
            }
        ],
        gateways=[],
        product_schemas={},
        apply_runtime_overrides=lambda payload: payload,
        rooms=[{"id": "397", "name": "客厅"}],
    )

    device_info = data[304784341]["ha_device_instance"]["device_info"]
    assert device_info["sw_version"] == "1.3.0"


def test_runtime_metadata_uses_component_state_fv_as_sw_version() -> None:
    """已有 canonical component state 时，fv 仍应进入 HA 固件版本."""
    device_info = build_fallback_device_info(
        {
            "id": 304784342,
            "name": "主卧灯带",
            "category": "light",
            "params": {"p": True, "l": 70},
            "ha_device_instance": {
                "components": [
                    {"component_id": "basic", "state": {"fv": "2.0.1"}},
                ],
            },
        }
    )

    assert device_info is not None
    assert device_info["sw_version"] == "2.0.1"
