"""Exercise LAN framing and topology recovery without exposed listening ports."""

import asyncio
import socket
from contextlib import asynccontextmanager

import pytest

from custom_components.yeelight_pro.lan_contract import (
    decode_lan_frames,
    encode_lan_frame,
)
from custom_components.yeelight_pro.lan_runtime import LanGatewayRuntime


@asynccontextmanager
async def connected_runtime(peer, receive, endpoint="gateway"):
    """Use real stream sockets without interference from local port scanners."""
    peers = []

    async def open_connection(host, port):
        client, server = socket.socketpair()
        reader, writer = await asyncio.open_connection(sock=client)
        peer_reader, peer_writer = await asyncio.open_connection(sock=server)
        peers.append(asyncio.create_task(peer(peer_reader, peer_writer)))
        return reader, writer

    runtime = LanGatewayRuntime(
        "unused", endpoint_kind=endpoint, open_connection=open_connection,
    )
    try:
        await runtime.async_start(receive)
        yield runtime
    finally:
        await runtime.async_stop()
        await asyncio.gather(*peers)


@pytest.mark.asyncio
@pytest.mark.parametrize("split", [1, 2])
async def test_utf8_character_split_across_reads(split):
    payload = {"method": "gateway_post.topology", "name": "主卫浴室灯带"}
    wire = encode_lan_frame(payload)
    cut = wire.index("主".encode()) + split
    received = asyncio.get_running_loop().create_future()

    async def peer(reader, writer):
        try:
            writer.write(wire[:cut])
            await writer.drain()
            await asyncio.sleep(0.05)
            writer.write(wire[cut:])
            await writer.drain()
            await reader.read()
        finally:
            writer.close()
            await writer.wait_closed()

    async def receive(message):
        if not received.done():
            received.set_result(message)

    async with connected_runtime(peer, receive):
        assert await asyncio.wait_for(received, 1) == payload


@pytest.mark.asyncio
@pytest.mark.parametrize("endpoint,method", [
    ("gateway", "gateway_get.topology"),
    ("wifi_panel", "device_get.topology"),
])
async def test_reconnect_requests_and_receives_topology(endpoint, method):
    recovered = asyncio.get_running_loop().create_future()
    requests = []
    payload = {"method": "gateway_post.topology", "name": "主卫"}

    async def peer(reader, writer):
        try:
            request = await reader.readline()
            if not request:
                return
            requests.append(decode_lan_frames(request)[0])
            if len(requests) == 1:
                return  # Drop the connection before its topology response.
            writer.write(encode_lan_frame(payload))
            await writer.drain()
            await reader.read()
        finally:
            writer.close()
            await writer.wait_closed()

    async def receive(message):
        if not recovered.done():
            recovered.set_result(message)

    async with connected_runtime(peer, receive, endpoint) as runtime:
        await runtime.async_get_topology()
        assert await asyncio.wait_for(recovered, 4) == payload
        assert [request["method"] for request in requests] == [method, method]
        assert requests[0]["id"] != requests[1]["id"]


@pytest.mark.asyncio
async def test_reconnect_recovers_when_wait_closed_raises_connection_reset():
    """Socket resets stored on StreamWriter.wait_closed() must not kill reconnect."""
    from custom_components.yeelight_pro.tests.lan_runtime_helpers import (
        FakeLanReader,
        FakeLanWriter,
    )

    recovered = asyncio.get_running_loop().create_future()
    payload = {"method": "gateway_post.topology", "name": "主卧床头灯带"}
    attempts = 0

    class ResettingReader:
        async def read(self, size: int) -> bytes:
            await asyncio.sleep(0)
            raise ConnectionResetError(104, "Connection reset by peer")

    class ResettingWriter(FakeLanWriter):
        async def wait_closed(self) -> None:
            self.wait_closed_count += 1
            raise ConnectionResetError(104, "Connection reset by peer")

    async def open_connection(host, port):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return ResettingReader(), ResettingWriter()
        return FakeLanReader([encode_lan_frame(payload)]), FakeLanWriter()

    async def receive(message):
        if not recovered.done():
            recovered.set_result(message)

    runtime = LanGatewayRuntime("10.0.30.22", open_connection=open_connection)
    try:
        await runtime.async_start(receive)
        assert await asyncio.wait_for(recovered, 4) == payload
        assert attempts == 2
    finally:
        await runtime.async_stop()


