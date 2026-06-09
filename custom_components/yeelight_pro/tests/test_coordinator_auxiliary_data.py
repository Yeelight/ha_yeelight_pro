"""Coordinator auxiliary-data fallback regression tests."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed

from custom_components.yeelight_pro.core.coordinator import YeelightProCoordinator
from custom_components.yeelight_pro.core.exceptions import AuthenticationError

from .coordinator_helpers import _client_with_payloads


@pytest.mark.asyncio
async def test_auxiliary_areas_fall_back_to_empty_list_on_error(
    hass: HomeAssistant,
) -> None:
    """area 首次普通读取异常只影响 area 辅助数据，不阻断主设备轮询."""
    client = _client_with_payloads(
        devices=[
            [{"id": 1, "name": "Lamp", "category": "light", "pid": 100}],
        ],
    )
    client.get_areas.side_effect = RuntimeError("area endpoint unavailable")
    coordinator = YeelightProCoordinator(hass, client, house_id=12345)

    data = await coordinator._async_update_data()

    assert 1 in data
    assert coordinator.areas == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method_name", "attribute_name", "stale_value"),
    [
        ("get_areas", "areas", [{"id": "area-1", "name": "Floor"}]),
        ("get_rooms", "rooms", [{"id": "room-1", "name": "Living"}]),
        ("get_groups", "groups", [{"id": "group-1", "name": "Main"}]),
        ("get_scenes", "scenes", [{"id": "scene-1", "name": "Movie"}]),
        ("get_automations", "automations", [{"id": "auto-1", "name": "Evening"}]),
    ],
)
async def test_auxiliary_data_keeps_previous_successful_value_on_error(
    hass: HomeAssistant,
    method_name: str,
    attribute_name: str,
    stale_value: list[dict],
) -> None:
    """辅助列表普通读取异常时应保留上一轮成功值，避免误报拓扑删除."""
    client = _client_with_payloads(
        devices=[
            [{"id": 1, "name": "Lamp", "category": "light", "pid": 100}],
        ],
    )
    setattr(client, method_name, AsyncMock(side_effect=RuntimeError("unavailable")))
    coordinator = YeelightProCoordinator(hass, client, house_id=12345)
    setattr(coordinator, attribute_name, stale_value)

    data = await coordinator._async_update_data()

    assert 1 in data
    assert getattr(coordinator, attribute_name) == stale_value


@pytest.mark.asyncio
async def test_auxiliary_soft_failure_logs_only_error_type(
    hass: HomeAssistant,
    caplog,
) -> None:
    """辅助列表失败日志不能泄露 house/device/token/URL 等底层错误细节."""
    client = _client_with_payloads(
        devices=[
            [{"id": 1, "name": "Lamp", "category": "light", "pid": 100}],
        ],
    )
    client.get_rooms.side_effect = RuntimeError(
        "house 12345 token secret-token https://api.yeelight.com device 67890"
    )
    coordinator = YeelightProCoordinator(hass, client, house_id=12345)

    with caplog.at_level("WARNING"):
        data = await coordinator._async_update_data()

    assert 1 in data
    assert "Failed to fetch rooms: RuntimeError" in caplog.text
    assert "secret-token" not in caplog.text
    assert "api.yeelight.com" not in caplog.text
    assert "12345" not in caplog.text
    assert "67890" not in caplog.text


@pytest.mark.asyncio
async def test_auxiliary_areas_auth_error_triggers_reauth(
    hass: HomeAssistant,
) -> None:
    """area 认证异常必须继续上抛，避免 token 失效被误判为普通缺数据."""
    client = _client_with_payloads(
        devices=[
            [{"id": 1, "name": "Lamp", "category": "light", "pid": 100}],
        ],
    )
    client.get_areas.side_effect = AuthenticationError("forbidden")
    coordinator = YeelightProCoordinator(hass, client, house_id=12345)

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()
