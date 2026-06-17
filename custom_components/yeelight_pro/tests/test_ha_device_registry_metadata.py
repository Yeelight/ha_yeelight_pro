"""Home Assistant device-registry metadata normalization tests."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.yeelight_pro.const import DOMAIN
from custom_components.yeelight_pro.ha_device_registry import (
    _sync_existing_device_metadata,
    async_sync_gateway_devices,
)

from .ha_device_registry_helpers import (
    DeviceRegistryCoordinator,
    device_payload,
    fallback_device_payload,
)


def _entry() -> MockConfigEntry:
    return MockConfigEntry(domain=DOMAIN, entry_id="entry-1")


async def test_sync_gateway_devices_clears_legacy_runtime_model_id() -> None:
    """旧 runtime-* 内部型号不应继续显示在 HA 设备详情中."""
    device_registry = _ModelIdDeviceRegistry()
    existing = SimpleNamespace(
        id="device-1",
        identifiers={(DOMAIN, "304784336")},
        connections=set(),
        manufacturer="Yeelight",
        model="继电器开关",
        name="墙壁开关1",
        model_id="runtime-relay_switch",
    )

    updated = _sync_existing_device_metadata(
        cast(Any, device_registry),
        existing,
        device_info=fallback_device_payload(identifier="304784336")["device_info"],
        identifiers={(DOMAIN, "304784336"), (DOMAIN, "device:304784336")},
        connections=set(),
    )

    assert updated.model_id == "YL-201"
    assert device_registry.updated_devices == [(
        "device-1",
        {
            "model": "墙壁开关",
            "model_id": "YL-201",
            "merge_identifiers": {(DOMAIN, "device:304784336")},
        },
    )]


async def test_sync_gateway_devices_drops_runtime_model_id_without_replacement() -> None:
    """无真实产品型号时，应清除历史 runtime-*，不要继续暴露内部兜底值."""
    device_registry = _ModelIdDeviceRegistry()
    existing = SimpleNamespace(
        id="device-1",
        identifiers={(DOMAIN, "304784337")},
        connections=set(),
        manufacturer="Yeelight",
        model="灯具",
        name="无 PID 灯",
        model_id="runtime-light",
    )
    device_info = {
        "identifiers": [[DOMAIN, "304784337"]],
        "manufacturer": "Yeelight",
        "model": "灯具",
        "name": "无 PID 灯",
    }

    updated = _sync_existing_device_metadata(
        cast(Any, device_registry),
        existing,
        device_info=device_info,
        identifiers={(DOMAIN, "304784337")},
        connections=set(),
    )

    assert updated.model_id is None
    assert device_registry.updated_devices == [
        ("device-1", {"model_id": None})
    ]


async def test_sync_gateway_devices_replaces_generic_model_label_without_model_id() -> None:
    """旧 registry 里泛化型号也应被替换，避免设备页继续显示大类."""
    device_registry = _ModelIdDeviceRegistry()
    existing = SimpleNamespace(
        id="device-1",
        identifiers={(DOMAIN, "304784338")},
        connections=set(),
        manufacturer="Yeelight",
        model="继电器开关",
        name="厨房双键开关",
        model_id=None,
    )
    device_info = {
        "identifiers": [[DOMAIN, "304784338"]],
        "manufacturer": "Yeelight",
        "model": "relay_switch",
        "name": "厨房双键开关",
    }

    updated = _sync_existing_device_metadata(
        cast(Any, device_registry),
        existing,
        device_info=device_info,
        identifiers={(DOMAIN, "304784338")},
        connections=set(),
    )

    assert updated.model_id is None
    assert device_registry.updated_devices == []


async def test_sync_gateway_devices_does_not_wrap_unknown_generic_model() -> None:
    """缺少能力或 category 证据时，不用伪设备型号掩盖问题."""
    device_registry = _ModelIdDeviceRegistry()
    existing = SimpleNamespace(
        id="device-1",
        identifiers={(DOMAIN, "304784340")},
        connections=set(),
        manufacturer="Yeelight",
        model="灯具",
        name="未知设备",
        model_id=None,
    )
    device_info = {
        "identifiers": [[DOMAIN, "304784340"]],
        "manufacturer": "Yeelight",
        "model": "light",
        "name": "未知设备",
    }

    updated = _sync_existing_device_metadata(
        cast(Any, device_registry),
        existing,
        device_info=device_info,
        identifiers={(DOMAIN, "304784340")},
        connections=set(),
    )

    assert updated.model_id is None
    assert device_registry.updated_devices == []


async def test_sync_gateway_devices_normalizes_canonical_generic_model(
    hass: HomeAssistant,
) -> None:
    """canonical device_info 里的 light/relay_switch 也不能进入 HA 型号字段."""
    entry = _entry()
    entry.add_to_hass(hass)
    coordinator = DeviceRegistryCoordinator({
        "device-1": device_payload(
            identifier="304784339",
            name="厨房双键开关",
            model="relay_switch",
            category="relay_switch",
        )
    })

    await async_sync_gateway_devices(hass, entry, coordinator)

    device = dr.async_get(hass).async_get_device(
        identifiers={(DOMAIN, "304784339")}
    )
    assert device is not None
    assert device.model == "继电器开关"


async def test_sync_gateway_devices_prefers_capability_specific_model(
    hass: HomeAssistant,
) -> None:
    """设备详情型号应来自能力证据，覆盖旧的粗 light/relay_switch 大类。"""
    entry = _entry()
    entry.add_to_hass(hass)
    coordinator = DeviceRegistryCoordinator({
        "contact": device_payload(
            identifier="311930423",
            name="玄关门磁传感器",
            model="门磁传感器",
            suggested_area="玄关",
        ),
        "curtain": device_payload(
            identifier="311930424",
            name="客厅窗帘电机",
            model="窗帘",
            suggested_area="客厅",
        ),
        "light": device_payload(
            identifier="311930425",
            name="餐厅吊灯",
            model="色温灯",
            suggested_area="餐厅",
        ),
    })

    await async_sync_gateway_devices(hass, entry, coordinator)

    registry = dr.async_get(hass)
    models = {
        identifier: registry.async_get_device(identifiers={(DOMAIN, identifier)}).model
        for identifier in ("311930423", "311930424", "311930425")
    }
    assert models == {
        "311930423": "门磁传感器",
        "311930424": "窗帘",
        "311930425": "色温灯",
    }


async def test_sync_gateway_devices_uses_screen_name_for_weak_models() -> None:
    """已有弱型号时，设备详情可用官方屏类名称作展示兜底."""
    device_registry = _ModelIdDeviceRegistry()
    existing = SimpleNamespace(
        id="device-1",
        identifiers={(DOMAIN, "40266156")},
        connections=set(),
        manufacturer="Yeelight",
        model="开关灯",
        name="S全面屏",
        model_id=None,
    )
    device_registry.devices[existing.id] = existing
    device_info = {
        "identifiers": [[DOMAIN, "40266156"]],
        "manufacturer": "Yeelight",
        "model": "开关灯",
        "name": "S全面屏",
    }

    updated = _sync_existing_device_metadata(
        cast(Any, device_registry),
        existing,
        device_info=device_info,
        identifiers={(DOMAIN, "40266156")},
        connections=set(),
    )

    assert updated.model == "全面屏"
    assert device_registry.updated_devices == [
        ("device-1", {"model": "全面屏", "model_id": None})
    ]


async def test_sync_gateway_devices_replaces_generic_temp_control_model_from_components() -> None:
    """已有温控大类型号应由官方组件结构刷新为具体控制器类型."""
    device_registry = _ModelIdDeviceRegistry()
    existing = SimpleNamespace(
        id="device-1",
        identifiers={(DOMAIN, "40266069")},
        connections=set(),
        manufacturer="Yeelight",
        model="温控设备",
        name="温控器1",
        model_id=None,
    )
    device_registry.devices[existing.id] = existing
    device_info = {
        "identifiers": [[DOMAIN, "40266069"]],
        "manufacturer": "Yeelight",
        "model": "温控设备",
        "name": "温控器1",
        "category": "temp_control",
        "ha_product_model": {
            "components": [
                {
                    "component_id": "air_conditioner",
                    "category": "air_conditioner",
                    "name": "air conditioner",
                }
            ]
        },
    }

    updated = _sync_existing_device_metadata(
        cast(Any, device_registry),
        existing,
        device_info=device_info,
        identifiers={(DOMAIN, "40266069")},
        connections=set(),
    )

    assert updated.model == "空调控制器"
    assert device_registry.updated_devices == [
        ("device-1", {"model": "空调控制器", "model_id": None})
    ]


async def test_sync_gateway_devices_keeps_specific_screen_product_model() -> None:
    """真实具体型号不能被设备名里的结构词覆盖."""
    device_registry = _ModelIdDeviceRegistry()
    existing = SimpleNamespace(
        id="device-1",
        identifiers={(DOMAIN, "40266145")},
        connections=set(),
        manufacturer="Yeelight",
        model="开关控制器",
        name="Yeelight Pro S系列AI智慧屏Ultra",
        model_id=None,
    )
    device_registry.devices[existing.id] = existing
    device_info = {
        "identifiers": [[DOMAIN, "40266145"]],
        "manufacturer": "Yeelight",
        "model": "Yeelight Pro S系列AI智慧屏Ultra",
        "name": "Yeelight Pro S系列AI智慧屏Ultra",
    }

    updated = _sync_existing_device_metadata(
        cast(Any, device_registry),
        existing,
        device_info=device_info,
        identifiers={(DOMAIN, "40266145")},
        connections=set(),
    )

    assert updated.model == "Yeelight Pro S系列AI智慧屏Ultra"
    assert device_registry.updated_devices == [
        (
            "device-1",
            {"model": "Yeelight Pro S系列AI智慧屏Ultra", "model_id": None},
        )
    ]


class _ModelIdDeviceRegistry:
    """Focused registry double whose update API supports model_id."""

    def __init__(self) -> None:
        self.updated_devices: list[tuple[str, dict[str, object]]] = []
        self.devices: dict[str, SimpleNamespace] = {}

    def async_update_device(
        self,
        device_id: str,
        *,
        manufacturer: str | None = None,
        model: str | None = None,
        name: str | None = None,
        model_id: str | None = None,
        merge_identifiers: set[tuple[str, str]] | None = None,
        merge_connections: set[tuple[str, str]] | None = None,
        **kwargs: object,
    ) -> SimpleNamespace:
        update_kwargs = {
            key: value
            for key, value in {
                "manufacturer": manufacturer,
                "model": model,
                "name": name,
                "model_id": model_id,
                "merge_identifiers": merge_identifiers,
                "merge_connections": merge_connections,
                **kwargs,
            }.items()
        if value is not None or key == "model_id"
        }
        self.updated_devices.append((device_id, update_kwargs))
        current = self.devices.get(device_id, SimpleNamespace(id=device_id))
        for key, value in update_kwargs.items():
            if key.startswith("merge_"):
                continue
            setattr(current, key, value)
        self.devices[device_id] = current
        return current
