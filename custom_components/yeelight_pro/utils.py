"""Yeelight Pro 工具函数库.

提供类型转换、布尔解析、字符串匹配等通用工具函数，
统一 lucore_gateway 中分散的重复实现。
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# 布尔值解析
# ---------------------------------------------------------------------------

# 字符串真值集合
_TRUTHY_STRINGS = frozenset({"true", "1", "yes", "on"})
_FALSY_STRINGS = frozenset({"false", "0", "no", "off"})


def to_bool(value: Any, *, default: bool = False) -> bool:
    """将任意值转换为布尔值.

    支持字符串智能解析（true/false/yes/no/on/off/1/0），
    None 返回 default。

    Args:
        value: 待转换的值
        default: 当 value 为 None 时返回的默认值

    Returns:
        转换后的布尔值
    """
    if value is None:
        return default
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in _TRUTHY_STRINGS:
            return True
        if lowered in _FALSY_STRINGS:
            return False
    return bool(value)


# ---------------------------------------------------------------------------
# 整数转换
# ---------------------------------------------------------------------------


def to_int(value: Any) -> int | None:
    """将任意值转换为整数.

    None 或空字符串返回 None，转换失败返回 None。

    Args:
        value: 待转换的值

    Returns:
        转换后的整数，或 None
    """
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# 浮点数转换
# ---------------------------------------------------------------------------


def to_float(value: Any) -> float | None:
    """将任意值转换为浮点数.

    None 或空字符串返回 None，转换失败返回 None。

    Args:
        value: 待转换的值

    Returns:
        转换后的浮点数，或 None
    """
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# 字符串转换
# ---------------------------------------------------------------------------


def to_str(value: Any) -> str | None:
    """将任意值转换为字符串，去除首尾空白.

    None 返回 None，空字符串返回 None。

    Args:
        value: 待转换的值

    Returns:
        转换后的字符串，或 None
    """
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def to_str_or_empty(value: Any) -> str:
    """将任意值转换为字符串，去除首尾空白.

    None 返回空字符串，空字符串返回空字符串。

    Args:
        value: 待转换的值

    Returns:
        转换后的字符串（永不为 None）
    """
    if value is None:
        return ""
    return str(value).strip()


# ---------------------------------------------------------------------------
# 类别判断
# ---------------------------------------------------------------------------


def to_category(value: Any) -> str:
    """将任意值转换为小写类别字符串.

    None 或空值返回空字符串。

    Args:
        value: 待转换的值

    Returns:
        小写类别字符串
    """
    text = to_str(value)
    return text.lower() if text else ""


# ---------------------------------------------------------------------------
# 匹配判断
# ---------------------------------------------------------------------------


def matches_any(values: list[str], tokens: tuple[str, ...]) -> bool:
    """判断 values 中是否有任何元素包含 tokens 中的任意一个 token.

    Args:
        values: 待检查的字符串列表
        tokens: 匹配 token 元组

    Returns:
        是否存在匹配
    """
    return any(token in value for value in values for token in tokens)


def matches_category(category: str, tokens: tuple[str, ...]) -> bool:
    """判断类别字符串是否包含 tokens 中的任意一个 token.

    Args:
        category: 类别字符串
        tokens: 匹配 token 元组

    Returns:
        是否存在匹配
    """
    return any(token in category for token in tokens)
