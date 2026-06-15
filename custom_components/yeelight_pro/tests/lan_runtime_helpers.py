"""Shared LAN runtime test doubles."""

from __future__ import annotations

import asyncio


class FakeLanReader:
    """有限 TCP reader double."""

    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = list(chunks)

    async def read(self, size: int) -> bytes:
        """Return the next chunk, then EOF."""
        await asyncio.sleep(0)
        return self._chunks.pop(0) if self._chunks else b""


class FakeLanWriter:
    """记录写入帧的 TCP writer double."""

    def __init__(self) -> None:
        self.written: list[bytes] = []
        self.closed = False
        self.wait_closed_count = 0

    def write(self, data: bytes) -> None:
        """Record bytes written by the runtime."""
        self.written.append(data)

    async def drain(self) -> None:
        """Match asyncio StreamWriter.drain."""

    def close(self) -> None:
        """Mark the writer closed."""
        self.closed = True

    async def wait_closed(self) -> None:
        """Record graceful close wait."""
        self.wait_closed_count += 1


__all__ = ["FakeLanReader", "FakeLanWriter"]
