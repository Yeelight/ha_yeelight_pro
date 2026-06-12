"""Normalize Yeelight Pro LAN topology nodes into runtime device payloads."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from ..capabilities.platform_contract import platform_candidates_for_payload
from ..utils import to_bool, to_int, to_str
from .device_payload import (
    DevicePayloadBuilder,
    RuntimeOverrideApplier,
    refresh_classification_metadata,
)

NODE_TYPE_ROOM = 1
NODE_TYPE_DEVICE = 2
NODE_TYPE_AREA = 3
NODE_TYPE_GROUP = 4
NODE_TYPE_HOUSE = 5
NODE_TYPE_SCENE = 6

_LIGHT_PARAMS: dict[int, dict[str, Any]] = {
    1: {"p": False},
    2: {"p": False, "l": 100},
    3: {"p": False, "l": 100, "ct": 4000},
    4: {"p": False, "l": 100, "ct": 4000, "c": 0xFFFFFF, "m": 2},
    14: {"p": False, "l": 100, "ct": 4000},
}
_LAN_TYPE_SPECS: dict[int, dict[str, Any]] = {
    1: {"category": "light", "model": "开关灯", "params": _LIGHT_PARAMS[1]},
    2: {"category": "light", "model": "亮度灯", "params": _LIGHT_PARAMS[2]},
    3: {"category": "light", "model": "色温灯", "params": _LIGHT_PARAMS[3]},
    4: {"category": "light", "model": "彩光灯", "params": _LIGHT_PARAMS[4]},
    6: {"category": "curtain", "model": "窗帘", "params": {"cp": 0, "tp": 0}},
    7: {"category": "relay_switch", "model": "继电器开关", "switch_prop": "p", "channels": 2},
    10: {"category": "temp_control", "model": "温控设备", "params": {"acp": False, "actt": 26, "acct": 26}},
    13: {"category": "relay_switch", "model": "继电器开关", "switch_prop": "sp"},
    14: {"category": "light", "model": "色温灯", "params": _LIGHT_PARAMS[14]},
    15: {"category": "temp_control", "model": "温控设备", "params": {"acp": False, "actt": 26, "acct": 26}},
    128: {"category": "scene_panel", "model": "情景面板", "events": ("click", "hold")},
    129: {
        "category": "human_sensor",
        "model": "人体传感器",
        "params": {"mv": False},
        "events": ("motion_detected", "motion_undetected"),
    },
    130: {
        "category": "contact_sensor",
        "model": "门磁传感器",
        "params": {"dc": False, "alm": False},
        "events": ("door_open", "door_close", "door_alarm", "door_normal"),
    },
    132: {"category": "knob_switch", "model": "旋钮开关", "events": ("knob_spin",)},
    134: {
        "category": "light_sensor",
        "model": "照度传感器",
        "params": {"mv": False, "level": 0},
        "events": ("motion_detected", "motion_undetected"),
    },
    135: {"category": "light_sensor", "model": "照度传感器", "params": {"luminance": 0}},
    136: {"category": "other", "model": "温湿度传感器", "params": {"t": 0, "h": 0}},
    138: {
        "category": "human_sensor",
        "model": "人体传感器",
        "params": {"mv": False, "luminance": 0},
        "events": ("motion_detected", "motion_undetected"),
    },
    2049: {"category": "temp_control", "model": "温控设备", "params": {"p": False, "tgt": 26, "t": 26}},
    2052: {"category": "human_sensor", "model": "人体传感器", "events": ("human_enter", "human_leave", "handwave")},
}


@dataclass(slots=True)
class LanTopologyPayloads:
    """从 LAN 拓扑生成的 coordinator 载荷集合。"""

    devices: dict[int, dict[str, Any]] = field(default_factory=dict)
    rooms: list[dict[str, Any]] = field(default_factory=list)
    areas: list[dict[str, Any]] = field(default_factory=list)
    groups: list[dict[str, Any]] = field(default_factory=list)
    houses: list[dict[str, Any]] = field(default_factory=list)
    scenes: list[dict[str, Any]] = field(default_factory=list)


def build_lan_topology_payloads(
    nodes: list[Any],
    *,
    builder: DevicePayloadBuilder,
    apply_runtime_overrides: RuntimeOverrideApplier,
) -> LanTopologyPayloads:
    """从协议定义的 LAN 拓扑节点构建规范运行时载荷。"""
    result = LanTopologyPayloads()
    node_rows = [node for node in nodes if isinstance(node, Mapping)]
    result.rooms = _auxiliary_nodes(node_rows, NODE_TYPE_ROOM)
    result.areas = _auxiliary_nodes(node_rows, NODE_TYPE_AREA)
    result.groups = _typed_auxiliary_nodes(node_rows, NODE_TYPE_GROUP)
    result.houses = _typed_auxiliary_nodes(node_rows, NODE_TYPE_HOUSE)
    result.scenes = _scene_nodes(node_rows)

    for node in node_rows:
        node_id = to_int(node.get("id"))
        if node_id is None or to_int(node.get("nt")) != NODE_TYPE_DEVICE:
            continue

        payload = _device_payload_from_node(node)
        normalized = builder.normalize(payload, {})
        normalized["id"] = node_id
        normalized["device_id"] = node_id
        normalized = apply_runtime_overrides(normalized)
        builder.attach_canonical_models_if_available(
            normalized,
            rooms=result.rooms,
            areas=result.areas,
        )
        _refresh_lan_classification_metadata(normalized)
        result.devices[node_id] = normalized

    return result


def _refresh_lan_classification_metadata(payload: dict[str, Any]) -> None:
    """同步 LAN 节点的 IoT 分类与 HA 平台候选元数据。"""
    refresh_classification_metadata(payload)
    candidates = platform_candidates_for_payload(payload)
    if candidates:
        payload["ha_platform_candidates"] = list(candidates)
    else:
        payload.pop("ha_platform_candidates", None)


def _device_payload_from_node(node: Mapping[str, Any]) -> dict[str, Any]:
    """将单个 LAN Mesh 子设备节点转换为接近 OpenAPI 的载荷。"""
    node_id = to_int(node.get("id"))
    lan_type = to_int(node.get("type"))
    spec = _LAN_TYPE_SPECS.get(lan_type or -1, {})
    category = to_str(spec.get("category")) or "other"
    model = to_str(spec.get("model")) or "易来设备"
    params = _params_for_node(node, spec)

    payload: dict[str, Any] = {
        "id": node_id,
        "device_id": node_id,
        "name": to_str(node.get("n")) or (f"{model} {node_id}" if node_id else model),
        "type": category,
        "category": category,
        "iot_category": category,
        "lan_type": lan_type,
        "node_type": NODE_TYPE_DEVICE,
        "online": True,
        "model": model,
        "modelName": model,
        "productName": model,
        "params": params,
    }
    model_id = _model_id(node, lan_type)
    if model_id is not None:
        payload["model_id"] = model_id
    for source, target in (
        ("roomid", "roomid"),
        ("roomid", "roomId"),
        ("pid", "pid"),
        ("ch_num", "ch_num"),
        ("cids", "cids"),
    ):
        if source in node:
            payload[target] = node[source]
    if subdevices := _subdevices_for_node(node, spec, category):
        payload["subDeviceList"] = subdevices
    if events := _events_for_spec(spec):
        payload["events"] = events
    return payload


def _params_for_node(node: Mapping[str, Any], spec: Mapping[str, Any]) -> dict[str, Any]:
    raw_params = spec.get("params")
    params = dict(raw_params) if isinstance(raw_params, Mapping) else {}
    switch_prop = to_str(spec.get("switch_prop"))
    if switch_prop is None:
        return params
    count = _channel_count(node, default=to_int(spec.get("channels")) or 1)
    for index in range(1, count + 1):
        params[f"{index}-{switch_prop}"] = False
    return params


def _subdevices_for_node(
    node: Mapping[str, Any],
    spec: Mapping[str, Any],
    category: str,
) -> list[dict[str, Any]]:
    switch_prop = to_str(spec.get("switch_prop"))
    if switch_prop is None:
        return []

    count = _channel_count(node, default=to_int(spec.get("channels")) or 1)
    cids = _cid_values(node.get("cids"))
    subdevices: list[dict[str, Any]] = []
    for index in range(1, count + 1):
        subdevices.append({
            "index": index,
            "cid": cids[index - 1] if index - 1 < len(cids) else None,
            "category": category,
            "name": None,
            "properties": [{"propId": switch_prop, "access": "read_write"}],
        })
    return subdevices


def _events_for_spec(spec: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [{"name": event} for event in spec.get("events", ()) if to_str(event)]


def _channel_count(node: Mapping[str, Any], *, default: int) -> int:
    count = to_int(node.get("ch_num")) or default
    return min(max(count, 1), 64)


def _cid_values(value: Any) -> list[int]:
    if not isinstance(value, list):
        return []
    return [cid for item in value if (cid := to_int(item)) is not None]


def _model_id(node: Mapping[str, Any], lan_type: int | None) -> str | None:
    pid = to_int(node.get("pid"))
    if pid is not None:
        return f"YL-{pid}"
    if lan_type is not None:
        return f"YL-LAN-{lan_type}"
    return None


def _auxiliary_nodes(nodes: list[Mapping[str, Any]], node_type: int) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for node in nodes:
        if to_int(node.get("nt")) != node_type:
            continue
        node_id = to_int(node.get("id"))
        if node_id is None:
            continue
        result.append({"id": node_id, "name": to_str(node.get("n")) or str(node_id)})
    return result


def _typed_auxiliary_nodes(
    nodes: list[Mapping[str, Any]],
    node_type: int,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for node in nodes:
        if to_int(node.get("nt")) != node_type:
            continue
        node_id = to_int(node.get("id"))
        if node_id is None:
            continue
        item: dict[str, Any] = {
            "id": node_id,
            "name": to_str(node.get("n")) or str(node_id),
            "type": to_int(node.get("type")),
            "node_type": node_type,
        }
        raw_online = node.get("o")
        if isinstance(raw_online, bool):
            item["online"] = raw_online
        elif raw_online is not None:
            item["online"] = to_bool(raw_online)
        params = node.get("params")
        if isinstance(params, Mapping):
            item["params"] = dict(params)
        result.append(item)
    return result


def _scene_nodes(nodes: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """返回带可选状态元数据的 LAN 情景行。"""
    result: list[dict[str, Any]] = []
    for node in nodes:
        if to_int(node.get("nt")) != NODE_TYPE_SCENE:
            continue
        node_id = to_int(node.get("id"))
        if node_id is None:
            continue
        item: dict[str, Any] = {
            "id": node_id,
            "name": to_str(node.get("n")) or str(node_id),
        }
        params = node.get("params")
        if isinstance(params, Mapping):
            item["params"] = dict(params)
            if state := to_str(params.get("state")):
                item["state"] = state
        result.append(item)
    return result
