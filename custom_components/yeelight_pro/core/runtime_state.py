"""Runtime state merge helpers for Yeelight Pro coordinator payloads."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from types import MappingProxyType
from typing import Any

from ..utils import to_bool

CanonicalRebuilder = Callable[[dict[str, Any]], None]


class RuntimeStateStore:
    """保存运行时状态覆盖，并同步 coordinator 当前载荷."""

    def __init__(self) -> None:
        self._overrides: dict[int, dict[str, Any]] = {}

    @property
    def overrides(self) -> Mapping[int, Mapping[str, Any]]:
        """返回只读覆盖视图，供内部测试和诊断读取."""
        return MappingProxyType(self._overrides)

    def apply_to_device(self, device: dict[str, Any]) -> dict[str, Any]:
        """把已保存的运行时覆盖应用到 normalize 后的设备."""
        device_id = device.get("id")
        if device_id not in self._overrides:
            return device

        overrides = self._overrides[device_id]
        params = overrides.get("params")
        merge_runtime_state_into_payload(
            device,
            params if isinstance(params, Mapping) else {},
            online=overrides.get("online"),
        )
        return device

    def store_update(
        self,
        device_id: int,
        params: Mapping[str, Any],
        *,
        devices: Mapping[int, dict[str, Any]],
        gateways: Mapping[int, dict[str, Any]],
        data: Mapping[int, Any],
        rebuild_canonical: CanonicalRebuilder,
    ) -> None:
        """保存运行时更新，并同步当前已加载的设备/网关载荷."""
        if not params:
            return

        overrides = self._overrides.setdefault(device_id, {})
        override_params = overrides.setdefault("params", {})
        if not isinstance(override_params, dict):
            override_params = {}
            overrides["params"] = override_params
        override_params.update(dict(params))

        online = online_from_params(params)
        if online is not None:
            overrides["online"] = online

        merge_runtime_state_into_loaded_payloads(
            device_id=device_id,
            params=params,
            online=online,
            devices=devices,
            gateways=gateways,
            data=data,
            rebuild_canonical=rebuild_canonical,
        )


def merge_runtime_state_into_loaded_payloads(
    *,
    device_id: int,
    params: Mapping[str, Any],
    online: bool | None,
    devices: Mapping[int, dict[str, Any]],
    gateways: Mapping[int, dict[str, Any]],
    data: Mapping[int, Any],
    rebuild_canonical: CanonicalRebuilder,
) -> None:
    """同步 coordinator 当前持有的设备快照."""
    seen: set[int] = set()
    for device in (
        devices.get(device_id),
        gateways.get(device_id),
        data.get(device_id),
    ):
        if not isinstance(device, dict) or id(device) in seen:
            continue
        seen.add(id(device))
        merge_runtime_state_into_payload(
            device,
            params,
            online=online,
            rebuild_canonical=rebuild_canonical,
        )


def merge_runtime_state_into_payload(
    device: dict[str, Any],
    params: Mapping[str, Any],
    *,
    online: Any = None,
    rebuild_canonical: CanonicalRebuilder | None = None,
) -> None:
    """把运行时属性合并进单个设备载荷."""
    if params:
        device_params = device.setdefault("params", {})
        if not isinstance(device_params, dict):
            device_params = {}
            device["params"] = device_params
        device_params.update(dict(params))

    if online is not None:
        device["online"] = bool(online)

    if rebuild_canonical is not None and isinstance(device.get("product_schema"), Mapping):
        rebuild_canonical(device)
        return

    merge_runtime_state_into_canonical_payload(
        device,
        params,
        online=online,
    )


def merge_runtime_state_into_canonical_payload(
    device: Mapping[str, Any],
    params: Mapping[str, Any],
    *,
    online: Any = None,
) -> None:
    """兼容手工构造的 canonical payload，同步组件状态."""
    instance = device.get("ha_device_instance")
    if not isinstance(instance, dict):
        return

    if online is not None:
        instance["online"] = bool(online)

    components = instance.get("components")
    if not isinstance(components, list):
        return

    for component in components:
        if not isinstance(component, dict):
            continue
        if online is not None:
            component["available"] = bool(online)
        state = component.setdefault("state", {})
        if not isinstance(state, dict):
            state = {}
            component["state"] = state
        for raw_key, value in params.items():
            key = str(raw_key)
            component_index, plain_key = split_indexed_runtime_key(key)
            if key in state:
                state[key] = value
            elif component_index is not None:
                if component_matches_index(component, component_index):
                    state[plain_key] = value
            elif plain_key in state or len(components) == 1:
                state[plain_key] = value


def online_from_params(params: Mapping[str, Any]) -> bool | None:
    """从运行时 params 提取在线状态语义."""
    return to_bool(params["o"], default=True) if "o" in params else None


def split_indexed_runtime_key(key: str) -> tuple[str | None, str]:
    """拆分 Yeelight 组件属性 key，兼容 plain key."""
    index, separator, prop_name = key.partition("-")
    if separator and index.isdigit() and prop_name:
        return index, prop_name
    return None, key


def component_matches_index(
    component: Mapping[str, Any],
    component_index: str,
) -> bool:
    """判断手工 canonical 组件是否匹配 indexed runtime key."""
    if str(component.get("index", "")) == component_index:
        return True
    component_id = str(component.get("component_id", component.get("componentId", "")))
    return component_id.endswith(f"_{component_index}")
