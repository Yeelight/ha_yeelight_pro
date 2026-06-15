"""WiFi full-screen LAN runtime endpoint tests."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest

from custom_components.yeelight_pro.const import (
    CONF_LOCAL_GATEWAY_CONTROL,
    CONF_LOCAL_GATEWAY_PORT,
)
from custom_components.yeelight_pro.lan_contract import (
    LanDiscoveryResponse,
    decode_lan_frames,
)
from custom_components.yeelight_pro.lan_runtime import (
    LAN_ENDPOINT_WIFI_PANEL,
    LanGatewayRuntime,
    async_start_lan_runtime,
)

from .config_entry_lifecycle_helpers import make_config_entry
from .lan_runtime_helpers import FakeLanReader, FakeLanWriter


@pytest.mark.asyncio
async def test_start_lan_runtime_uses_wifi_panel_endpoint_for_discovered_pid_2(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """发现 pid=2 时，runtime 应使用 WiFi 全面屏 device_* 方法族。"""
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
            product_id=2,
            mac="F8:24:41:00:23:A4",
            device_id="22535",
            ip="192.168.1.102",
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

    assert fake_runtime.host == "192.168.1.102"
    assert fake_runtime.port == 65444
    assert fake_runtime.endpoint_kind == LAN_ENDPOINT_WIFI_PANEL
    assert fake_runtime.callback is coordinator.async_handle_lan_payload
    assert fake_runtime.topology_requested is True


@pytest.mark.asyncio
async def test_lan_runtime_writes_wifi_panel_topology_and_property_frames() -> None:
    """WiFi 全面屏 endpoint 应写出 device_get.topology/device_set.prop。"""
    writer = FakeLanWriter()
    reader = FakeLanReader([b'{"id":2,"result":"ok","data":{}}\r\n'])

    async def _open_connection(
        host: str,
        port: int,
    ) -> tuple[FakeLanReader, FakeLanWriter]:
        assert (host, port) == ("192.168.1.21", 65443)
        return reader, writer

    runtime = LanGatewayRuntime(
        host="192.168.1.21",
        endpoint_kind=LAN_ENDPOINT_WIFI_PANEL,
        open_connection=_open_connection,
    )
    await runtime.async_start(AsyncMock())
    await runtime.async_get_topology()
    await runtime.async_set_properties([
        {"id": 7919, "nt": 2, "set": {"1-p": False}},
    ])

    frames = [decode_lan_frames(frame)[0] for frame in writer.written]
    assert [frame["method"] for frame in frames] == [
        "device_get.topology",
        "device_set.prop",
    ]
    assert frames[1]["nodes"] == [{"id": 7919, "nt": 2, "set": {"1-p": False}}]

    await runtime.async_stop()


@pytest.mark.asyncio
async def test_wifi_panel_runtime_rejects_unsupported_scene_payload() -> None:
    """WiFi 全面屏文档不支持 gateway scenes 控制，不能发送伪命令。"""
    writer = FakeLanWriter()

    async def _open_connection(
        host: str,
        port: int,
    ) -> tuple[FakeLanReader, FakeLanWriter]:
        return FakeLanReader([]), writer

    runtime = LanGatewayRuntime(
        host="192.168.1.21",
        endpoint_kind=LAN_ENDPOINT_WIFI_PANEL,
        open_connection=_open_connection,
    )
    await runtime.async_start(AsyncMock())

    ack = await runtime.async_set_properties([], scenes=[{"id": 413, "duration": 500}])

    assert ack == {
        "result": "error",
        "data": {"reason": "unsupported_wifi_panel_request"},
    }
    assert writer.written == []

    await runtime.async_stop()
