"""Debug push service logging tests."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from homeassistant.core import HomeAssistant

from custom_components.yeelight_pro.const import ATTR_SOURCE_DEVICE_ID, DOMAIN
from custom_components.yeelight_pro.debug_push_service import (
    ATTR_PARAMS,
    SERVICE_DEBUG_DUMP_PUSH_HEALTH,
    SERVICE_DEBUG_EMIT_PUSH_PAYLOAD,
    async_register_debug_push_services,
)
from custom_components.yeelight_pro.debug_runtime import ATTR_ENTRY_ID

from .debug_push_service_helpers import (
    debug_push_coordinator,
    debug_push_health_manager,
    synthetic_push_summary,
)


@pytest.mark.asyncio
async def test_debug_emit_push_payload_service_is_quiet_at_info_level(
    hass: HomeAssistant,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """调试注入结果默认不应污染 HA INFO 日志。"""
    coordinator = debug_push_coordinator(summary=synthetic_push_summary())
    hass.data[DOMAIN] = {"entry-1": {"coordinator": coordinator}}

    async_register_debug_push_services(hass)
    with caplog.at_level("INFO"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_DEBUG_EMIT_PUSH_PAYLOAD,
            {
                ATTR_ENTRY_ID: "entry-1",
                ATTR_SOURCE_DEVICE_ID: "12345",
                ATTR_PARAMS: {"p": True},
            },
            blocking=True,
        )

    assert "Emitted debug Yeelight Pro push payload" not in _debug_push_logs(caplog)


@pytest.mark.asyncio
async def test_debug_dump_push_health_is_quiet_at_info_level(
    hass: HomeAssistant,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """push health dump 默认只在 DEBUG 输出，避免活动历史和日志噪音。"""
    coordinator = MagicMock()
    coordinator.debug_mode = True
    hass.data[DOMAIN] = {
        "entry-1": {
            "coordinator": coordinator,
            "push_manager": debug_push_health_manager(),
        }
    }

    async_register_debug_push_services(hass)
    with caplog.at_level("INFO"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_DEBUG_DUMP_PUSH_HEALTH,
            {ATTR_ENTRY_ID: "entry-1"},
            blocking=True,
        )

    assert "Yeelight Pro push health debug dump" not in _debug_push_logs(caplog)


def _debug_push_logs(caplog: pytest.LogCaptureFixture) -> str:
    """Return only this integration's debug push service logs."""
    return "\n".join(
        record.getMessage()
        for record in caplog.records
        if record.name == "custom_components.yeelight_pro.debug_push_service"
    )
