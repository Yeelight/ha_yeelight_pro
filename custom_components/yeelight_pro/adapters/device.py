"""Adapters that normalize Yeelight Pro LAN runtime payloads into source contracts."""

from __future__ import annotations

from collections import defaultdict
import re
from typing import Any, Mapping

from ..canonical.models import HAProductModel
from .models import (
    SourceDeviceComponentInput,
    SourceDeviceInfoInput,
    SourceDeviceInstanceInput,
)
from ..utils import to_bool, to_str

# 运行时排除的组件类型
RUNTIME_EXCLUDED_COMPONENT_TYPES = {"global"}
# 运行时排除的属性种类
RUNTIME_EXCLUDED_KINDS = {"config", "diagnostic", "info"}
# 运行时排除的属性类型
RUNTIME_EXCLUDED_PROPERTY_TYPES = {"config"}
# 回退模式下按设备类型映射的运行时 key 集合
FALLBACK_RUNTIME_KEYS: dict[str, set[str]] = {
    "light": {"p", "sp", "l", "ct", "c", "m"},
    "fan": {"p", "lv", "dir", "m"},
    "switch": {"p", "sp", "on"},
    "outlet": {"p", "sp", "on"},
    "binary_sensor": {"mv", "dc", "alm"},
    "sensor": {"t", "h", "luminance", "level"},
    "cover": {"cp", "tp"},
    "climate": {"acm", "actt", "acct", "acf", "aco"},
    "lock": {"lock", "locked", "lck"},
}
# 索引运行时 key 正则：匹配 "0-p", "1-ct" 等格式
INDEXED_RUNTIME_KEY_RE = re.compile(r"^\d+-(.+)$")
# 无状态执行器类别 token，用于判断是否应暴露无状态组件
STATELESS_ACTUATOR_CATEGORY_TOKENS = (
    "light",
    "lamp",
    "灯",
    "灯带",
    "彩光",
    "色温",
    "switch",
    "relay",
    "outlet",
    "fan",
    "ceiling fan",
    "开关",
    "面板",
    "风扇",
    "吊扇",
    "cover",
    "curtain",
    "blind",
    "窗帘",
    "lock",
    "door lock",
    "门锁",
    "climate",
    "air",
    "heater",
    "bath",
    "空调",
    "浴霸",
)


