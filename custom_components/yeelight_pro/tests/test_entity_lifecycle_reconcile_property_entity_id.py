"""Tests for legacy Yeelight property-helper entity_id reconciliation."""

from __future__ import annotations

from types import SimpleNamespace

from homeassistant.const import EntityCategory
import pytest

from custom_components.yeelight_pro.entity_lifecycle import (
    async_reconcile_entity_registry,
)

from .entity_lifecycle_helpers import (
    FakeEntityRegistry,
    lifecycle_coordinator,
    patch_entity_registry,
    registry_entry,
)
from .projection_helpers import projection_payload


@pytest.mark.asyncio
async def test_reconcile_renames_legacy_property_control_entity_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """旧英文属性名 helper entity_id 应迁移为官方中文属性名."""
    registry = FakeEntityRegistry(
        [
            registry_entry(
                unique_id="yeelight_pro_312613269_light_dd_number",
                entity_id="number.cai_guang_deng_cai_guang_deng_cai_guang_deng_default_duration",
                domain="number",
                original_name="彩光灯 default duration",
            ),
            registry_entry(
                unique_id="yeelight_pro_312613269_light_slisaon_select",
                entity_id="select.cai_guang_deng_cai_guang_deng_cai_guang_deng_slisaon",
                domain="select",
                original_name="彩光灯 slisaon",
            ),
            registry_entry(
                unique_id="yeelight_pro_312613269_light_bp_select",
                entity_id="select.cai_guang_deng_cai_guang_deng_cai_guang_deng_power_on_boot",
                domain="select",
                original_name="彩光灯 power on boot",
            ),
        ]
    )
    patch_entity_registry(monkeypatch, registry)

    await async_reconcile_entity_registry(
        SimpleNamespace(),
        SimpleNamespace(entry_id="entry_1"),
        lifecycle_coordinator(data={312613269: _legacy_color_light_payload()}),
    )

    assert registry.updated_entities == [
        (
            "number.cai_guang_deng_cai_guang_deng_cai_guang_deng_default_duration",
            {
                "new_entity_id": "number.cai_guang_deng_mo_ren_jian_bian_shi_chang",
                "original_name": "默认渐变时长",
                "original_icon": "mdi:numeric",
                "entity_category": EntityCategory.CONFIG,
                "disabled_by": None,
            },
        ),
        (
            "select.cai_guang_deng_cai_guang_deng_cai_guang_deng_slisaon",
            {
                "new_entity_id": "select.cai_guang_deng_shi_fou_kai_qi_shan_duan",
                "original_name": "是否开启闪断",
                "original_icon": "mdi:form-dropdown",
                "entity_category": EntityCategory.CONFIG,
                "disabled_by": None,
            },
        ),
        (
            "select.cai_guang_deng_cai_guang_deng_cai_guang_deng_power_on_boot",
            {
                "new_entity_id": "select.cai_guang_deng_shang_dian_hou_zhuang_tai",
                "original_name": "上电后状态",
                "original_icon": "mdi:form-dropdown",
                "entity_category": EntityCategory.CONFIG,
                "disabled_by": None,
            },
        ),
    ]


@pytest.mark.asyncio
async def test_reconcile_preserves_user_named_legacy_property_entity_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """用户命名的旧属性 helper entity_id 不应被自动迁移."""
    registry = FakeEntityRegistry(
        [
            registry_entry(
                unique_id="yeelight_pro_312613269_light_dd_number",
                entity_id="number.cai_guang_deng_cai_guang_deng_cai_guang_deng_default_duration",
                domain="number",
                original_name="彩光灯 default duration",
                name="自定义渐变",
            )
        ]
    )
    patch_entity_registry(monkeypatch, registry)

    await async_reconcile_entity_registry(
        SimpleNamespace(),
        SimpleNamespace(entry_id="entry_1"),
        lifecycle_coordinator(data={312613269: _legacy_color_light_payload()}),
    )

    assert registry.updated_entities == [
        (
            "number.cai_guang_deng_cai_guang_deng_cai_guang_deng_default_duration",
            {
                "original_name": "默认渐变时长",
                "original_icon": "mdi:numeric",
                "entity_category": EntityCategory.CONFIG,
                "disabled_by": None,
            },
        )
    ]


def _legacy_color_light_payload() -> dict:
    """构造含官方可写属性能力的彩光灯 payload."""
    payload = projection_payload(
        device_id="312613269",
        category="light",
        component_id="light",
        component_category="color light",
        state={"p": True, "dd": 300, "bp": "1", "slisaon": "0"},
        params={"dd": 300, "bp": "1", "slisaon": "0"},
    )
    payload["name"] = "彩光灯"
    payload["ha_device_instance"]["name"] = "彩光灯"
    payload["ha_device_instance"]["device_info"]["name"] = "彩光灯"
    payload["ha_device_instance"]["components"][0]["name"] = "彩光灯"
    payload["ha_product_model"]["components"][0]["name"] = "彩光灯"
    payload["ha_product_model"]["components"][0]["properties"] = _light_properties()
    return payload


def _light_properties() -> list[dict]:
    """Return official writable light helper properties for tests."""
    return [
        {"prop_id": "p", "access": "read_write", "property_type": "bool"},
        {
            "prop_id": "dd",
            "name": "default duration",
            "access": "read_write",
            "property_type": "config",
            "format": "int",
            "value_range": {"min": 0, "max": 10000, "step": 100},
            "unit": "ms",
        },
        {
            "prop_id": "bp",
            "name": "power on boot",
            "access": "read_write",
            "property_type": "config",
            "format": "int",
            "value_list": [
                {"code": "0", "desc": "断电前状态"},
                {"code": "1", "desc": "开启"},
                {"code": "2", "desc": "关闭"},
            ],
        },
        {
            "prop_id": "slisaon",
            "name": "slisaon",
            "access": "read_write",
            "property_type": "config",
            "format": "int",
            "value_list": [
                {"code": "0", "desc": "关闭"},
                {"code": "1", "desc": "开启"},
            ],
        },
    ]