@pytest.mark.asyncio
async def test_pending_ack_flushed_on_disconnect_raises_ha_error_not_cancelled():
    """Disconnect while waiting for ACK must raise HomeAssistantError, not CancelledError."""
    from homeassistant.exceptions import HomeAssistantError
    from custom_components.yeelight_pro.tests.lan_runtime_helpers import FakeLanWriter

    send_started = asyncio.Event()

    class DisconnectingReader:
        async def read(self, size: int) -> bytes:
            await send_started.wait()
            return b""

    class TriggeringWriter(FakeLanWriter):
        async def drain(self) -> None:
            send_started.set()

    async def open_connection(host, port):
        return DisconnectingReader(), TriggeringWriter()

    runtime = LanGatewayRuntime("10.0.30.22", open_connection=open_connection)
    try:
        await runtime.async_start(lambda _: asyncio.sleep(0))
        with pytest.raises(HomeAssistantError, match="not connected"):
            await runtime.async_set_properties([{"id": 312356039, "set": {"p": False}}])
    finally:
        await runtime.async_stop()


@pytest.mark.asyncio
async def test_ack_timeout_marks_half_open_socket_disconnected_and_raises_command_error(
    monkeypatch: pytest.MonkeyPatch,
):
    """Unanswered ACK on a silent socket must trigger reconnect and reject false success."""
    from custom_components.yeelight_pro.core.exceptions import CommandError
    from custom_components.yeelight_pro.core.lan_control import (
        async_try_lan_control_device,
    )
    from custom_components.yeelight_pro.tests.lan_runtime_helpers import FakeLanWriter

    class SilentReader:
        async def read(self, size: int) -> bytes:
            await asyncio.sleep(60)
            return b""

    async def open_connection(host, port):
        return SilentReader(), FakeLanWriter()

    monkeypatch.setattr("custom_components.yeelight_pro.lan_runtime._LAN_ACK_TIMEOUT", 0.05)
    runtime = LanGatewayRuntime("10.0.30.22", open_connection=open_connection)
    try:
        await runtime.async_start(lambda _: asyncio.sleep(0))
        with pytest.raises(CommandError, match="timed out waiting for ACK"):
            await async_try_lan_control_device(
                runtime,
                device_id=312356039,
                params={"p": False},
            )
        await asyncio.sleep(0)
        assert runtime.health.connected is False
        assert runtime.health.ack_timeout_count == 1
    finally:
        await runtime.async_stop()

@pytest.mark.asyncio
async def test_cloud_coordinator_lan_topology_schedules_refresh_without_wiping_devices(
    hass,
):
    """Optional LAN topology push on a cloud entry must not overwrite other gateways' devices."""
    from unittest.mock import AsyncMock, MagicMock
    from custom_components.yeelight_pro.core.coordinator import YeelightProCoordinator

    coordinator = YeelightProCoordinator(hass=hass, client=MagicMock(), house_id=1)
    coordinator.devices = {999: {"id": 999, "name": "Other Gateway Light"}}
    coordinator.async_refresh_from_lan_topology = AsyncMock()

    await coordinator.async_handle_lan_payload(
        {
            "id": 1,
            "method": "gateway_post.topology",
            "nodes": [{"id": 1001, "nt": 2, "type": 3, "n": "Local Light"}],
        }
    )
    await hass.async_block_till_done()

    assert 999 in coordinator.devices
    coordinator.async_refresh_from_lan_topology.assert_awaited_once()
    await coordinator.async_shutdown()

