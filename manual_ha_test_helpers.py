#!/usr/bin/env python3
"""Shared helpers for root-level manual Home Assistant validation scripts."""
from __future__ import annotations

import sys
import traceback
from collections.abc import Awaitable, Callable
from pathlib import Path

ManualTest = tuple[str, Callable[[], Awaitable[bool]]]
ManualResult = tuple[str, bool]


def add_python_path(path: Path) -> None:
    """将测试目标目录加入 Python import path，避免重复插入。"""
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)


def print_banner(title: str, *, width: int = 60) -> None:
    """打印手工验证脚本标题。"""
    print("=" * width)
    print(title)
    print("=" * width)


def print_exception(prefix: str, err: Exception) -> None:
    """打印异常类型和堆栈，供手工脚本定位环境问题。"""
    print(f"  ❌ {prefix}: {err}")
    traceback.print_exc()


def sample_light_device(*, name: str = "客厅灯") -> dict[str, object]:
    """返回稳定的灯设备样例，供 root-level smoke 脚本复用。"""
    return {
        "device_id": 12345,
        "name": name,
        "model_id": "YLCT01",
        "online": True,
        "params": {
            "power": "on",
            "brightness": 80,
            "color_temperature": 4000,
        },
        "ha_device_instance": {
            "device_info": {
                "identifiers": [["yeelight_pro", "12345"]],
                "name": name,
            },
            "component_instances": {
                "light": {
                    "available": True,
                    "params": {
                        "power": "on",
                        "brightness": 80,
                        "color_temperature": 4000,
                    },
                },
            },
        },
    }


async def run_named_tests(
    title: str,
    tests: list[ManualTest],
    *,
    width: int = 60,
    success_message: str,
    failure_message: str = "⚠️  部分测试失败，请检查并修复问题",
) -> bool:
    """按顺序运行手工测试函数并打印汇总。"""
    print_banner(title, width=width)
    results: list[ManualResult] = []
    for test_name, test_func in tests:
        try:
            results.append((test_name, await test_func()))
        except Exception as err:  # pragma: no cover - manual script safety net
            print(f"\n❌ {test_name} 测试异常: {err}")
            results.append((test_name, False))
    return print_summary(
        results,
        width=width,
        success_message=success_message,
        failure_message=failure_message,
    )


def print_summary(
    results: list[ManualResult],
    *,
    width: int,
    success_message: str,
    failure_message: str,
) -> bool:
    """打印测试结果汇总并返回是否全部通过。"""
    print("\n" + "=" * width)
    print("📊 测试结果汇总")
    print("=" * width)

    passed = sum(1 for _, result in results if result)
    total = len(results)
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")

    print("\n" + "-" * width)
    print(f"总计: {passed}/{total} 测试通过")
    print(f"通过率: {passed / total * 100:.1f}%")

    if passed == total:
        print(f"\n{success_message}")
        return True
    print(f"\n{failure_message}")
    return False
