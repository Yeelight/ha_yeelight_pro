"""Debug push service tests."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from homeassistant.auth.const import GROUP_ID_USER
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import HomeAssistantError, Unauthorized
from homeassistant.helpers import entity_registry as er

from custom_components.yeelight_pro.const import ATTR_SOURCE_DEVICE_ID, DOMAIN
from custom_components.yeelight_pro.debug_push_service import (
    ATTR_ENTITY_ID,
    ATTR_NODE_TYPE,
    ATTR_PAYLOAD_SHAPE,
    ATTR_PARAMS,
    PAYLOAD_SHAPE_PRIVATE_SUBSCRIBE_SNAPSHOT,
    SERVICE_DEBUG_DUMP_PUSH_HEALTH,
    SERVICE_DEBUG_DUMP_PUSH_HEALTH_SCHEMA,
    SERVICE_DEBUG_EMIT_PUSH_PAYLOAD,
    SERVICE_DEBUG_EMIT_PUSH_PAYLOAD_SCHEMA,
    async_register_debug_push_services,
)
from custom_components.yeelight_pro.debug_runtime import ATTR_ENTRY_ID
from .debug_push_service_helpers import (
    debug_push_coordinator,
    debug_push_health_manager,
    synthetic_push_summary,
)


def test_debug_dump_push_health_schema_accepts_optional_entry_id() -> None:
    """debug_dump_push_health schema 只需要可选 entry_id."""
    payload = SERVICE_DEBUG_DUMP_PUSH_HEALTH_SCHEMA({ATTR_ENTRY_ID: "entry-1"})

    assert payload[ATTR_ENTRY_ID] == "entry-1"


def test_debug_emit_push_payload_schema_accepts_runtime_params() -> None:
    """debug_emit_push_payload schema 用于合成 prop 推送."""
    payload = SERVICE_DEBUG_EMIT_PUSH_PAYLOAD_SCHEMA(
        {
            ATTR_ENTRY_ID: "entry-1",
            ATTR_SOURCE_DEVICE_ID: 12345,
            ATTR_NODE_TYPE: "2",
            ATTR_PARAMS: {"p": True},
        }
    )

    assert payload[ATTR_ENTRY_ID] == "entry-1"
    assert payload[ATTR_SOURCE_DEVICE_ID] == 12345
    assert payload[ATTR_NODE_TYPE] == 2
    assert payload[ATTR_PAYLOAD_SHAPE] == "prop"
    assert payload[ATTR_PARAMS] == {"p": True}


def test_debug_emit_push_payload_schema_accepts_entity_id() -> None:
    """debug_emit_push_payload 可通过 HA entity_id 解析源设备."""
    payload = SERVICE_DEBUG_EMIT_PUSH_PAYLOAD_SCHEMA(
        {
            ATTR_ENTRY_ID: "entry-1",
            ATTR_ENTITY_ID: "light.kitchen",
            ATTR_PARAMS: {"p": True},
        }
    )

    assert payload[ATTR_ENTITY_ID] == "light.kitchen"
    assert ATTR_SOURCE_DEVICE_ID not in payload


def test_debug_emit_push_payload_schema_accepts_private_snapshot_shape() -> None:
    """debug 服务可模拟私有 subscribe snapshot 状态帧."""
    payload = SERVICE_DEBUG_EMIT_PUSH_PAYLOAD_SCHEMA(
        {
            ATTR_SOURCE_DEVICE_ID: 12345,
            ATTR_PAYLOAD_SHAPE: PAYLOAD_SHAPE_PRIVATE_SUBSCRIBE_SNAPSHOT,
            ATTR_PARAMS: {"1-p": False},
        }
    )

    assert payload[ATTR_PAYLOAD_SHAPE] == PAYLOAD_SHAPE_PRIVATE_SUBSCRIBE_SNAPSHOT


@pytest.mark.asyncio
async def test_debug_dump_push_health_service_rejects_non_admin_user(
    hass: HomeAssistant,
) -> None:
    """debug_dump_push_health 读取运行态诊断，也必须限制为管理员服务."""
    coordinator = MagicMock()
    coordinator.debug_mode = True
    hass.data[DOMAIN] = {"entry-1": {"coordinator": coordinator}}
    user = await hass.auth.async_create_system_user(
        "limited",
        group_ids=[GROUP_ID_USER],
    )

    async_register_debug_push_services(hass)
    with pytest.raises(Unauthorized):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_DEBUG_DUMP_PUSH_HEALTH,
            {ATTR_ENTRY_ID: "entry-1"},
            blocking=True,
            context=Context(user_id=user.id),
        )


@pytest.mark.asyncio
async def test_debug_emit_push_payload_service_rejects_non_admin_user(
    hass: HomeAssistant,
) -> None:
    """debug_emit_push_payload 会改 HA 运行态，必须限制为管理员服务."""
    coordinator = MagicMock()
    coordinator.debug_mode = True
    coordinator.async_handle_push_payload = AsyncMock()
    hass.data[DOMAIN] = {"entry-1": {"coordinator": coordinator}}
    user = await hass.auth.async_create_system_user(
        "limited",
        group_ids=[GROUP_ID_USER],
    )

    async_register_debug_push_services(hass)
    with pytest.raises(Unauthorized):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_DEBUG_EMIT_PUSH_PAYLOAD,
            {
                ATTR_ENTRY_ID: "entry-1",
                ATTR_SOURCE_DEVICE_ID: 12345,
                ATTR_PARAMS: {"p": True},
            },
            blocking=True,
            context=Context(user_id=user.id),
        )

    coordinator.async_handle_push_payload.assert_not_awaited()


@pytest.mark.asyncio
async def test_debug_dump_push_health_service_rejects_disabled_debug_mode(
    hass: HomeAssistant,
) -> None:
    """debug_mode 关闭时，push health dump 也必须拒绝."""
    coordinator = MagicMock()
    coordinator.debug_mode = False
    hass.data[DOMAIN] = {"entry-1": {"coordinator": coordinator}}

    async_register_debug_push_services(hass)
    with pytest.raises(HomeAssistantError, match="debug mode is disabled"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_DEBUG_DUMP_PUSH_HEALTH,
            {ATTR_ENTRY_ID: "entry-1"},
            blocking=True,
        )


@pytest.mark.asyncio
async def test_debug_emit_push_payload_service_rejects_disabled_debug_mode(
    hass: HomeAssistant,
) -> None:
    """debug_mode 关闭时，合成 push 注入也必须拒绝."""
    coordinator = MagicMock()
    coordinator.debug_mode = False
    coordinator.async_handle_push_payload = AsyncMock()
    hass.data[DOMAIN] = {"entry-1": {"coordinator": coordinator}}

    async_register_debug_push_services(hass)
    with pytest.raises(HomeAssistantError, match="debug mode is disabled"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_DEBUG_EMIT_PUSH_PAYLOAD,
            {
                ATTR_ENTRY_ID: "entry-1",
                ATTR_SOURCE_DEVICE_ID: 12345,
                ATTR_PARAMS: {"p": True},
            },
            blocking=True,
        )

    coordinator.async_handle_push_payload.assert_not_awaited()


@pytest.mark.asyncio
async def test_debug_emit_push_payload_service_injects_synthetic_push(
    hass: HomeAssistant,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """debug 服务应走生产 push bridge，但日志只输出脱敏聚合结果."""
    coordinator = debug_push_coordinator(summary=synthetic_push_summary())
    hass.data[DOMAIN] = {"entry-1": {"coordinator": coordinator}}

    async_register_debug_push_services(hass)
    with caplog.at_level("DEBUG"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_DEBUG_EMIT_PUSH_PAYLOAD,
            {
                ATTR_ENTRY_ID: "entry-1",
                ATTR_SOURCE_DEVICE_ID: "12345",
                ATTR_NODE_TYPE: 2,
                ATTR_PARAMS: {"p": True},
            },
            blocking=True,
        )

    coordinator.async_handle_push_payload.assert_awaited_once_with(
        {
            "type": "prop",
            "nodes": [
                {
                    "id": "12345",
                    "nt": 2,
                    "params": {"p": True},
                }
            ],
        }
    )
    message = "\n".join(
        record.getMessage()
        for record in caplog.records
        if record.name == "custom_components.yeelight_pro.debug_push_service"
    )
    assert "Emitted debug Yeelight Pro push payload" in message
    assert '"changed":true' in message
    assert '"node_id_hash":"ddabe06356586fa8"' in message
    assert '"param_keys":["p"]' in message
    assert "12345" not in message
    assert "True" not in message


@pytest.mark.asyncio
async def test_debug_emit_push_payload_service_injects_private_snapshot_shape(
    hass: HomeAssistant,
) -> None:
    """私有快照形态也必须经生产转换逻辑后进入 push bridge."""
    coordinator = debug_push_coordinator(summary=synthetic_push_summary())
    hass.data[DOMAIN] = {"entry-1": {"coordinator": coordinator}}

    async_register_debug_push_services(hass)
    await hass.services.async_call(
        DOMAIN,
        SERVICE_DEBUG_EMIT_PUSH_PAYLOAD,
        {
            ATTR_ENTRY_ID: "entry-1",
            ATTR_SOURCE_DEVICE_ID: "12345",
            ATTR_NODE_TYPE: 2,
            ATTR_PAYLOAD_SHAPE: PAYLOAD_SHAPE_PRIVATE_SUBSCRIBE_SNAPSHOT,
            ATTR_PARAMS: {"1-p": False, "2-p": True},
        },
        blocking=True,
    )

    coordinator.async_handle_push_payload.assert_awaited_once_with(
        {
            "type": "prop",
            "nodes": [
                {
                    "id": "12345",
                    "nt": 2,
                    "params": {"1-p": False, "2-p": True},
                }
            ],
        }
    )


@pytest.mark.asyncio
async def test_debug_emit_push_payload_service_resolves_entity_id(
    hass: HomeAssistant,
) -> None:
    """合成 push 可从 HA entity_id 的 unique_id 解析 Yeelight 设备 ID."""
    registry = er.async_get(hass)
    registry.async_get_or_create(
        "light",
        DOMAIN,
        f"{DOMAIN}_12345_light",
        suggested_object_id="debug lamp",
    )
    coordinator = debug_push_coordinator()
    hass.data[DOMAIN] = {"entry-1": {"coordinator": coordinator}}

    async_register_debug_push_services(hass)
    await hass.services.async_call(
        DOMAIN,
        SERVICE_DEBUG_EMIT_PUSH_PAYLOAD,
        {
            ATTR_ENTRY_ID: "entry-1",
            ATTR_ENTITY_ID: "light.debug_lamp",
            ATTR_PARAMS: {"p": True},
        },
        blocking=True,
    )

    coordinator.async_handle_push_payload.assert_awaited_once_with(
        {
            "type": "prop",
            "nodes": [{"id": "12345", "nt": 2, "params": {"p": True}}],
        }
    )


@pytest.mark.asyncio
async def test_debug_emit_push_payload_service_requires_source_or_entity(
    hass: HomeAssistant,
) -> None:
    """合成 push 必须指定 source_device_id 或可解析的 entity_id."""
    coordinator = debug_push_coordinator()
    hass.data[DOMAIN] = {"entry-1": {"coordinator": coordinator}}

    async_register_debug_push_services(hass)
    with pytest.raises(HomeAssistantError, match="source_device_id or entity_id"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_DEBUG_EMIT_PUSH_PAYLOAD,
            {ATTR_ENTRY_ID: "entry-1", ATTR_PARAMS: {"p": True}},
            blocking=True,
        )

    coordinator.async_handle_push_payload.assert_not_awaited()


@pytest.mark.asyncio
async def test_debug_dump_push_health_logs_aggregate_payload_only(
    hass: HomeAssistant,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """push health dump 可输出字段名级样本，但不能泄露原始标识。"""
    coordinator = MagicMock()
    coordinator.debug_mode = True
    manager = debug_push_health_manager()
    hass.data[DOMAIN] = {
        "entry-1": {"coordinator": coordinator, "push_manager": manager}
    }

    async_register_debug_push_services(hass)
    with caplog.at_level("DEBUG"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_DEBUG_DUMP_PUSH_HEALTH,
            {ATTR_ENTRY_ID: "entry-1"},
            blocking=True,
        )

    message = "\n".join(
        record.getMessage()
        for record in caplog.records
        if record.name == "custom_components.yeelight_pro.debug_push_service"
    )
    assert "Yeelight Pro push health debug dump" in message
    assert '"status":"data_payload_applied"' in message
    assert '"data_topology_check":"matched_loaded_topology"' in message
    assert '"last_private_status_result":"success"' in message
    assert '"private_status_reason":"no_subscribable_devices"' in message
    assert '"last_private_status_reason":"no_subscribable_devices"' in message
    assert '"keys":["token","value"]' in message
    assert '"result_length":13' in message
    assert '"result_hash":"abc123statushash"' in message
    assert '"data_keys":["message"]' in message
    assert '"node_id_hash":"ddabe06356586fa8"' in message
    assert '"param_keys":["1-sp","o"]' in message
    assert '"matched_collections":["devices","data"]' in message
    assert "secret-node-hash" not in message
    assert "secret-raw-device-id" not in message
    assert "secret-data-hash" not in message
    assert "secret-status" not in message
    assert "secret-value" not in message
