"""LAN sensor value normalization tests."""

from __future__ import annotations

from custom_components.yeelight_pro.core.lan_sensor_values import (
    normalize_lan_device_params,
)


def test_lan_temperature_humidity_normalizes_raw_integer_temperature() -> None:
    """LAN type=136 的整数 t 使用协议文档定义的 t/100。"""
    assert normalize_lan_device_params({"t": 2534, "h": 58}, lan_type=136) == {
        "t": 25.34,
        "h": 58,
    }


def test_lan_temperature_humidity_preserves_actual_float_temperature() -> None:
    """已是实际摄氏值的浮点温度不能被二次缩放。"""
    assert normalize_lan_device_params({"t": 24.5, "h": 58}, lan_type=136) == {
        "t": 24.5,
        "h": 58,
    }


def test_lan_temperature_humidity_does_not_scale_other_lan_types() -> None:
    """浴霸/温控等其他 LAN type 的 t 不是温湿度传感器缩放语义。"""
    assert normalize_lan_device_params({"t": 26}, lan_type=2049) == {"t": 26}
