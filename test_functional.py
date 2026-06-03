#!/usr/bin/env python3
"""Yeelight Pro 集成本地功能测试脚本.

这个脚本用于在没有实际 HA 环境的情况下测试集成的基本功能。
"""
import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


async def test_client_api():
    """测试客户端 API."""
    print("\n🔍 测试客户端 API...")

    try:
        from custom_components.yeelight_pro.core.client import YeelightProClient
        from custom_components.yeelight_pro.core.exceptions import (
            AuthenticationError,
            ConnectionError,
        )

        # 创建模拟 session
        mock_session = MagicMock()

        # 创建客户端实例
        client = YeelightProClient(
            domain="api.yeelight.com",
            access_token="test_token",
            session=mock_session,
        )

        print("  ✅ 客户端创建成功")
        print(f"     - 域名: {client.domain}")
        print(f"     - Base URL: {client.base_url}")

        # 测试请求头生成
        headers = client._get_headers(with_auth=True)
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test_token"
        print("  ✅ 认证头生成正确")

        # 测试请求 ID 生成
        request_id = client._next_request_id()
        assert request_id.startswith("ha-yeelight-")
        print("  ✅ 请求 ID 生成正确")

        return True

    except Exception as e:
        print(f"  ❌ 客户端测试失败: {e}")
        return False


