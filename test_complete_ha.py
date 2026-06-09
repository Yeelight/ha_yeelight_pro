#!/usr/bin/env python3
"""Yeelight Pro 集成 - 完整真实 HA 环境测试."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from manual_ha_test_checks import (
    check_client_creation,
    check_config_files,
    check_config_flow,
    check_ha_core_import,
    check_integration_import,
    check_projectors,
    check_services,
    check_utils,
)
from manual_ha_test_helpers import (
    add_python_path,
    print_banner,
    print_exception,
    print_summary,
)

HA_CONFIG_DIR = Path.cwd()
add_python_path(HA_CONFIG_DIR)


async def test_complete_ha_integration() -> bool:
    """在真实 HA 环境中进行完整测试."""
    print_banner("🚀 Yeelight Pro - 完整真实 HA 环境测试", width=70)
    results: list[tuple[str, bool]] = []
    try:
        tests = [
            ("HA 核心模块导入", check_ha_core_import),
            ("集成模块导入", lambda: check_integration_import(path=HA_CONFIG_DIR)),
            ("客户端功能测试", lambda: check_client_creation(timeout=10, check_no_auth=True)),
            ("配置流程测试", check_config_flow),
            (
                "投影层测试",
                lambda: check_projectors(
                    domain="yeelight_pro",
                    include_all=True,
                    device_name="测试设备",
                ),
            ),
            ("工具函数测试", lambda: check_utils(include_to_str_or_empty=True)),
            ("配置文件验证", lambda: check_config_files(HA_CONFIG_DIR)),
            ("服务定义测试", lambda: check_services(require_setup_entry=True)),
        ]
        for name, test_func in tests:
            result = await test_func()
            results.append((name, result))
            if not result:
                return False
    except Exception as err:
        print_exception("测试过程中发生异常", err)
        return False

    return print_summary(
        results,
        width=70,
        success_message="🎉 所有真实 HA 环境测试通过！\n\n✅ 本地 HA 检查通过；仍需完成发布审查后再提交 HACS",
        failure_message="⚠️  部分测试失败，请检查并修复问题",
    )


if __name__ == "__main__":
    success = asyncio.run(test_complete_ha_integration())
    sys.exit(0 if success else 1)
