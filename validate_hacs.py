#!/usr/bin/env python3
"""HACS 发布验证脚本.

验证 Yeelight Pro 集成是否满足 HACS 发布要求。
"""
import json
import os
import sys
from pathlib import Path


def check_file_exists(path: str, description: str) -> bool:
    """检查文件是否存在."""
    if os.path.exists(path):
        print(f"✅ {description}: {path}")
        return True
    else:
        print(f"❌ {description}: {path} 不存在")
        return False


def check_json_valid(path: str, description: str) -> bool:
    """检查 JSON 文件是否有效."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            json.load(f)
        print(f"✅ {description}: JSON 格式正确")
        return True
    except Exception as e:
        print(f"❌ {description}: JSON 格式错误 - {e}")
        return False


def check_manifest() -> bool:
    """检查 manifest.json."""
    manifest_path = "custom_components/yeelight_pro/manifest.json"
    if not check_file_exists(manifest_path, "manifest.json"):
        return False

    if not check_json_valid(manifest_path, "manifest.json"):
        return False

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    required_fields = ["domain", "name", "codeowners", "config_flow", "documentation", "iot_class", "version"]
    for field in required_fields:
        if field not in manifest:
            print(f"❌ manifest.json 缺少必要字段: {field}")
            return False

    print(f"✅ manifest.json 包含所有必要字段")
    return True


def check_hacs_json() -> bool:
    """检查 hacs.json."""
    hacs_path = "hacs.json"
    if not check_file_exists(hacs_path, "hacs.json"):
        return False

    if not check_json_valid(hacs_path, "hacs.json"):
        return False

    with open(hacs_path, "r", encoding="utf-8") as f:
        hacs = json.load(f)

    required_fields = ["name", "homeassistant", "render_readme"]
    for field in required_fields:
        if field not in hacs:
            print(f"❌ hacs.json 缺少必要字段: {field}")
            return False

    print(f"✅ hacs.json 包含所有必要字段")
    return True


def check_readme() -> bool:
    """检查 README.md."""
    readme_path = "README.md"
    if not check_file_exists(readme_path, "README.md"):
        return False

    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    if len(content) > 100:
        print(f"✅ README.md 内容充足 ({len(content)} 字符)")
        return True
    else:
        print(f"❌ README.md 内容不足 ({len(content)} 字符)")
        return False


def check_platforms() -> bool:
    """检查实体平台."""
    const_path = "custom_components/yeelight_pro/const.py"
    if not check_file_exists(const_path, "const.py"):
        return False

    with open(const_path, "r", encoding="utf-8") as f:
        content = f.read()

    if "PLATFORMS" in content:
        print(f"✅ PLATFORMS 定义存在")
        return True
    else:
        print(f"❌ PLATFORMS 定义不存在")
        return False


def check_config_flow() -> bool:
    """检查配置流程."""
    config_flow_path = "custom_components/yeelight_pro/config_flow.py"
    if not check_file_exists(config_flow_path, "config_flow.py"):
        return False

    with open(config_flow_path, "r", encoding="utf-8") as f:
        content = f.read()

    if "async_step_user" in content:
        print(f"✅ 配置流程存在")
        return True
    else:
        print(f"❌ 配置流程不存在")
        return False


def check_tests() -> bool:
    """检查测试文件."""
    test_dir = "custom_components/yeelight_pro/tests"
    if not os.path.exists(test_dir):
        print(f"❌ 测试目录不存在: {test_dir}")
        return False

    test_files = list(Path(test_dir).glob("test_*.py"))
    if len(test_files) > 0:
        print(f"✅ 测试文件存在: {len(test_files)} 个")
        return True
    else:
        print(f"❌ 测试文件不存在")
        return False


def main() -> bool:
    """主函数."""
    print("=" * 60)
    print("HACS 发布验证")
    print("=" * 60)
    print()

    checks = [
        ("manifest.json", check_manifest),
        ("hacs.json", check_hacs_json),
        ("README.md", check_readme),
        ("PLATFORMS", check_platforms),
        ("配置流程", check_config_flow),
        ("测试文件", check_tests),
    ]

    results = []
    for name, check_func in checks:
        print(f"\n--- {name} ---")
        results.append(check_func())

    print("\n" + "=" * 60)
    print("验证结果")
    print("=" * 60)

    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"✅ 所有验证通过 ({passed}/{total})")
        print("\n集成已准备好发布到 HACS！")
        print("\n发布步骤：")
        print("1. 访问 https://hacs.xyz/docs/publish/start")
        print("2. 登录 GitHub")
        print("3. 提交仓库: https://github.com/Yeelight/ha_yeelight_pro")
        print("4. 等待审核")
        return True
    else:
        print(f"❌ 部分验证失败 ({passed}/{total})")
        return False


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
