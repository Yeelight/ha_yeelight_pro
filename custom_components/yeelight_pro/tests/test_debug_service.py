"""Debug event service tests."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from homeassistant.auth.const import GROUP_ID_USER
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import HomeAssistantError, Unauthorized

from custom_components.yeelight_pro.const import (
    ATTR_COMPONENT_ID,
    ATTR_EVENT_ATTRIBUTES,
    ATTR_EVENT_TYPE,
    ATTR_SOURCE_DEVICE_ID,
    DOMAIN,
)
from custom_components.yeelight_pro.debug_push_service import (
    SERVICE_DEBUG_DUMP_PUSH_HEALTH,
    SERVICE_DEBUG_EMIT_PUSH_PAYLOAD,
)
from custom_components.yeelight_pro.debug_runtime import ATTR_ENTRY_ID
from custom_components.yeelight_pro.debug_service import (
    SERVICE_DEBUG_EMIT_EVENT_SCHEMA,
    _debug_coordinator,
    async_register_debug_event_service,
)


def test_debug_coordinator_routes_to_requested_entry_id(
    hass: HomeAssistant,
) -> None:
    """多 entry 调试事件应可指定目标 config entry."""
    first = MagicMock()
    first.debug_mode = True
    second = MagicMock()
    second.debug_mode = True
    hass.data[DOMAIN] = {
        "entry-1": {"coordinator": first},
        "entry-2": {"coordinator": second},
    }

    assert _debug_coordinator(hass, entry_id="entry-2") is second


def test_debug_coordinator_rejects_invalid_or_disabled_entry_id(
    hass: HomeAssistant,
) -> None:
    """指定 entry_id 时必须存在且启用 debug mode."""
    disabled = MagicMock()
    disabled.debug_mode = False
    hass.data[DOMAIN] = {"entry-1": {"coordinator": disabled}}

    assert _debug_coordinator(hass, entry_id="entry-1") is None
    assert _debug_coordinator(hass, entry_id="missing") is None


def test_debug_service_schema_accepts_optional_entry_id() -> None:
    """debug_emit_event schema 必须接受可选 entry_id 并保留事件字段."""
    payload = SERVICE_DEBUG_EMIT_EVENT_SCHEMA(
        {
            ATTR_ENTRY_ID: "entry-1",
            ATTR_SOURCE_DEVICE_ID: 12345,
            ATTR_COMPONENT_ID: "button",
            ATTR_EVENT_TYPE: "click",
        }
    )

    assert payload[ATTR_ENTRY_ID] == "entry-1"
    assert payload[ATTR_SOURCE_DEVICE_ID] == 12345
    assert payload[ATTR_EVENT_ATTRIBUTES] == {}


def test_debug_service_registers_push_debug_services(hass: HomeAssistant) -> None:
    """统一 debug 入口必须继续注册 push 诊断服务."""
    async_register_debug_event_service(hass)

    assert hass.services.has_service(DOMAIN, "debug_emit_event")
    assert hass.services.has_service(DOMAIN, SERVICE_DEBUG_DUMP_PUSH_HEALTH)
    assert hass.services.has_service(DOMAIN, SERVICE_DEBUG_EMIT_PUSH_PAYLOAD)


@pytest.mark.asyncio
async def test_debug_emit_event_service_rejects_non_admin_user(
    hass: HomeAssistant,
) -> None:
    """debug_emit_event 可注入 HA 事件，必须限制为管理员服务."""
    coordinator = MagicMock()
    coordinator.debug_mode = True
    coordinator.async_handle_runtime_event = AsyncMock()
    hass.data[DOMAIN] = {"entry-1": {"coordinator": coordinator}}
    user = await hass.auth.async_create_system_user(
        "limited",
        group_ids=[GROUP_ID_USER],
    )

    async_register_debug_event_service(hass)
    with pytest.raises(Unauthorized):
        await hass.services.async_call(
            DOMAIN,
            "debug_emit_event",
            {
                ATTR_ENTRY_ID: "entry-1",
                ATTR_SOURCE_DEVICE_ID: 12345,
                ATTR_COMPONENT_ID: "button",
                ATTR_EVENT_TYPE: "click",
            },
            blocking=True,
            context=Context(user_id=user.id),
        )

    coordinator.async_handle_runtime_event.assert_not_awaited()


@pytest.mark.asyncio
async def test_debug_emit_event_service_rejects_disabled_debug_mode(
    hass: HomeAssistant,
) -> None:
    """debug_mode 关闭时，服务调用必须拒绝且不分发事件."""
    coordinator = MagicMock()
    coordinator.debug_mode = False
    coordinator.async_handle_runtime_event = AsyncMock()
    hass.data[DOMAIN] = {"entry-1": {"coordinator": coordinator}}

    async_register_debug_event_service(hass)
    with pytest.raises(HomeAssistantError, match="debug mode is disabled"):
        await hass.services.async_call(
            DOMAIN,
            "debug_emit_event",
            {
                ATTR_ENTRY_ID: "entry-1",
                ATTR_SOURCE_DEVICE_ID: 12345,
                ATTR_COMPONENT_ID: "button",
                ATTR_EVENT_TYPE: "click",
            },
            blocking=True,
        )

    coordinator.async_handle_runtime_event.assert_not_awaited()


@pytest.mark.asyncio
async def test_debug_emit_event_service_is_quiet_at_info_level(
    hass: HomeAssistant,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """调试事件注入成功后默认不写 INFO 日志。"""
    event = MagicMock()
    event.event_type = "click"
    coordinator = MagicMock()
    coordinator.debug_mode = True
    coordinator.async_handle_runtime_event = AsyncMock(return_value=event)
    hass.data[DOMAIN] = {"entry-1": {"coordinator": coordinator}}

    async_register_debug_event_service(hass)
    with caplog.at_level("INFO"):
        await hass.services.async_call(
            DOMAIN,
            "debug_emit_event",
            {
                ATTR_ENTRY_ID: "entry-1",
                ATTR_SOURCE_DEVICE_ID: 12345,
                ATTR_COMPONENT_ID: "button",
                ATTR_EVENT_TYPE: "click",
            },
            blocking=True,
        )

    message = "\n".join(record.getMessage() for record in caplog.records)
    assert "Emitted debug Yeelight Pro event" not in message
