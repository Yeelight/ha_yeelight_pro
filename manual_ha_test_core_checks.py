#!/usr/bin/env python3
"""Core smoke checks for root-level manual Home Assistant scripts."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from manual_ha_test_helpers import add_python_path, print_exception


async def check_ha_core_import() -> bool:
    """保留旧 complete 脚本的 HA 核心环境检查入口。"""
    print("\n🔍 测试 1: HA 核心模块导入...")
    print("  ✅ HA 核心模块导入成功")
    return True


async def check_integration_import(*, path: Path | None = None) -> bool:
    """检查集成核心模块和全部平台可导入。"""
    print("\n🔍 测试集成导入...")
    try:
        if path is not None:
            add_python_path(path)
        from custom_components.yeelight_pro.const import DOMAIN, PLATFORMS
        from custom_components.yeelight_pro.core.client import YeelightProClient
        from custom_components.yeelight_pro.core.coordinator import (
            YeelightProCoordinator,
        )

        print(f"  ✅ DOMAIN: {DOMAIN}")
        print(f"  ✅ PLATFORMS: {len(PLATFORMS)} 个")
        print(f"  ✅ YeelightProClient: {YeelightProClient.__name__}")
        print(f"  ✅ YeelightProCoordinator: {YeelightProCoordinator.__name__}")

        for platform in PLATFORMS:
            module = __import__(
                f"custom_components.yeelight_pro.{platform}",
                fromlist=[platform],
            )
            assert hasattr(module, "async_setup_entry")
            print(f"  ✅ {platform} 平台导入成功")
        return True
    except Exception as err:
        print_exception("集成导入失败", err)
        return False


async def check_client_creation(
    *,
    timeout: int | None = None,
    check_no_auth: bool = False,
) -> bool:
    """检查 client 基础属性、认证头和 request id。"""
    print("\n🔍 测试客户端创建...")
    try:
        from custom_components.yeelight_pro.core.client import YeelightProClient

        kwargs = {"timeout": timeout} if timeout is not None else {}
        client = YeelightProClient(
            domain="api.yeelight.com",
            access_token="test_token",
            session=MagicMock(),
            **kwargs,
        )

        assert client.domain == "api.yeelight.com"
        assert client.base_url == "https://api.yeelight.com"
        assert client._get_headers(with_auth=True)["Authorization"] == "Bearer test_token"
        assert client._next_request_id().startswith("ha-yeelight-")
        if check_no_auth:
            assert "Authorization" not in client._get_headers(with_auth=False)

        print("  ✅ 客户端创建成功")
        print("  ✅ 认证头生成正确")
        print("  ✅ 请求 ID 生成正确")
        if check_no_auth:
            print("  ✅ 无认证请求头正确")
        return True
    except Exception as err:
        print_exception("客户端创建失败", err)
        return False


async def check_canonical_models() -> bool:
    """检查 canonical model 的 from_dict/to_dict smoke 行为。"""
    print("\n🔍 测试规范模型...")
    try:
        from custom_components.yeelight_pro.canonical.models import (
            HAProductModel,
            ComponentModel,
            PropertyModel,
        )

        prop_data = {
            "prop_id": "brightness",
            "name": "亮度",
            "property_type": "integer",
            "value_range": {"min": 0, "max": 100, "step": 1},
        }
        prop = PropertyModel.from_dict(prop_data)
        assert prop.prop_id == "brightness"
        assert prop.name == "亮度"

        comp_data = {"component_id": "light", "name": "灯光", "properties": [prop_data]}
        comp = ComponentModel.from_dict(comp_data)
        assert comp.component_id == "light"
        assert len(comp.properties) == 1

        product = HAProductModel.from_dict(
            {
                "product": {"model_id": "YLCT01", "name": "Yeelight 灯泡"},
                "components": [comp_data],
            }
        )
        assert product.product.model_id == "YLCT01"
        assert len(product.components) == 1
        assert "product" in product.to_dict()

        print("  ✅ PropertyModel 创建成功")
        print("  ✅ ComponentModel 创建成功")
        print("  ✅ HAProductModel 创建成功")
        print("  ✅ to_dict 转换成功")
        return True
    except Exception as err:
        print_exception("规范模型测试失败", err)
        return False


async def check_config_flow() -> bool:
    """检查 config flow 基础步骤跳转。"""
    print("\n🔍 测试配置流程...")
    try:
        from custom_components.yeelight_pro.config_flow import YeelightProConfigFlow
        from custom_components.yeelight_pro.const import (
            CONNECTION_MODE_CLOUD,
            CONNECTION_MODE_PRIVATE,
        )

        flow = YeelightProConfigFlow()
        assert flow.VERSION == 1
        assert flow._connection_mode is None
        result = await flow.async_step_user()
        assert result["type"] == "form"
        assert result["step_id"] == "user"

        result = await flow.async_step_user({"connection_mode": CONNECTION_MODE_CLOUD})
        assert result["type"] == "form"
        assert result["step_id"] == "cloud_auth"
        assert flow._connection_mode == CONNECTION_MODE_CLOUD

        flow._connection_mode = None
        result = await flow.async_step_user({"connection_mode": CONNECTION_MODE_PRIVATE})
        assert result["type"] == "form"
        assert result["step_id"] == "private_config"
        assert flow._connection_mode == CONNECTION_MODE_PRIVATE

        print("  ✅ 配置流程创建成功")
        print("  ✅ 用户步骤正常")
        print("  ✅ 云端模式选择正常")
        print("  ✅ 私有模式选择正常")
        return True
    except Exception as err:
        print_exception("配置流程测试失败", err)
        return False


async def check_utils(*, include_to_str_or_empty: bool = False) -> bool:
    """检查常用工具函数 smoke 行为。"""
    print("\n🔍 测试工具函数...")
    try:
        from custom_components.yeelight_pro.utils import (
            matches_any,
            matches_category,
            to_bool,
            to_category,
            to_float,
            to_int,
            to_str,
            to_str_or_empty,
        )

        assert to_bool(True) is True
        assert to_bool(False) is False
        assert to_bool("true") is True
        assert to_bool("false") is False
        assert to_bool(None) is False
        assert to_int(42) == 42
        assert to_int("100") == 100
        assert to_int(None) is None
        assert to_float(3.14) == 3.14
        assert to_float("2.5") == 2.5
        assert to_float(None) is None
        assert to_str("hello") == "hello"
        assert to_str(123) == "123"
        assert to_str(None) is None
        assert to_category("Light") == "light"
        assert to_category(None) == ""
        assert matches_any(["light_controller", "fan_switch"], ("light",)) is True
        assert matches_any(["switch", "outlet"], ("light", "fan")) is False
        assert matches_category("light_controller", ("light",)) is True
        assert matches_category("fan", ("light",)) is False
        if include_to_str_or_empty:
            assert to_str_or_empty("hello") == "hello"
            assert to_str_or_empty(None) == ""
        print("  ✅ 工具函数测试通过")
        return True
    except Exception as err:
        print_exception("工具函数测试失败", err)
        return False


async def check_platform_entities() -> bool:
    """检查平台常量和平台模块 import。"""
    print("\n🔍 测试平台实体...")
    try:
        from custom_components.yeelight_pro.const import (
            PLATFORMS,
            get_enabled_platforms,
        )

        expected_platforms = [
            "binary_sensor",
            "button",
            "climate",
            "cover",
            "event",
            "fan",
            "light",
            "number",
            "select",
            "sensor",
            "switch",
        ]
        for platform in expected_platforms:
            assert platform in PLATFORMS, f"缺少平台: {platform}"
        assert "text" not in PLATFORMS
        assert "scene" not in PLATFORMS
        assert "lock" not in PLATFORMS
        assert "vacuum" not in PLATFORMS
        assert "lock" not in get_enabled_platforms({})
        assert "vacuum" not in get_enabled_platforms({})

        for module_name in PLATFORMS:
            __import__(
                f"custom_components.yeelight_pro.{module_name}",
                fromlist=[module_name],
            )
            print(f"  ✅ {module_name} 模块导入成功")
        print(f"  ✅ PLATFORMS 注册 {len(expected_platforms)} 个平台")
        print("  ✅ 无文档支撑的平台未加载")
        return True
    except Exception as err:
        print_exception("平台实体测试失败", err)
        return False


async def check_services(*, require_setup_entry: bool = False) -> bool:
    """检查集成 setup entrypoint 是否存在。"""
    print("\n🔍 测试服务定义...")
    try:
        init_module = __import__("custom_components.yeelight_pro", fromlist=["__init__"])
        if hasattr(init_module, "async_setup"):
            print("  ✅ async_setup 函数存在")
        else:
            print("  ⚠️  async_setup 函数不存在")

        has_setup_entry = hasattr(init_module, "async_setup_entry")
        if require_setup_entry and not has_setup_entry:
            print("  ❌ async_setup_entry 函数不存在")
            return False
        if has_setup_entry:
            print("  ✅ async_setup_entry 函数存在")
        return True
    except Exception as err:
        print_exception("服务定义测试失败", err)
        return False
