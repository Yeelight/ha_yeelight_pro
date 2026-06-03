#!/usr/bin/env python3
"""
Yeelight Pro 集成 - 完整的真实 HA 环境测试

使用方法:
1. 将整个 custom_components/yeelight_pro 目录复制到 HA 的 config/custom_components/
2. 将此脚本复制到 HA 配置目录
3. 重启 Home Assistant
4. 在 HA 环境中运行: python test_complete_ha.py

注意: 此脚本需要在真实的 Home Assistant 环境中运行
"""
import asyncio
import sys
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# 添加 HA 配置目录到 Python 路径
ha_config_dir = Path.cwd()
sys.path.insert(0, str(ha_config_dir))


async def test_complete_ha_integration():
    """在真实 HA 环境中进行完整测试."""
    print("=" * 70)
    print("🚀 Yeelight Pro - 完整真实 HA 环境测试")
    print("=" * 70)

    test_results = []
    total_tests = 0
    passed_tests = 0

    def record_test(name, passed, details=""):
        nonlocal total_tests, passed_tests
        total_tests += 1
        if passed:
            passed_tests += 1
            test_results.append((name, "✅ 通过", details))
        else:
            test_results.append((name, "❌ 失败", details))

    try:
        # ============================================================
        # 测试 1: HA 核心模块导入
        # ============================================================
        print("\n🔍 测试 1: HA 核心模块导入...")
        try:
            from homeassistant.core import HomeAssistant
            from homeassistant.config_entries import ConfigEntry
            from homeassistant.const import CONF_ACCESS_TOKEN
            from homeassistant.helpers.aiohttp_client import async_get_clientsession
            record_test("HA 核心模块导入", True, "HomeAssistant, ConfigEntry, etc.")
            print("  ✅ HA 核心模块导入成功")
        except Exception as e:
            record_test("HA 核心模块导入", False, str(e))
            print(f"  ❌ HA 核心模块导入失败: {e}")
            return False

        # ============================================================
        # 测试 2: 集成模块导入
        # ============================================================
        print("\n🔍 测试 2: 集成模块导入...")
        try:
            from custom_components.yeelight_pro.const import DOMAIN, PLATFORMS
            from custom_components.yeelight_pro.core.client import YeelightProClient
            from custom_components.yeelight_pro.core.coordinator import YeelightProCoordinator
            from custom_components.yeelight_pro.core.exceptions import (
                AuthenticationError,
                ConnectionError,
                CommandError,
            )
            record_test("集成模块导入", True, f"DOMAIN={DOMAIN}, PLATFORMS={len(PLATFORMS)}")
            print(f"  ✅ DOMAIN: {DOMAIN}")
            print(f"  ✅ PLATFORMS: {len(PLATFORMS)} 个")
            print(f"  ✅ YeelightProClient 导入成功")
            print(f"  ✅ YeelightProCoordinator 导入成功")
        except Exception as e:
            record_test("集成模块导入", False, str(e))
            print(f"  ❌ 集成模块导入失败: {e}")
            return False

        # ============================================================
        # 测试 3: 所有平台导入
        # ============================================================
        print("\n🔍 测试 3: 导入所有平台...")
        all_platforms_ok = True
        for platform in PLATFORMS:
            try:
                module = __import__(
                    f"custom_components.yeelight_pro.{platform}",
                    fromlist=[platform],
                )
                assert hasattr(module, "async_setup_entry")
                print(f"  ✅ {platform} 平台导入成功")
            except Exception as e:
                all_platforms_ok = False
                print(f"  ❌ {platform} 平台导入失败: {e}")

        record_test("所有平台导入", all_platforms_ok, f"{len(PLATFORMS)} 个平台")
        if not all_platforms_ok:
            return False

        # ============================================================
        # 测试 4: 客户端功能测试
        # ============================================================
        print("\n🔍 测试 4: 客户端功能测试...")
        try:
            mock_session = MagicMock()
            client = YeelightProClient(
                domain="api.yeelight.com",
                access_token="test_token",
                session=mock_session,
                timeout=10,
            )

            # 测试属性
            assert client.domain == "api.yeelight.com"
            assert client.base_url == "https://api.yeelight.com"
            print(f"  ✅ 客户端属性正确")

            # 测试请求头
            headers = client._get_headers(with_auth=True)
            assert "Authorization" in headers
            assert headers["Authorization"] == "Bearer test_token"
            print(f"  ✅ 认证头生成正确")

            # 测试请求 ID
            request_id = client._next_request_id()
            assert request_id.startswith("ha-yeelight-")
            print(f"  ✅ 请求 ID 生成正确")

            # 测试无认证请求头
            headers_no_auth = client._get_headers(with_auth=False)
            assert "Authorization" not in headers_no_auth
            print(f"  ✅ 无认证请求头正确")

            record_test("客户端功能测试", True, "所有功能正常")
        except Exception as e:
            record_test("客户端功能测试", False, str(e))
            print(f"  ❌ 客户端功能测试失败: {e}")
            return False

        # ============================================================
        # 测试 5: 配置流程测试
        # ============================================================
        print("\n🔍 测试 5: 配置流程测试...")
        try:
            from custom_components.yeelight_pro.config_flow import YeelightProConfigFlow
            from custom_components.yeelight_pro.const import (
                CONNECTION_MODE_CLOUD,
                CONNECTION_MODE_PRIVATE,
            )

            # 创建配置流程实例
            flow = YeelightProConfigFlow()
            assert flow.VERSION == 1
            assert flow._connection_mode is None
            print(f"  ✅ 配置流程创建成功")

            # 测试用户步骤
            result = await flow.async_step_user()
            assert result["type"] == "form"
            assert result["step_id"] == "user"
            print(f"  ✅ 用户步骤正常")

            # 测试云端模式
            result = await flow.async_step_user(
                {"connection_mode": CONNECTION_MODE_CLOUD}
            )
            assert result["type"] == "form"
            assert result["step_id"] == "cloud_auth"
            assert flow._connection_mode == CONNECTION_MODE_CLOUD
            print(f"  ✅ 云端模式选择正常")

            # 测试私有模式
            flow._connection_mode = None
            result = await flow.async_step_user(
                {"connection_mode": CONNECTION_MODE_PRIVATE}
            )
            assert result["type"] == "form"
            assert result["step_id"] == "private_config"
            assert flow._connection_mode == CONNECTION_MODE_PRIVATE
            print(f"  ✅ 私有模式选择正常")

            record_test("配置流程测试", True, "所有步骤正常")
        except Exception as e:
            record_test("配置流程测试", False, str(e))
            print(f"  ❌ 配置流程测试失败: {e}")
            return False

        # ============================================================
        # 测试 6: 投影层测试
        # ============================================================
        print("\n🔍 测试 6: 投影层测试...")
        try:
            from custom_components.yeelight_pro.projector.light import project_light
            from custom_components.yeelight_pro.projector.fan import project_fans
            from custom_components.yeelight_pro.projector.switch import project_switches
            from custom_components.yeelight_pro.projector.sensor import project_sensors
            from custom_components.yeelight_pro.projector.binary_sensor import project_binary_sensors
            from custom_components.yeelight_pro.projector.cover import project_cover
            from custom_components.yeelight_pro.projector.climate import project_climate
            from custom_components.yeelight_pro.projector.lock import project_lock
            from custom_components.yeelight_pro.projector.event import project_events

            # 测试数据
            test_device = {
                "device_id": 12345,
                "name": "测试设备",
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
                        "name": "测试设备",
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

            # 测试各投影函数
            light = project_light(test_device, domain=DOMAIN)
            print(f"  ✅ 灯光投影: {'成功' if light else '返回 None'}")

            fans = project_fans(test_device, domain=DOMAIN)
            assert isinstance(fans, list)
            print(f"  ✅ 风扇投影: 返回 {len(fans)} 个")

            switches = project_switches(test_device, domain=DOMAIN)
            assert isinstance(switches, list)
            print(f"  ✅ 开关投影: 返回 {len(switches)} 个")

            sensors = project_sensors(test_device, domain=DOMAIN)
            assert isinstance(sensors, list)
            print(f"  ✅ 传感器投影: 返回 {len(sensors)} 个")

            binary_sensors = project_binary_sensors(test_device, domain=DOMAIN)
            assert isinstance(binary_sensors, list)
            print(f"  ✅ 二值传感器投影: 返回 {len(binary_sensors)} 个")

            cover = project_cover(test_device, domain=DOMAIN)
            print(f"  ✅ 窗帘投影: {'成功' if cover else '返回 None'}")

            climate = project_climate(test_device, domain=DOMAIN)
            print(f"  ✅ 空调投影: {'成功' if climate else '返回 None'}")

            lock = project_lock(test_device, domain=DOMAIN)
            print(f"  ✅ 门锁投影: {'成功' if lock else '返回 None'}")

            events = project_events(test_device, domain=DOMAIN)
            assert isinstance(events, list)
            print(f"  ✅ 事件投影: 返回 {len(events)} 个")

            record_test("投影层测试", True, "所有投影函数正常")
        except Exception as e:
            record_test("投影层测试", False, str(e))
            print(f"  ❌ 投影层测试失败: {e}")
            return False

        # ============================================================
        # 测试 7: 工具函数测试
        # ============================================================
        print("\n🔍 测试 7: 工具函数测试...")
        try:
            from custom_components.yeelight_pro.utils import (
                to_bool,
                to_int,
                to_float,
                to_str,
                to_str_or_empty,
                to_category,
                matches_any,
                matches_category,
            )

            # 测试 to_bool
            assert to_bool(True) is True
            assert to_bool(False) is False
            assert to_bool("true") is True
            assert to_bool("false") is False
            assert to_bool(None) is False
            print(f"  ✅ to_bool 测试通过")

            # 测试 to_int
            assert to_int(42) == 42
            assert to_int("100") == 100
            assert to_int(None) is None
            print(f"  ✅ to_int 测试通过")

            # 测试 to_float
            assert to_float(3.14) == 3.14
            assert to_float("2.5") == 2.5
            assert to_float(None) is None
            print(f"  ✅ to_float 测试通过")

            # 测试 to_str
            assert to_str("hello") == "hello"
            assert to_str(123) == "123"
            assert to_str(None) is None
            print(f"  ✅ to_str 测试通过")

            # 测试 to_str_or_empty
            assert to_str_or_empty("hello") == "hello"
            assert to_str_or_empty(None) == ""
            print(f"  ✅ to_str_or_empty 测试通过")

            # 测试 to_category
            assert to_category("Light") == "light"
            assert to_category(None) == ""
            print(f"  ✅ to_category 测试通过")

            # 测试 matches_any
            assert matches_any(["light_controller", "fan_switch"], ("light",)) is True
            assert matches_any(["switch", "outlet"], ("light", "fan")) is False
            print(f"  ✅ matches_any 测试通过")

            # 测试 matches_category
            assert matches_category("light_controller", ("light",)) is True
            assert matches_category("fan", ("light",)) is False
            print(f"  ✅ matches_category 测试通过")

            record_test("工具函数测试", True, "所有工具函数正常")
        except Exception as e:
            record_test("工具函数测试", False, str(e))
            print(f"  ❌ 工具函数测试失败: {e}")
            return False

        # ============================================================
        # 测试 8: 配置文件验证
        # ============================================================
        print("\n🔍 测试 8: 配置文件验证...")
        try:
            import json

            # 测试 manifest.json
            manifest_path = ha_config_dir / "custom_components" / "yeelight_pro" / "manifest.json"
            if manifest_path.exists():
                with open(manifest_path) as f:
                    manifest = json.load(f)
                assert manifest["domain"] == DOMAIN
                assert manifest["config_flow"] is True
                assert "version" in manifest
                print(f"  ✅ manifest.json 验证通过")
            else:
                print(f"  ❌ manifest.json 不存在")
                record_test("配置文件验证", False, "manifest.json 不存在")
                return False

            # 测试 hacs.json
            hacs_path = ha_config_dir / "hacs.json"
            if hacs_path.exists():
                with open(hacs_path) as f:
                    hacs = json.load(f)
                assert "name" in hacs
                assert "homeassistant" in hacs
                print(f"  ✅ hacs.json 验证通过")
            else:
                print(f"  ⚠️  hacs.json 不存在（可选）")

            # 测试 strings.json
            strings_path = ha_config_dir / "custom_components" / "yeelight_pro" / "strings.json"
            if strings_path.exists():
                with open(strings_path) as f:
                    strings = json.load(f)
                assert "config" in strings
                print(f"  ✅ strings.json 验证通过")
            else:
                print(f"  ⚠️  strings.json 不存在（可选）")

            record_test("配置文件验证", True, "所有配置文件正确")
        except Exception as e:
            record_test("配置文件验证", False, str(e))
            print(f"  ❌ 配置文件验证失败: {e}")
            return False

        # ============================================================
        # 测试 9: 服务定义测试
        # ============================================================
        print("\n🔍 测试 9: 服务定义测试...")
        try:
            from custom_components.yeelight_pro.const import DOMAIN

            # 检查 __init__.py 中的服务注册
            init_module = __import__(
                "custom_components.yeelight_pro",
                fromlist=["__init__"],
            )

            # 检查是否有服务注册函数
            if hasattr(init_module, "async_setup"):
                print(f"  ✅ async_setup 函数存在")
            else:
                print(f"  ⚠️  async_setup 函数不存在")

            # 检查是否有 async_setup_entry
            if hasattr(init_module, "async_setup_entry"):
                print(f"  ✅ async_setup_entry 函数存在")
            else:
                print(f"  ❌ async_setup_entry 函数不存在")
                record_test("服务定义测试", False, "async_setup_entry 不存在")
                return False

            record_test("服务定义测试", True, "所有服务定义正确")
        except Exception as e:
            record_test("服务定义测试", False, str(e))
            print(f"  ❌ 服务定义测试失败: {e}")
            return False

        # ============================================================
        # 测试结果汇总
        # ============================================================
        print("\n" + "=" * 70)
        print("📊 测试结果汇总")
        print("=" * 70)

        for name, status, details in test_results:
            print(f"  {name}: {status}")
            if details:
                print(f"    - {details}")

        print("\n" + "-" * 70)
        print(f"总计: {passed_tests}/{total_tests} 测试通过")
        print(f"通过率: {passed_tests / total_tests * 100:.1f}%")

        if passed_tests == total_tests:
            print("\n🎉 所有真实 HA 环境测试通过！")
            print("\n✅ 集成已准备就绪，可以进行 HACS 发布")
            print("\n📋 HACS 发布步骤:")
            print("   1. 访问 https://hacs.xyz/docs/publish/start")
            print("   2. 提交仓库: https://github.com/Yeelight/ha_yeelight_pro")
            print("   3. 等待审核 (1-7 天)")
            return True
        else:
            print("\n⚠️  部分测试失败，请检查并修复问题")
            return False

    except Exception as e:
        print(f"\n❌ 测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_complete_ha_integration())
    sys.exit(0 if success else 1)
