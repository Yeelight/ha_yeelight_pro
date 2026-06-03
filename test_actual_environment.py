#!/usr/bin/env python3
"""Yeelight Pro 集成 - 实际环境测试脚本.

这个脚本用于在真实的 Home Assistant 环境中测试集成。
使用方法:
1. 将此脚本复制到 HA 配置目录
2. 运行: python test_in_ha.py
"""
import asyncio
import sys
import os
from pathlib import Path


async def test_integration_import():
    """测试集成导入."""
    print("\n🔍 测试集成导入...")

    try:
        # 添加路径
        sys.path.insert(0, str(Path(__file__).parent))

        # 测试核心模块导入
        from custom_components.yeelight_pro.const import DOMAIN, PLATFORMS
        from custom_components.yeelight_pro.core.client import YeelightProClient
        from custom_components.yeelight_pro.core.coordinator import YeelightProCoordinator
        from custom_components.yeelight_pro.core.exceptions import (
            AuthenticationError,
            ConnectionError,
        )

        print(f"  ✅ DOMAIN: {DOMAIN}")
        print(f"  ✅ PLATFORMS: {len(PLATFORMS)} 个")
        print(f"  ✅ YeelightProClient: {YeelightProClient.__name__}")
        print(f"  ✅ YeelightProCoordinator: {YeelightProCoordinator.__name__}")

        # 测试平台导入
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

        return True

    except Exception as e:
        print(f"  ❌ 集成导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_client_creation():
    """测试客户端创建."""
    print("\n🔍 测试客户端创建...")

    try:
        from unittest.mock import MagicMock
        from custom_components.yeelight_pro.core.client import YeelightProClient

        # 创建模拟 session
        mock_session = MagicMock()

        # 创建客户端实例
        client = YeelightProClient(
            domain="api.yeelight.com",
            access_token="test_token",
            session=mock_session,
        )

        print(f"  ✅ 客户端创建成功")
        print(f"     - 域名: {client.domain}")
        print(f"     - Base URL: {client.base_url}")

        # 测试请求头生成
        headers = client._get_headers(with_auth=True)
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test_token"
        print(f"  ✅ 认证头生成正确")

        # 测试请求 ID 生成
        request_id = client._next_request_id()
        assert request_id.startswith("ha-yeelight-")
        print(f"  ✅ 请求 ID 生成正确")

        return True

    except Exception as e:
        print(f"  ❌ 客户端创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_config_flow():
    """测试配置流程."""
    print("\n🔍 测试配置流程...")

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

        # 测试选择云端模式
        result = await flow.async_step_user(
            {"connection_mode": CONNECTION_MODE_CLOUD}
        )
        assert result["type"] == "form"
        assert result["step_id"] == "cloud_auth"
        assert flow._connection_mode == CONNECTION_MODE_CLOUD
        print(f"  ✅ 云端模式选择正常")

        # 测试选择私有模式
        flow._connection_mode = None
        result = await flow.async_step_user(
            {"connection_mode": CONNECTION_MODE_PRIVATE}
        )
        assert result["type"] == "form"
        assert result["step_id"] == "private_config"
        assert flow._connection_mode == CONNECTION_MODE_PRIVATE
        print(f"  ✅ 私有模式选择正常")

        return True

    except Exception as e:
        print(f"  ❌ 配置流程测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_projectors():
    """测试投影层."""
    print("\n🔍 测试投影层...")

    try:
        from custom_components.yeelight_pro.projector.light import project_light
        from custom_components.yeelight_pro.projector.fan import project_fans
        from custom_components.yeelight_pro.projector.switch import project_switches
        from custom_components.yeelight_pro.projector.sensor import project_sensors

        # 测试数据
        device_data = {
            "device_id": 12345,
            "name": "客厅灯",
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
                    "name": "客厅灯",
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

        # 测试灯光投影
        light = project_light(device_data, domain="yeelight_pro")
        print(f"  ✅ 灯光投影: {'成功' if light else '返回 None'}")

        # 测试风扇投影
        fans = project_fans(device_data, domain="yeelight_pro")
        assert isinstance(fans, list)
        print(f"  ✅ 风扇投影: 返回 {len(fans)} 个")

        # 测试开关投影
        switches = project_switches(device_data, domain="yeelight_pro")
        assert isinstance(switches, list)
        print(f"  ✅ 开关投影: 返回 {len(switches)} 个")

        # 测试传感器投影
        sensors = project_sensors(device_data, domain="yeelight_pro")
        assert isinstance(sensors, list)
        print(f"  ✅ 传感器投影: 返回 {len(sensors)} 个")

        return True

    except Exception as e:
        print(f"  ❌ 投影层测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_utils():
    """测试工具函数."""
    print("\n🔍 测试工具函数...")

    try:
        from custom_components.yeelight_pro.utils import (
            to_bool,
            to_int,
            to_float,
            to_str,
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

        return True

    except Exception as e:
        print(f"  ❌ 工具函数测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_manifest():
    """测试 manifest.json."""
    print("\n🔍 测试 manifest.json...")

    try:
        import json
        manifest_path = Path(__file__).parent / "custom_components" / "yeelight_pro" / "manifest.json"

        if not manifest_path.exists():
            print(f"  ❌ manifest.json 不存在")
            return False

        with open(manifest_path) as f:
            manifest = json.load(f)

        # 检查必需字段
        required_fields = ["domain", "name", "version", "config_flow", "iot_class"]
        for field in required_fields:
            if field not in manifest:
                print(f"  ❌ manifest.json 缺少字段: {field}")
                return False

        print(f"  ✅ manifest.json 存在且格式正确")
        print(f"     - domain: {manifest['domain']}")
        print(f"     - name: {manifest['name']}")
        print(f"     - version: {manifest['version']}")
        print(f"     - config_flow: {manifest['config_flow']}")
        print(f"     - iot_class: {manifest['iot_class']}")

        return True

    except Exception as e:
        print(f"  ❌ manifest.json 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_hacs_json():
    """测试 hacs.json."""
    print("\n🔍 测试 hacs.json...")

    try:
        import json
        hacs_path = Path(__file__).parent / "hacs.json"

        if not hacs_path.exists():
            print(f"  ❌ hacs.json 不存在")
            return False

        with open(hacs_path) as f:
            hacs = json.load(f)

        # 检查必需字段
        required_fields = ["name", "homeassistant", "render_readme"]
        for field in required_fields:
            if field not in hacs:
                print(f"  ❌ hacs.json 缺少字段: {field}")
                return False

        print(f"  ✅ hacs.json 存在且格式正确")
        print(f"     - name: {hacs['name']}")
        print(f"     - homeassistant: {hacs['homeassistant']}")
        print(f"     - render_readme: {hacs['render_readme']}")

        return True

    except Exception as e:
        print(f"  ❌ hacs.json 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """运行所有测试."""
    print("=" * 60)
    print("🚀 Yeelight Pro 集成 - 实际环境测试")
    print("=" * 60)

    results = []

    # 运行各项测试
    tests = [
        ("集成导入", test_integration_import),
        ("客户端创建", test_client_creation),
        ("配置流程", test_config_flow),
        ("投影层", test_projectors),
        ("工具函数", test_utils),
        ("manifest.json", test_manifest),
        ("hacs.json", test_hacs_json),
    ]

    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ {test_name} 测试异常: {e}")
            results.append((test_name, False))

    # 显示测试结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")

    print("\n" + "-" * 60)
    print(f"总计: {passed}/{total} 测试通过")
    print(f"通过率: {passed / total * 100:.1f}%")

    if passed == total:
        print("\n🎉 所有实际环境测试通过！")
        print("\n✅ 集成可以发布到 HACS")
        return True
    else:
        print("\n⚠️  部分测试失败，请检查并修复问题")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
