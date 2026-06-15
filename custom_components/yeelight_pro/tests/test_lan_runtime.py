"""LAN gateway runtime wiring tests."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from homeassistant.exceptions import HomeAssistantError

from custom_components.yeelight_pro.const import (
    CONF_LOCAL_GATEWAY_CONTROL,
    CONF_LOCAL_GATEWAY_HOST,
    CONF_LOCAL_GATEWAY_PORT,
)
from custom_components.yeelight_pro.lan_contract import (
    LanDiscoveryResponse,
    decode_lan_frames,
)
from custom_components.yeelight_pro.lan_runtime import (
    LanGatewayRuntime,
    async_start_lan_runtime,
    lan_runtime_options,
)

from .config_entry_lifecycle_helpers import make_config_entry
from .lan_runtime_helpers import FakeLanReader, FakeLanWriter


def test_lan_runtime_options_reads_config_entry_options() -> None:
    """LAN options 应规范化启用、host 与端口字段."""
    entry = make_config_entry()

    assert lan_runtime_options(entry) == (False, "", 65443)

    entry.options = {
        CONF_LOCAL_GATEWAY_CONTROL: True,
        CONF_LOCAL_GATEWAY_HOST: " 192.168.1.20 ",
        CONF_LOCAL_GATEWAY_PORT: "65444",
    }

    assert lan_runtime_options(entry) == (True, "192.168.1.20", 65444)


@pytest.mark.asyncio
async def test_start_lan_runtime_requires_discovery_when_host_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """启用本地控制但未填 host 时，发现不到网关才失败."""
    entry = make_config_entry()
    entry.options = {CONF_LOCAL_GATEWAY_CONTROL: True}
    discover = AsyncMock(return_value=None)
    monkeypatch.setattr(
        "custom_components.yeelight_pro.lan_runtime.async_discover_lan_gateway",
        discover,
    )

    with pytest.raises(HomeAssistantError):
        await async_start_lan_runtime(entry, AsyncMock())

    discover.assert_awaited_once()


@pytest.mark.asyncio
async def test_start_lan_runtime_stays_disabled_by_default() -> None:
    """默认配置不应创建 LAN runtime."""
    entry = make_config_entry()

    assert await async_start_lan_runtime(entry, AsyncMock()) is None


@pytest.mark.asyncio
async def test_start_lan_runtime_opens_gateway_and_requests_topology(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """配置 host 后应启动 runtime 并发送 topology 请求."""
    created: dict[str, Any] = {}

    class FakeRuntime:
        def __init__(self, *, host: str, port: int, endpoint_kind: str) -> None:
            self.host = host
            self.port = port
            self.endpoint_kind = endpoint_kind
            self.callback: Callable[[Mapping[str, Any]], Awaitable[object]] | None = None
            self.topology_requested = False
            created["runtime"] = self

        async def async_start(
            self,
            callback: Callable[[Mapping[str, Any]], Awaitable[object]],
        ) -> None:
            self.callback = callback

        async def async_get_topology(self) -> None:
            self.topology_requested = True

    entry = make_config_entry()
    entry.options = {
        CONF_LOCAL_GATEWAY_CONTROL: True,
        CONF_LOCAL_GATEWAY_HOST: "192.168.1.20",
        CONF_LOCAL_GATEWAY_PORT: 65444,
    }
    coordinator = AsyncMock()
    monkeypatch.setattr(
        "custom_components.yeelight_pro.lan_runtime.LanGatewayRuntime",
        FakeRuntime,
    )

    runtime = await async_start_lan_runtime(entry, coordinator)
    fake_runtime = cast(FakeRuntime, runtime)

    assert runtime is created["runtime"]
    assert fake_runtime.host == "192.168.1.20"
    assert fake_runtime.port == 65444
    assert fake_runtime.endpoint_kind == "gateway"
    assert fake_runtime.callback is coordinator.async_handle_lan_payload
    assert fake_runtime.topology_requested is True


@pytest.mark.asyncio
async def test_start_lan_runtime_discovers_gateway_when_host_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """显式启用 LAN 控制且 host 为空时，可用 UDP 发现结果启动 TCP runtime."""
    created: dict[str, Any] = {}

    class FakeRuntime:
        def __init__(self, *, host: str, port: int, endpoint_kind: str) -> None:
            self.host = host
            self.port = port
            self.endpoint_kind = endpoint_kind
            self.callback: Callable[[Mapping[str, Any]], Awaitable[object]] | None = None
            self.topology_requested = False
            created["runtime"] = self

        async def async_start(
            self,
            callback: Callable[[Mapping[str, Any]], Awaitable[object]],
        ) -> None:
            self.callback = callback

        async def async_get_topology(self) -> None:
            self.topology_requested = True

    discover = AsyncMock(
        return_value=LanDiscoveryResponse(
            product_id=1,
            mac="F8:24:41:00:23:A4",
            device_id="22535",
            ip="192.168.1.101",
        )
    )
    entry = make_config_entry()
    entry.options = {
        CONF_LOCAL_GATEWAY_CONTROL: True,
        CONF_LOCAL_GATEWAY_PORT: 65444,
    }
    coordinator = AsyncMock()
    monkeypatch.setattr(
        "custom_components.yeelight_pro.lan_runtime.async_discover_lan_gateway",
        discover,
    )
    monkeypatch.setattr(
        "custom_components.yeelight_pro.lan_runtime.LanGatewayRuntime",
        FakeRuntime,
    )

    runtime = await async_start_lan_runtime(entry, coordinator)
    fake_runtime = cast(FakeRuntime, runtime)

    discover.assert_awaited_once()
    assert fake_runtime.host == "192.168.1.101"
    assert fake_runtime.port == 65444
    assert fake_runtime.endpoint_kind == "gateway"
    assert fake_runtime.callback is coordinator.async_handle_lan_payload
    assert fake_runtime.topology_requested is True


@pytest.mark.asyncio
async def test_lan_gateway_runtime_writes_topology_and_property_frames() -> None:
    """LAN runtime 应写出 CRLF 分隔的 topology 与 set.prop 帧."""
    writer = FakeLanWriter()
    reader = FakeLanReader(
        [
            b'{"id":2,"result":"ok","data":{}}\r\n',
        ]
    )

    async def _open_connection(host: str, port: int) -> tuple[FakeLanReader, FakeLanWriter]:
        assert (host, port) == ("192.168.1.20", 65443)
        return reader, writer

    runtime = LanGatewayRuntime(
        host="192.168.1.20",
        open_connection=_open_connection,
    )
    await runtime.async_start(AsyncMock())
    await runtime.async_get_topology()
    await runtime.async_set_properties([
        {"id": 331915, "params": {"p": True}},
    ])

    frames = [decode_lan_frames(frame)[0] for frame in writer.written]
    assert [frame["method"] for frame in frames] == [
        "gateway_get.topology",
        "gateway_set.prop",
    ]
    assert frames[1]["nodes"] == [{"id": 331915, "params": {"p": True}}]
    assert runtime.health.as_dict()["sent_count"] == 2
    assert runtime.health.as_dict()["ack_count"] == 1

    await runtime.async_stop()

    assert writer.closed is True
    assert writer.wait_closed_count == 1


@pytest.mark.asyncio
async def test_lan_gateway_runtime_dispatches_received_frames() -> None:
    """收到 gateway_post 帧时应交给 coordinator/runtime bridge 回调."""
    received: list[Mapping[str, Any]] = []
    received_event = asyncio.Event()
    payload = (
        b'{"version":"1.0","id":8,"method":"gateway_post.prop","nodes":'
        b'[{"id":331915,"nt":2,"params":{"p":true}}]}\r\n'
    )

    async def _open_connection(
        host: str,
        port: int,
    ) -> tuple[FakeLanReader, FakeLanWriter]:
        return FakeLanReader([payload[:40], payload[40:]]), FakeLanWriter()

    async def _callback(data: Mapping[str, Any]) -> None:
        received.append(data)
        received_event.set()

    runtime = LanGatewayRuntime(
        host="192.168.1.20",
        open_connection=_open_connection,
    )

    await runtime.async_start(_callback)
    await asyncio.wait_for(received_event.wait(), timeout=1)
    await runtime.async_stop()

    assert received == [
        {
            "version": "1.0",
            "id": 8,
            "method": "gateway_post.prop",
            "nodes": [{"id": 331915, "nt": 2, "params": {"p": True}}],
        }
    ]
    assert runtime.health.as_dict()["received_count"] == 1


@pytest.mark.asyncio
async def test_lan_gateway_runtime_records_connection_error_type() -> None:
    """连接失败时 health 只记录异常类型，不泄漏 host/token 文本."""

    async def _open_connection(host: str, port: int) -> tuple[Any, Any]:
        raise OSError("192.168.1.20 token-secret")

    runtime = LanGatewayRuntime(
        host="192.168.1.20",
        open_connection=_open_connection,
    )

    with pytest.raises(OSError):
        await runtime.async_start(MagicMock())

    assert runtime.health.as_dict() == {
        "running": False,
        "connected": False,
        "sent_count": 0,
        "received_count": 0,
        "ack_count": 0,
        "ack_timeout_count": 0,
        "reconnect_attempts": 0,
        "last_error_type": "OSError",
    }
    assert "192.168.1.20" not in str(runtime.health.as_dict())
    assert "token-secret" not in str(runtime.health.as_dict())
