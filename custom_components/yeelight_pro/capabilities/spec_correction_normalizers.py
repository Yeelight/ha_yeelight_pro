"""Yeelight IoT schema normalizers used by conservative correction rules."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

WRITE_OPERATORS = frozenset({"set", "toggle", "adjust"})
VALID_ACCESS_VALUES = frozenset({"read_only", "read_write"})
ACCESS_WRITE_BIT = 0b10


def normalize_property_format(value: Any) -> str | None:
    """规范化 Yeelight 属性格式."""
    text = text_value(value)
    if text is None:
        return None
    lowered = text.lower()
    if lowered == "bool":
        return "boolean"
    return lowered


def normalize_property_access(raw_access: Any, operators: Any) -> str:
    """规范化属性访问级别，合法内部值优先保留."""
    access = text_value(raw_access)
    if access is not None and access.lower() in VALID_ACCESS_VALUES:
        return access.lower()
    if access_text_has_write(access):
        return "read_write"
    if access_text_is_read_only(access):
        return "read_only"
    numeric_access = int_value(raw_access)
    if numeric_access is not None:
        return "read_write" if numeric_access & ACCESS_WRITE_BIT else "read_only"
    return "read_write" if has_write_operator(operators) else "read_only"


def normalize_property_operators(operators: Any) -> list[str]:
    """规范化 Yeelight operators 列表，保留顺序并去重."""
    normalized: list[str] = []
    for item in iter_operator_items(operators):
        operator = operator_text(item)
        if operator is None or operator not in WRITE_OPERATORS:
            continue
        if operator not in normalized:
            normalized.append(operator)
    return normalized


def normalize_property_type(value: str | None) -> str | None:
    """规范化属性类型标识."""
    text = text_value(value)
    if text in {"apply", "application", "应用类"}:
        return "apply"
    if text in {"config", "配置类"}:
        return "config"
    return None


def normalize_source_property_type(value: Any) -> str | None:
    """将 Yeelight 原始属性类型数值映射为标识."""
    numeric_value = int_value(value)
    if numeric_value == 0:
        return "apply"
    if numeric_value == 1:
        return "config"
    return normalize_property_type(text_value(value))


def normalize_component_type(value: Any) -> str | None:
    """将 Yeelight 组件类型数值映射为标识."""
    numeric_value = int_value(value)
    if numeric_value == 0:
        return "custom"
    if numeric_value == 1:
        return "global"
    return text_value(value)


def has_write_operator(operators: Any) -> bool:
    """判断 operators 是否包含写操作."""
    return bool(normalize_property_operators(operators))


def iter_operator_items(operators: Any) -> Iterable[Any]:
    """遍历 operators 的兼容形态."""
    if operators is None:
        return ()
    if isinstance(operators, str):
        return (
            item.strip()
            for item in operators.replace("/", ",").replace("|", ",").split(",")
        )
    if isinstance(operators, Mapping):
        return operators.values()
    if isinstance(operators, Iterable):
        return operators
    return (operators,)


def operator_text(value: Any) -> str | None:
    """返回 operators 项中的操作文本."""
    if isinstance(value, Mapping):
        for key in ("name", "operator", "op", "code", "value"):
            text = text_value(value.get(key))
            if text is not None:
                return text.lower()
        return None
    text = text_value(value)
    return text.lower() if text is not None else None


def access_text_has_write(value: str | None) -> bool:
    """判断文本权限是否包含写能力."""
    if value is None:
        return False
    lowered = value.lower()
    collapsed = (
        lowered.replace(" ", "")
        .replace("_", "")
        .replace("-", "")
        .replace("/", "")
        .replace(",", "")
    )
    return collapsed in {"rw", "readwrite"} or (
        ("read" in collapsed and "write" in collapsed) or ("读" in value and "写" in value)
    )


def access_text_is_read_only(value: str | None) -> bool:
    """判断文本权限是否明确只读."""
    if value is None:
        return False
    lowered = value.lower()
    return lowered in {"read", "read_only", "readonly", "ro", "r", "读"}


def int_value(value: Any) -> int | None:
    """返回整数值；布尔值不参与数值权限推断."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    text = text_value(value)
    if text is None:
        return None
    try:
        return int(text, 10)
    except ValueError:
        return None


def text_value(value: Any) -> str | None:
    """返回去空白文本或 None."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


__all__ = [
    "normalize_component_type",
    "normalize_property_access",
    "normalize_property_format",
    "normalize_property_operators",
    "normalize_property_type",
    "normalize_source_property_type",
    "text_value",
]
