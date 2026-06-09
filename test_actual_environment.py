#!/usr/bin/env python3
"""Yeelight Pro 集成 - 实际环境测试脚本."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from manual_ha_test_checks import (
    check_client_creation,
    check_config_flow,
    check_hacs_json,
    check_integration_import,
    check_manifest,
    check_projectors,
    check_utils,
)
from manual_ha_test_helpers import (
    run_named_tests,
)

BASE_DIR = Path(__file__).parent


async def test_integration_import() -> bool:
    """测试集成导入."""
    return await check_integration_import(path=BASE_DIR)


async def test_client_creation() -> bool:
    """测试客户端创建."""
    return await check_client_creation()


async def test_config_flow() -> bool:
    """测试配置流程."""
    return await check_config_flow()


async def test_projectors() -> bool:
    """测试投影层."""
    return await check_projectors()


async def test_utils() -> bool:
    """测试工具函数."""
    return await check_utils()


async def test_manifest() -> bool:
    """测试 manifest.json."""
    return await check_manifest(BASE_DIR)


async def test_hacs_json() -> bool:
    """测试 hacs.json."""
    return await check_hacs_json(BASE_DIR)


async def run_all_tests() -> bool:
    """运行所有测试."""
    return await run_named_tests(
        "🚀 Yeelight Pro 集成 - 实际环境测试",
        [
            ("集成导入", test_integration_import),
            ("客户端创建", test_client_creation),
            ("配置流程", test_config_flow),
            ("投影层", test_projectors),
            ("工具函数", test_utils),
            ("manifest.json", test_manifest),
            ("hacs.json", test_hacs_json),
        ],
        success_message="🎉 所有实际环境测试通过！\n\n✅ 本地检查通过；仍需完成发布审查后再提交 HACS",
    )


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
