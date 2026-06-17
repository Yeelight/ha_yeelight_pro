"""Shared test doubles for Yeelight Pro push transport tests."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from aiohttp import WSMsgType


@dataclass(slots=True)
class FakeMessage:
    """提供 aiohttp websocket message 需要的最小字段。"""

    type: WSMsgType
    data: str | bytes | None


class FakeWebSocket:
    """内存 websocket double，用于有限消息流测试。"""

    def __init__(self, messages: list[FakeMessage]) -> None:
        self._messages = messages
        self.sent_json: list[dict[str, Any]] = []
        self.closed = False

    async def send_json(self, data: dict[str, Any]) -> None:
        """记录发送到 websocket 的 JSON frame。"""
        self.sent_json.append(data)

    async def close(self) -> None:
        """标记 websocket 已关闭。"""
        self.closed = True

    def __aiter__(self) -> "FakeWebSocket":
        return self

    async def __anext__(self) -> FakeMessage:
        if not self._messages:
            raise StopAsyncIteration
        return self._messages.pop(0)


class OpenFakeWebSocket(FakeWebSocket):
    """保持打开状态，直到 reader task 被取消。"""

    def __init__(self) -> None:
        super().__init__([])
        self.waiting_for_message = asyncio.Event()

    async def __anext__(self) -> FakeMessage:
        self.waiting_for_message.set()
        await asyncio.Event().wait()
        raise StopAsyncIteration


class FailingSubscribeWebSocket(FakeWebSocket):
    """发送 subscribe frame 时失败的 websocket double。"""

    async def send_json(self, data: dict[str, Any]) -> None:
        self.sent_json.append(data)
        raise ConnectionError("token-secret")


class HangingSubscribeWebSocket(FakeWebSocket):
    """发送 subscribe frame 时挂起的 websocket double。"""

    def __init__(self) -> None:
        super().__init__([])
        self.send_started = asyncio.Event()

    async def send_json(self, data: dict[str, Any]) -> None:
        self.sent_json.append(data)
        self.send_started.set()
        await asyncio.Event().wait()


class FailingCloseWebSocket(OpenFakeWebSocket):
    """第一次 close 失败，第二次 close 成功的 websocket double。"""

    def __init__(self) -> None:
        super().__init__()
        self.close_attempts = 0

    async def close(self) -> None:
        self.close_attempts += 1
        if self.close_attempts == 1:
            raise OSError("token-secret")
        await super().close()


class FailingHeartbeatWebSocket(OpenFakeWebSocket):
    """发送 heartbeat frame 时失败的 websocket double。"""

    def __init__(self) -> None:
        super().__init__()
        self.closed_event = asyncio.Event()

    async def send_json(self, data: dict[str, Any]) -> None:
        self.sent_json.append(data)
        if data.get("method") == "heartbeat":
            raise OSError("token-secret")

    async def close(self) -> None:
        await super().close()
        self.closed_event.set()


class FailingReaderWebSocket(FakeWebSocket):
    """读取消息时失败的 websocket double。"""

    def __init__(self) -> None:
        super().__init__([])
        self.reader_started = asyncio.Event()
        self.closed_event = asyncio.Event()

    async def __anext__(self) -> FakeMessage:
        self.reader_started.set()
        raise OSError("token-secret")

    async def close(self) -> None:
        await super().close()
        self.closed_event.set()


class FakeSession:
    """注入 transport 的最小 aiohttp session double。"""

    def __init__(
        self,
        websocket: FakeWebSocket | Exception | list[FakeWebSocket | Exception],
    ) -> None:
        self._websockets = websocket if isinstance(websocket, list) else [websocket]
        self.connected_urls: list[str] = []

    async def ws_connect(self, url: str) -> FakeWebSocket:
        self.connected_urls.append(url)
        if not self._websockets:
            raise AssertionError("no websocket double queued")
        websocket = self._websockets.pop(0)
        if isinstance(websocket, Exception):
            raise websocket
        return websocket


class ControlledSleep:
    """由测试显式释放的 sleep double。"""

    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.delays: list[float] = []

    async def __call__(self, delay: float) -> None:
        self.delays.append(delay)
        self.started.set()
        await self.release.wait()
        self.release.clear()
        self.started.clear()


async def wait_for_sleep_calls(sleep: ControlledSleep, count: int) -> None:
    """等待 sleep double 达到指定调用次数。"""
    while len(sleep.delays) < count:
        await sleep.started.wait()
        await asyncio.sleep(0)
