"""Shared fake aiohttp sessions for P0 client tests."""

from __future__ import annotations

import time


class FakeResponse:
    """提供 aiohttp response 需要的最小异步上下文接口。"""

    def __init__(
        self,
        status: int,
        text: str = "error",
        payload: dict[str, object] | None = None,
    ) -> None:
        self.status = status
        self._text = text
        self._payload = payload if payload is not None else {}

    async def __aenter__(self) -> "FakeResponse":
        return self

    async def __aexit__(
        self,
        _exc_type: object,
        _exc: object,
        _traceback: object,
    ) -> None:
        return None

    async def text(self) -> str:
        return self._text

    async def json(self) -> dict[str, object]:
        return self._payload


class FakeSession:
    """提供 client._request 需要的最小 session 接口。"""

    def __init__(
        self,
        status: int,
        text: str = "error",
        payload: dict[str, object] | None = None,
    ) -> None:
        self.status = status
        self.text = text
        self.payload = payload

    def request(self, *_args: object, **_kwargs: object) -> FakeResponse:
        return FakeResponse(self.status, self.text, self.payload)


class FakeOAuthSession:
    """Capture OAuth token requests without network I/O."""

    def __init__(
        self,
        status: int = 200,
        payload: dict[str, object] | None = None,
    ) -> None:
        self.status = status
        self.payload = payload if payload is not None else oauth_success_payload()
        self.calls: list[dict[str, object]] = []

    def post(self, url: str, **kwargs: object) -> FakeResponse:
        self.calls.append({"url": url, **kwargs})
        return FakeResponse(self.status, payload=self.payload)


def oauth_success_payload() -> dict[str, object]:
    """Return a documented OAuth token response."""
    return {
        "access_token": "access-1",
        "token_type": "bearer",
        "refresh_token": "refresh-2",
        "expires_in": 7775999,
        "scope": "read write",
        "id": 122349,
        "region": "CN",
        "device": "home-assistant",
        "client_id": "client-1",
        "username": "user-1",
        "jti": "jti-1",
    }


class FakeScanLoginSession:
    """Capture scan-login requests without network I/O."""

    def __init__(
        self,
        status: int = 200,
        payload: dict[str, object] | None = None,
    ) -> None:
        self.status = status
        self.payload = payload if payload is not None else scan_login_created_payload()
        self.calls: list[dict[str, object]] = []

    def post(self, url: str, **kwargs: object) -> FakeResponse:
        self.calls.append({"url": url, **kwargs})
        return FakeResponse(self.status, payload=self.payload)


def scan_login_created_payload() -> dict[str, object]:
    """Return a documented scan-login CREATED response."""
    now_ms = int(time.time() * 1000)
    return {
        "success": True,
        "code": "0",
        "msg": "ok",
        "data": {
            "qrCodeId": "qr-1",
            "device": "ha-device-1",
            "createAt": now_ms,
            "expireIn": 300_000,
            "expireAt": now_ms + 300_000,
            "status": "CREATED",
            "token": None,
            "source": "homeassistant",
        },
    }


def scan_login_login_payload() -> dict[str, object]:
    """Return a documented scan-login LOGIN response with token data."""
    now_ms = int(time.time() * 1000)
    return {
        "success": True,
        "code": "0",
        "msg": "ok",
        "data": {
            "qrCodeId": "qr-1",
            "device": "ha-device-1",
            "createAt": now_ms,
            "expireIn": 300_000,
            "expireAt": now_ms + 300_000,
            "status": "LOGIN",
            "source": "homeassistant",
            "token": {
                "accessToken": "access-1",
                "tokenType": "bearer",
                "refreshToken": "refresh-2",
                "expiresIn": 7775999,
                "scope": "read write",
                "id": 122349,
                "region": "CN",
                "device": "ha-device-1",
                "clientId": "client-1",
                "username": "user-1",
            },
        },
    }
