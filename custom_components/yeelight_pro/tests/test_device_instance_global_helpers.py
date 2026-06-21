"""Global helper component conversion regressions."""

from __future__ import annotations

from custom_components.yeelight_pro.converter.device import (
    YeelightLanDeviceInstanceConverter,
)
from custom_components.yeelight_pro.converter.product import (
    YeelightProductSchemaConverter,
)


def test_device_converter_keeps_global_other_music_helper_controls() -> None:
    """official global music helper 组件无状态时也应保留给 helper 投影."""
    product = YeelightProductSchemaConverter().convert(
        {
            "pid": 17000007,
            "name": "Smart screen",
            "category": "gateway",
            "components": [
                {
                    "cid": 44,
                    "name": "basic",
                    "type": 1,
                    "properties": [{"propId": "name"}, {"propId": "o"}],
                },
                {
                    "cid": 27,
                    "name": "music control",
                    "type": 1,
                    "category": "other",
                    "properties": [
                        {
                            "propId": "mpmp",
                            "format": "boolean",
                            "operators": ["set"],
                        },
                        {
                            "propId": "mppm",
                            "format": "uint16",
                            "operators": ["set"],
                            "valueRange": {"min": 0, "max": 10, "step": 1},
                        },
                    ],
                },
            ],
        }
    )

    device = YeelightLanDeviceInstanceConverter().convert(
        {
            "id": "smart-screen-1",
            "name": "6.9 inch smart screen",
            "pid": 17000007,
            "online": True,
            "params": {},
        },
        product_model=product,
    )

    assert [component.component_id for component in device.components] == [
        "other_global"
    ]
    assert device.components[0].component_type == "global"
    assert device.components[0].state == {}
