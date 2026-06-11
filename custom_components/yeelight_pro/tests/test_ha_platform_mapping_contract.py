"""Home Assistant platform mapping boundary tests."""

from __future__ import annotations

from custom_components.yeelight_pro.capabilities.ha_platforms import (
    EXPERIMENTAL_HA_PLATFORMS,
    HA_CORE_PLATFORMS,
    HA_PLATFORM_MAPPING_MATRIX,
    MAPPED_HA_PLATFORMS,
    SUPPORTED_HA_PLATFORMS,
    UNSUPPORTED_HA_PLATFORMS,
    ha_platform_mapping_status,
)
from custom_components.yeelight_pro.const import PLATFORMS
from homeassistant.const import Platform

HA_2026_PLATFORM_ADDITIONS = {
    "ai_task",
    "assist_satellite",
    "conversation",
    "infrared",
    "radio_frequency",
}


def test_supported_platform_matrix_matches_loaded_platforms() -> None:
    """运行时加载平台必须有明确的映射状态."""
    assert set(PLATFORMS) == SUPPORTED_HA_PLATFORMS | EXPERIMENTAL_HA_PLATFORMS
    assert EXPERIMENTAL_HA_PLATFORMS == frozenset()

    statuses = {item.platform: item.status for item in HA_PLATFORM_MAPPING_MATRIX}
    for platform in SUPPORTED_HA_PLATFORMS:
        assert statuses[platform] == "supported"
    for platform in EXPERIMENTAL_HA_PLATFORMS:
        assert ha_platform_mapping_status(platform) == "experimental"


def test_mapping_matrix_covers_ha_core_platform_space() -> None:
    """HA 核心平台空间必须全部有支持/实验/不支持结论，避免目标狭窄."""
    assert HA_CORE_PLATFORMS == MAPPED_HA_PLATFORMS
    assert len(HA_CORE_PLATFORMS) > len(PLATFORMS)


def test_ha_core_platform_space_matches_installed_home_assistant() -> None:
    """平台合同至少覆盖当前测试 HA 运行时和已验证 HA 2026 新平台."""
    assert {platform.value for platform in Platform}.issubset(HA_CORE_PLATFORMS)
    assert HA_2026_PLATFORM_ADDITIONS.issubset(HA_CORE_PLATFORMS)


def test_unsupported_ha_platforms_are_not_loaded() -> None:
    """缺少易来属性/事件/动作支撑的平台不能进入 PLATFORMS."""
    assert UNSUPPORTED_HA_PLATFORMS.isdisjoint(PLATFORMS)
    for platform in UNSUPPORTED_HA_PLATFORMS:
        assert ha_platform_mapping_status(platform) == "unsupported"


def test_user_facing_platform_question_has_no_narrow_target_set() -> None:
    """sensor/event/button/select/number/cover/climate 不是完整目标集合."""
    user_listed = {
        "sensor",
        "event",
        "button",
        "select",
        "number",
        "cover",
        "climate",
    }

    assert user_listed < SUPPORTED_HA_PLATFORMS
    assert {
        "light",
        "switch",
        "binary_sensor",
    }.issubset(SUPPORTED_HA_PLATFORMS - user_listed)
    assert "scene" in UNSUPPORTED_HA_PLATFORMS
