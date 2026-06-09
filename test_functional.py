#!/usr/bin/env python3
"""Yeelight Pro 集成本地功能测试脚本."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from manual_ha_test_helpers import (
    add_python_path,
    run_named_tests,
)
from manual_ha_test_checks import (
    check_canonical_models,
    check_client_creation,
    check_config_flow,
    check_platform_entities,
    check_projectors,
    check_services,
    check_utils,
)

PROJECT_ROOT = Path(__file__).parent
add_python_path(PROJECT_ROOT)


async def test_client_api() -> bool:
    """测试客户端 API."""
    return await check_client_creation()


async def test_canonical_models() -> bool:
    """测试规范模型."""
    return await check_canonical_models()


async def test_projector() -> bool:
    """测试投影层."""
    return await check_projectors()


async def test_utils() -> bool:
    """测试工具函数."""
    return await check_utils()


async def test_config_flow() -> bool:
    """测试配置流程."""
    return await check_config_flow()


async def test_platform_entities() -> bool:
    """测试平台实体."""
    return await check_platform_entities()


async def test_services() -> bool:
    """测试服务定义."""
    return await check_services()


async def run_all_tests() -> bool:
    """运行所有测试."""
    return await run_named_tests(
        "🚀 Yeelight Pro 集成功能测试",
        [
            ("客户端 API", test_client_api),
            ("规范模型", test_canonical_models),
            ("投影层", test_projector),
            ("工具函数", test_utils),
            ("配置流程", test_config_flow),
            ("平台实体", test_platform_entities),
            ("服务定义", test_services),
        ],
        success_message="🎉 所有功能测试通过！\n\n✅ 功能脚本通过；仍需完成本地 HA 验证和发布审查",
    )


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
