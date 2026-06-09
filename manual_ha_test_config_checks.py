#!/usr/bin/env python3
"""Config-file smoke checks for root-level manual Home Assistant scripts."""
from __future__ import annotations

import json
from pathlib import Path

from manual_ha_test_helpers import print_exception


async def check_manifest(base_dir: Path) -> bool:
    """检查 manifest.json 的发布必备字段。"""
    print("\n🔍 测试 manifest.json...")
    try:
        manifest_path = base_dir / "custom_components" / "yeelight_pro" / "manifest.json"
        with manifest_path.open(encoding="utf-8") as file:
            manifest = json.load(file)
        for field in ["domain", "name", "version", "config_flow", "iot_class"]:
            assert field in manifest, f"manifest.json 缺少字段: {field}"
        print("  ✅ manifest.json 存在且格式正确")
        return True
    except Exception as err:
        print_exception("manifest.json 测试失败", err)
        return False


async def check_hacs_json(base_dir: Path, *, optional: bool = False) -> bool:
    """检查 hacs.json 字段；完整 HA 脚本允许 HA config 目录缺失该文件。"""
    print("\n🔍 测试 hacs.json...")
    try:
        hacs_path = base_dir / "hacs.json"
        if optional and not hacs_path.exists():
            print("  ⚠️  hacs.json 不存在（可选）")
            return True
        with hacs_path.open(encoding="utf-8") as file:
            hacs = json.load(file)
        for field in ["name", "homeassistant"]:
            assert field in hacs, f"hacs.json 缺少字段: {field}"
        print("  ✅ hacs.json 存在且格式正确")
        return True
    except Exception as err:
        print_exception("hacs.json 测试失败", err)
        return False


async def check_strings_json(base_dir: Path, *, optional: bool = True) -> bool:
    """检查 strings.json 是否包含 config 根节点。"""
    print("\n🔍 测试 strings.json...")
    try:
        strings_path = base_dir / "custom_components" / "yeelight_pro" / "strings.json"
        if optional and not strings_path.exists():
            print("  ⚠️  strings.json 不存在（可选）")
            return True
        with strings_path.open(encoding="utf-8") as file:
            strings = json.load(file)
        assert "config" in strings
        print("  ✅ strings.json 验证通过")
        return True
    except Exception as err:
        print_exception("strings.json 测试失败", err)
        return False


async def check_config_files(base_dir: Path) -> bool:
    """检查完整 HA smoke 脚本中的配置文件集合。"""
    print("\n🔍 测试配置文件验证...")
    manifest_ok = await check_manifest(base_dir)
    hacs_ok = await check_hacs_json(base_dir, optional=True)
    strings_ok = await check_strings_json(base_dir, optional=True)
    return manifest_ok and hacs_ok and strings_ok
