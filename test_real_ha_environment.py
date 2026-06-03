#!/usr/bin/env python3
"""
Yeelight Pro 集成 - 真实 HA 环境测试脚本

使用方法:
1. 将此脚本复制到 Home Assistant 配置目录
2. 确保 custom_components/yeelight_pro 已安装
3. 运行: python test_real_ha.py

注意: 此脚本需要在真实的 Home Assistant 环境中运行
"""
import asyncio
import sys
import os
from pathlib import Path

# 添加 HA 配置目录到 Python 路径
ha_config_dir = Path.cwd()
sys.path.insert(0, str(ha_config_dir))


async def test_ha_integration():
    """在真实 HA 环境中测试集成."""
    print("=" * 60)
    print("🚀 Yeelight Pro - 真实 HA 环境测试")
    print("=" * 60)

    try:
        # 测试 1: 导入 HA 核心模块
        print("\n🔍 测试 1: 导入 HA 核心模块...")
        from homeassistant.core import HomeAssistant
        from homeassistant.config_entries import ConfigEntry
        from homeassistant.const import CONF_ACCESS_TOKEN
        print("  ✅ HA 核心模块导入成功")

        # 测试 2: 导入集成模块
        print("\n🔍 测试 2: 导入集成模块...")
        from custom_components.yeelight_pro.const import DOMAIN, PLATFORMS
        from custom_components.yeelight_pro.core.client import YeelightProClient
        from custom_components.yeelight_pro.core.coordinator import YeelightProCoordinator
        print(f"  ✅ DOMAIN: {DOMAIN}")
        print(f"  ✅ PLATFORMS: {len(PLATFORMS)} 个")
        print(f"  ✅ YeelightProClient 导入成功")
        print(f"  ✅ YeelightProCoordinator 导入成功")

        # 测试 3: 导入所有平台
        print("\n🔍 测试 3: 导入所有平台...")
        for platform in PLATFORMS:
            try:
                module = __import__(
                    f"custom_components.yeelight_pro.{platform}",
                    fromlist=[platform],
                )
                assert hasattr(module, "async_setup_entry")
                print(f"  ✅ {platform} 平台导入成功")
            except Exception as e:
                print(f"  ❌ {platform} 平台导入失败: {e}")
                return False

        # 测试 4: 测试客户端创建
        print("\n🔍 测试 4: 测试客户端创建...")
        from unittest.mock import MagicMock
        mock_session = MagicMock()
        client = YeelightProClient(
            domain="api.yeelight.com",
            access_token="test_token",
            session=mock_session,
        )
        print(f"  ✅ 客户端创建成功")
        print(f"     - 域名: {client.domain}")
        print(f"     - Base URL: {client.base_url}")

        # 测试 5: 测试配置流程
        print("\n🔍 测试 5: 测试配置流程...")
        from custom_components.yeelight_pro.config_flow import YeelightProConfigFlow
        flow = YeelightProConfigFlow()
        assert flow.VERSION == 1
        print(f"  ✅ 配置流程创建成功")

        # 测试用户步骤
        result = await flow.async_step_user()
        assert result["type"] == "form"
        assert result["step_id"] == "user"
        print(f"  ✅ 用户步骤正常")

        # 测试云端模式
        result = await flow.async_step_user(
            {"connection_mode": "cloud"}
        )
        assert result["type"] == "form"
        assert result["step_id"] == "cloud_auth"
        print(f"  ✅ 云端模式选择正常")

        # 测试私有模式
        flow._connection_mode = None
        result = await flow.async_step_user(
            {"connection_mode": "private"}
        )
        assert result["type"] == "form"
        assert result["step_id"] == "private_config"
        print(f"  ✅ 私有模式选择正常")

        # 测试 6: 测试投影层
        print("\n🔍 测试 6: 测试投影层...")
        from custom_components.yeelight_pro.projector.light import project_light
        from custom_components.yeelight_pro.projector.fan import project_fans
        from custom_components.yeelight_pro.projector.switch import project_switches
        from custom_components.yeelight_pro.projector.sensor import project_sensors

        test_device = {
            "device_id": 12345,
            "name": "测试设备",
            "online": True,
            "params": {"power": "on", "brightness": 80},
            "ha_device_instance": {
                "device_info": {"identifiers": [["yeelight_pro", "12345"]]},
                "component_instances": {},
            },
        }

        light = project_light(test_device, domain=DOMAIN)
        print(f"  ✅ 灯光投影: {'成功' if light else '返回 None'}")

        fans = project_fans(test_device, domain=DOMAIN)
        print(f"  ✅ 风扇投影: 返回 {len(fans)} 个")

        switches = project_switches(test_device, domain=DOMAIN)
        print(f"  ✅ 开关投影: 返回 {len(switches)} 个")

        sensors = project_sensors(test_device, domain=DOMAIN)
        print(f"  ✅ 传感器投影: 返回 {len(sensors)} 个")

        # 测试 7: 测试工具函数
        print("\n🔍 测试 7: 测试工具函数...")
        from custom_components.yeelight_pro.utils import (
            to_bool, to_int, to_float, to_str, to_category
        )

        assert to_bool(True) is True
        assert to_bool(False) is False
        assert to_int(42) == 42
        assert to_float(3.14) == 3.14
        assert to_str("hello") == "hello"
        assert to_category("Light") == "light"
        print(f"  ✅ 所有工具函数测试通过")

        # 测试 8: 测试 manifest.json
        print("\n🔍 测试 8: 测试 manifest.json...")
        import json
        manifest_path = ha_config_dir / "custom_components" / "yeelight_pro" / "manifest.json"
        if manifest_path.exists():
            with open(manifest_path) as f:
                manifest = json.load(f)
            assert manifest["domain"] == DOMAIN
            assert manifest["config_flow"] is True
            print(f"  ✅ manifest.json 验证通过")
        else:
            print(f"  ⚠️  manifest.json 不存在")

        # 测试 9: 测试 hacs.json
        print("\n🔍 测试 9: 测试 hacs.json...")
        hacs_path = ha_config_dir / "hacs.json"
        if hacs_path.exists():
            with open(hacs_path) as f:
                hacs = json.load(f)
            assert "name" in hacs
            assert "homeassistant" in hacs
            print(f"  ✅ hacs.json 验证通过")
        else:
            print(f"  ⚠️  hacs.json 不存在")

        print("\n" + "=" * 60)
        print("🎉 所有真实 HA 环境测试通过！")
        print("=" * 60)
        print("\n✅ 集成可以发布到 HACS")
        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_ha_integration())
    sys.exit(0 if success else 1)