class YeelightLanDeviceAdapter:
    """Normalize Yeelight LAN topology and device snapshots into source contracts."""

    def adapt(
        self,
        payload: Mapping[str, Any],
        *,
        product_model: HAProductModel | None = None,
        model_id: str | None = None,
        device_info: Mapping[str, Any] | None = None,
    ) -> SourceDeviceInstanceInput:
        """Adapt a runtime payload into a normalized device-instance contract."""
        device_id = to_str(
            payload.get("device_id", payload.get("deviceId", payload.get("id")))
        )
        name = to_str(payload.get("name", payload.get("n")))
        online = to_bool(payload.get("online", payload.get("o")), default=True)
        params = payload.get("params") if isinstance(payload.get("params"), Mapping) else {}

        resolved_model_id = model_id
        if not resolved_model_id and product_model is not None:
            resolved_model_id = product_model.product.model_id
        if not resolved_model_id and payload.get("model_id") is not None:
            resolved_model_id = to_str(payload.get("model_id"))

        product_key = to_str(
            payload.get("product_key", payload.get("pid", payload.get("product_type")))
        )

        return SourceDeviceInstanceInput(
            source="yeelight",
            device_id=device_id,
            product_key=product_key,
            model_id=resolved_model_id,
            name=name,
            online=online,
            device_info=self._adapt_device_info(device_info, payload, resolved_model_id, name),
            components=self._adapt_components(
                payload,
                params=params,
                online=online,
                product_model=product_model,
            ),
            extensions=self._build_extensions(payload),
        )

    def _adapt_device_info(
        self,
        device_info: Mapping[str, Any] | None,
        payload: Mapping[str, Any],
        model_id: str | None,
        name: str | None,
    ) -> SourceDeviceInfoInput | None:
        """适配设备信息，优先使用显式 device_info，回退到 payload 推断。"""
        if device_info:
            return SourceDeviceInfoInput(
                identifiers=self._normalize_pair_list(device_info.get("identifiers")),
                connections=self._normalize_pair_list(device_info.get("connections")),
                via_device=self._normalize_pair(device_info.get("via_device")),
                manufacturer=to_str(device_info.get("manufacturer")),
                model=to_str(device_info.get("model")),
                model_id=to_str(device_info.get("model_id")) or model_id,
                name=to_str(device_info.get("name")) or name,
                serial_number=to_str(device_info.get("serial_number")),
                sw_version=to_str(device_info.get("sw_version")),
                hw_version=to_str(device_info.get("hw_version")),
                configuration_url=to_str(device_info.get("configuration_url")),
                entry_type=to_str(device_info.get("entry_type")),
                suggested_area=to_str(device_info.get("suggested_area")),
                default_manufacturer=to_str(device_info.get("default_manufacturer")),
                default_model=to_str(device_info.get("default_model")),
                default_name=to_str(device_info.get("default_name")),
                translation_key=to_str(device_info.get("translation_key")),
                translation_placeholders=(
                    dict(device_info.get("translation_placeholders"))
                    if isinstance(device_info.get("translation_placeholders"), Mapping)
                    else None
                ),
            )

        # 从 payload 推断设备信息
        identifiers = []
        device_id = to_str(payload.get("device_id", payload.get("id")))
        if device_id:
            identifiers.append(["yeelight_pro", f"device:{device_id}"])

        mac = to_str(payload.get("mac"))
        connections = [["mac", mac]] if mac else []

        if not identifiers and not connections and not model_id and not name:
            return None

        return SourceDeviceInfoInput(
            identifiers=identifiers,
            connections=connections,
            manufacturer="Yeelight" if model_id else None,
            model_id=model_id,
            name=name,
        )

    def _adapt_components(
        self,
        payload: Mapping[str, Any],
        *,
        params: Mapping[str, Any],
        online: bool,
        product_model: HAProductModel | None,
    ) -> list[SourceDeviceComponentInput]:
        """适配设备组件列表，有产品模型时精确映射，否则回退。"""
        if product_model is None:
            return [
                SourceDeviceComponentInput(
                    component_key=self._fallback_component_key(payload),
                    category=to_str(payload.get("category")),
                    available=online,
                    state=self._fallback_runtime_state(payload, params),
                )
            ]

        state_map = {component.component_id: {} for component in product_model.components}
        indexed_lookup: dict[str, tuple[str, str]] = {}
        plain_lookup: dict[str, list[str]] = defaultdict(list)

        component_by_id = {component.component_id: component for component in product_model.components}
        for component in product_model.components:
            if not self._should_expose_component_state(component):
                continue
            for prop in component.properties:
                if not self._should_expose_runtime_property(component, prop):
                    continue
                plain_lookup[prop.prop_id].append(component.component_id)
                if component.index is not None:
                    indexed_lookup[f"{component.index}-{prop.prop_id}"] = (
                        component.component_id,
                        prop.prop_id,
                    )

        # 将运行时 params 映射到组件 state
        for raw_key, value in params.items():
            if raw_key in indexed_lookup:
                component_id, prop_id = indexed_lookup[raw_key]
                state_map[component_id][prop_id] = value
                continue

            candidates = plain_lookup.get(raw_key, [])
            if len(candidates) == 1:
                state_map[candidates[0]][raw_key] = value
                continue

            if len(candidates) > 1:
                preferred = self._prefer_plain_match(candidates, component_by_id, raw_key)
                if preferred:
                    state_map[preferred][raw_key] = value

        components: list[SourceDeviceComponentInput] = []
        for component in product_model.components:
            if not self._should_expose_component_state(component):
                continue
            component_state = state_map.get(component.component_id, {})
            if not self._should_include_runtime_component(component, component_state):
                continue
            components.append(
                SourceDeviceComponentInput(
                    component_key=component.component_id,
                    component_type=component.component_type,
                    category=component.category,
                    available=online,
                    state=component_state,
                )
            )

        return components

    def _should_include_runtime_component(
        self,
        component: Any,
        component_state: Mapping[str, Any],
    ) -> bool:
        """判断是否应暴露该运行时组件（有状态、有事件、或是无状态执行器）。"""
        if component_state:
            return True
        if bool(getattr(component, "events", None)):
            return True
        return self._looks_like_stateless_actuator_component(component)

    def _build_extensions(
        self,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        """构建设备扩展元数据（当前为空，预留扩展点）。"""
        return {}

    def _fallback_runtime_state(
        self,
        payload: Mapping[str, Any],
        params: Mapping[str, Any],
    ) -> dict[str, Any]:
        """无产品模型时的回退状态提取逻辑。"""
        source_type = to_str(payload.get("type"))
        allowed = FALLBACK_RUNTIME_KEYS.get(source_type or "", set())
        if not allowed:
            return {}

        state: dict[str, Any] = {}
        for raw_key, value in params.items():
            key = to_str(raw_key)
            if not key:
                continue
            if key in allowed or self._matches_indexed_runtime_key(key, allowed):
                state[key] = value
        return state

    def _matches_indexed_runtime_key(self, raw_key: str, allowed: set[str]) -> bool:
        """检查索引格式 key（如 '0-p'）是否匹配允许集合。"""
        matched = INDEXED_RUNTIME_KEY_RE.match(raw_key)
        if matched is None:
            return False
        return matched.group(1) in allowed

    def _should_expose_component_state(self, component: Any) -> bool:
        """判断组件是否应暴露运行时状态。"""
        component_type = to_str(getattr(component, "component_type", None))
        if component_type in RUNTIME_EXCLUDED_COMPONENT_TYPES:
            return False
        return True

    def _should_expose_runtime_property(self, component: Any, prop: Any) -> bool:
        """判断属性是否应暴露到运行时状态。"""
        if not self._should_expose_component_state(component):
            return False

        kind = to_str(getattr(prop, "kind", None))
        if kind in RUNTIME_EXCLUDED_KINDS:
            return False

        property_type = to_str(getattr(prop, "property_type", None))
        if property_type in RUNTIME_EXCLUDED_PROPERTY_TYPES:
            return False

        return True

    def _prefer_plain_match(
        self,
        candidates: list[str],
        component_by_id: Mapping[str, Any],
        raw_key: str,
    ) -> str | None:
        """多候选时优先匹配 global 组件的特定 key。"""
        global_candidates = [
            component_id
            for component_id in candidates
            if getattr(component_by_id.get(component_id), "component_type", None) == "global"
        ]
        if raw_key in {"fv", "name", "icon", "o"} and len(global_candidates) == 1:
            return global_candidates[0]
        return None

    def _looks_like_stateless_actuator_component(self, component: Any) -> bool:
        """根据类别或组件 ID 判断是否为无状态执行器。"""
        category = (to_str(getattr(component, "category", None)) or "").lower()
        component_id = (to_str(getattr(component, "component_id", None)) or "").lower()
        haystacks = (category, component_id)
        return any(token in haystack for haystack in haystacks for token in STATELESS_ACTUATOR_CATEGORY_TOKENS)

    def _normalize_pair_list(self, value: Any) -> list[list[str]]:
        """规范化二元组列表（如 identifiers、connections）。"""
        pairs: list[list[str]] = []
        for item in value or []:
            normalized = self._normalize_pair(item)
            if normalized:
                pairs.append(normalized)
        return pairs

    def _normalize_pair(self, value: Any) -> list[str] | None:
        """规范化单个二元组。"""
        if isinstance(value, (list, tuple)) and len(value) == 2:
            return [str(value[0]), str(value[1])]
        return None

    def _fallback_component_key(self, payload: Mapping[str, Any]) -> str:
        """无产品模型时的回退组件 key 提取。"""
        device_type = to_str(payload.get("type"))
        if device_type:
            return device_type
        return "main"