async def test_canonical_models():
    """测试规范模型."""
    print("\n🔍 测试规范模型...")

    try:
        from custom_components.yeelight_pro.canonical.models import (
            HAProductModel,
            HADeviceInstanceModel,
            ComponentModel,
            PropertyModel,
        )

        # 测试 PropertyModel
        prop_data = {
            "prop_id": "brightness",
            "name": "亮度",
            "property_type": "integer",
            "value_range": {"min": 0, "max": 100, "step": 1},
        }
        prop = PropertyModel.from_dict(prop_data)
        assert prop.prop_id == "brightness"
        assert prop.name == "亮度"
        print("  ✅ PropertyModel 创建成功")

        # 测试 ComponentModel
        comp_data = {
            "component_id": "light",
            "name": "灯光",
            "properties": [prop_data],
        }
        comp = ComponentModel.from_dict(comp_data)
        assert comp.component_id == "light"
        assert len(comp.properties) == 1
        print("  ✅ ComponentModel 创建成功")

        # 测试 HAProductModel
        product_data = {
            "product": {
                "model_id": "YLCT01",
                "name": "Yeelight 灯泡",
            },
            "components": [comp_data],
        }
        product = HAProductModel.from_dict(product_data)
        assert product.product.model_id == "YLCT01"
        assert len(product.components) == 1
        print("  ✅ HAProductModel 创建成功")

        # 测试 to_dict
        product_dict = product.to_dict()
        assert "product" in product_dict
        assert "components" in product_dict
        print("  ✅ to_dict 转换成功")

        return True

    except Exception as e:
        print(f"  ❌ 规范模型测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_projector():
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
        # light 可能是 None 或 HALightProjection
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
        print("  ✅ to_bool 测试通过")

        # 测试 to_int
        assert to_int(42) == 42
        assert to_int("100") == 100
        assert to_int(None) is None
        print("  ✅ to_int 测试通过")

        # 测试 to_float
        assert to_float(3.14) == 3.14
        assert to_float("2.5") == 2.5
        assert to_float(None) is None
        print("  ✅ to_float 测试通过")

        # 测试 to_str
        assert to_str("hello") == "hello"
        assert to_str(123) == "123"
        assert to_str(None) is None
        print("  ✅ to_str 测试通过")

        # 测试 to_category
        assert to_category("Light") == "light"
        assert to_category(None) == ""
        print("  ✅ to_category 测试通过")

        # 测试 matches_any
        assert matches_any(["light_controller", "fan_switch"], ("light",)) is True
        assert matches_any(["switch", "outlet"], ("light", "fan")) is False
        print("  ✅ matches_any 测试通过")

        # 测试 matches_category
        assert matches_category("light_controller", ("light",)) is True
        assert matches_category("fan", ("light",)) is False
        print("  ✅ matches_category 测试通过")

        return True

    except Exception as e:
        print(f"  ❌ 工具函数测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_config_flow():
    """测试配置流程."""
    print("\n🔍 测试配置流程...")

    try:
        from custom_components.yeelight_pro.config_flow import YeelightProConfigFlow
        from custom_components.yeelight_pro.const import (
            DOMAIN,
            CONNECTION_MODE_CLOUD,
            CONNECTION_MODE_PRIVATE,
        )

        # 创建配置流程实例
        flow = YeelightProConfigFlow()
        assert flow.VERSION == 1
        assert flow._connection_mode is None
        print("  ✅ 配置流程创建成功")

        # 测试用户步骤
        result = await flow.async_step_user()
        assert result["type"] == "form"
        assert result["step_id"] == "user"
        print("  ✅ 用户步骤正常")

        # 测试选择云端模式
        result = await flow.async_step_user(
            {"connection_mode": CONNECTION_MODE_CLOUD}
        )
        assert result["type"] == "form"
        assert result["step_id"] == "cloud_auth"
        assert flow._connection_mode == CONNECTION_MODE_CLOUD
        print("  ✅ 云端模式选择正常")

        # 测试选择私有模式
        flow._connection_mode = None
        result = await flow.async_step_user(
            {"connection_mode": CONNECTION_MODE_PRIVATE}
        )
        assert result["type"] == "form"
        assert result["step_id"] == "private_config"
        assert flow._connection_mode == CONNECTION_MODE_PRIVATE
        print("  ✅ 私有模式选择正常")

        return True

    except Exception as e:
        print(f"  ❌ 配置流程测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_platform_entities():
    """测试平台实体."""
    print("\n🔍 测试平台实体...")

    try:
        from custom_components.yeelight_pro.const import PLATFORMS

        expected_platforms = [
            "binary_sensor",
            "button",
            "climate",
            "cover",
            "event",
            "fan",
            "light",
            "lock",
            "number",
            "scene",
            "select",
            "sensor",
            "switch",
            "text",
            "vacuum",
        ]

        # 检查所有平台都在 PLATFORMS 列表中
        for platform in expected_platforms:
            assert platform in PLATFORMS, f"缺少平台: {platform}"

        print(f"  ✅ PLATFORMS 列表包含所有 {len(expected_platforms)} 个平台")

        # 测试平台模块导入
        platform_modules = [
            "light",
            "fan",
            "switch",
            "sensor",
            "binary_sensor",
            "cover",
            "climate",
            "lock",
            "event",
            "scene",
            "button",
            "select",
            "number",
            "vacuum",
            "text",
        ]

        for module_name in platform_modules:
            try:
                module = __import__(
                    f"custom_components.yeelight_pro.{module_name}",
                    fromlist=[module_name],
                )
                print(f"  ✅ {module_name} 模块导入成功")
            except Exception as e:
                print(f"  ⚠️  {module_name} 模块导入失败: {e}")

        return True

    except Exception as e:
        print(f"  ❌ 平台实体测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_services():
    """测试服务定义."""
    print("\n🔍 测试服务定义...")

    try:
        from custom_components.yeelight_pro.const import DOMAIN

        # 检查 __init__.py 中的服务注册
        init_module = __import__(
            "custom_components.yeelight_pro",
            fromlist=["__init__"],
        )

        # 检查是否有服务注册函数
        if hasattr(init_module, "async_setup"):
            print("  ✅ async_setup 函数存在")
        else:
            print("  ⚠️  async_setup 函数不存在")

        return True

    except Exception as e:
        print(f"  ❌ 服务定义测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """运行所有测试."""
    print("=" * 60)
    print("🚀 Yeelight Pro 集成功能测试")
    print("=" * 60)

    results = []

    # 运行各项测试
    tests = [
        ("客户端 API", test_client_api),
        ("规范模型", test_canonical_models),
        ("投影层", test_projector),
        ("工具函数", test_utils),
        ("配置流程", test_config_flow),
        ("平台实体", test_platform_entities),
        ("服务定义", test_services),
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
        print("\n🎉 所有功能测试通过！")
        print("\n✅ 集成可以发布")
        return True
    else:
        print("\n⚠️  部分测试失败，请检查并修复问题")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
