# utils.py 迁移指南

## 概述

`utils.py` 统一了 `lucore_gateway` 中分散在 15+ 个文件中的重复工具函数。

## 函数映射表

| 旧函数名 | 新函数名 | 签名变化 | 说明 |
|---------|---------|---------|------|
| `_bool(value, default=False)` | `to_bool(value, *, default=False)` | `default` 变为 keyword-only | 字符串智能解析 |
| `_bool(value, *, default)` | `to_bool(value, *, default=False)` | 添加默认值 | 兼容现有调用 |
| `_int(value)` | `to_int(value)` | 无 | - |
| `_float(value)` | `to_float(value)` | 无 | - |
| `_string(value) -> str\|None` | `to_str(value)` | 无 | 返回 Optional |
| `_string(value) -> str` | `to_str_or_empty(value)` | 无 | 返回非 None |
| `_category(value)` | `to_category(value)` | 无 | - |
| `_matches_any(values, tokens)` | `matches_any(values, tokens)` | 无 | - |
| `_matches_category(category, tokens)` | `matches_category(category, tokens)` | 无 | - |

## 迁移示例

### Before (projector/light.py)
```python
def _bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    return bool(value)

def _int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
```

### After
```python
from yeelight_pro.utils import to_bool, to_int
```

## 兼容性说明

### `_bool` 签名变化

旧代码中有两种调用方式：
1. 位置参数: `_bool(value, True)` → **需要改为**: `to_bool(value, default=True)`
2. 关键字参数: `_bool(value, default=True)` → 无需修改

### `_string` 返回类型差异

- `_string() -> str | None`: 使用 `to_str()`
- `_string() -> str`: 使用 `to_str_or_empty()`

## 函数特性

### `to_bool` - 智能布尔解析

支持以下字符串真值（不区分大小写）：
- 真值: `"true"`, `"1"`, `"yes"`, `"on"`
- 假值: `"false"`, `"0"`, `"no"`, `"off"`

### `to_int` / `to_float` - 宽松转换

- `None` → `None`
- `""` → `None`
- 转换失败 → `None`

### `to_str` - 可选字符串

- `None` → `None`
- `""` → `None`
- `"  "` → `None`
- `"abc"` → `"abc"`
- `123` → `"123"`

### `to_str_or_empty` - 非空字符串

- `None` → `""`
- `""` → `""`
- `"  "` → `""`
- `"abc"` → `"abc"`

## 使用建议

1. **新代码**: 直接使用 `to_*` 前缀函数
2. **迁移旧代码**: 按映射表替换，注意 `_bool` 的 keyword-only 参数
3. **局部函数**: 如果某文件需要特殊行为，保留局部实现
