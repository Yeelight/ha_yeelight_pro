"""Shared helpers for Yeelight Pro projector modules."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping

from ..canonical.models import ComponentModel, HADeviceInstanceModel, HAProductModel
from ..utils import to_int

COMPONENT_INDEX_RE = re.compile(r"_(?P<index>\d+)$")


@dataclass(slots=True)
class NumericRange:
    """归一化的数值范围元数据。"""

    min: int | None = None
    max: int | None = None
    step: int | None = None


def load_instance(device_payload: Mapping[str, Any]) -> HADeviceInstanceModel | None:
    """从载荷中加载设备实例模型。"""
    payload = device_payload.get("ha_device_instance")
    if not isinstance(payload, Mapping):
        return None
    return HADeviceInstanceModel.from_dict(payload)


def load_product_model(device_payload: Mapping[str, Any]) -> HAProductModel | None:
    """从载荷中加载产品模型。"""
    payload = device_payload.get("ha_product_model")
    if not isinstance(payload, Mapping):
        return None
    return HAProductModel.from_dict(payload)


def product_component(
    product_model: HAProductModel | None,
    component_id: str,
) -> ComponentModel | None:
    """从产品模型中查找匹配的组件定义。"""
    if product_model is None:
        return None
    return next(
        (item for item in product_model.components if item.component_id == component_id),
        None,
    )


def component_index(component_id: str) -> int | None:
    """从组件 ID 中提取数字索引。"""
    match = COMPONENT_INDEX_RE.search(component_id)
    if not match:
        return None
    return to_int(match.group("index"))


def humanize_component_id(component_id: str) -> str | None:
    """将组件 ID 转换为人类可读名称。"""
    text = component_id.replace("_", " ").strip()
    return text or None
