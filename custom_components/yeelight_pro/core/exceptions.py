"""Yeelight Pro 统一异常体系."""

from __future__ import annotations

import re


class YeelightProError(Exception):
    """Yeelight Pro 集成基础异常."""


class ConnectionError(YeelightProError):
    """连接错误."""


class AuthenticationError(YeelightProError):
    """认证错误."""


class DeviceNotFoundError(YeelightProError):
    """设备未找到."""


class DeviceOfflineError(YeelightProError):
    """设备离线."""


class CommandError(YeelightProError):
    """命令执行错误."""


class DiscoveryError(YeelightProError):
    """设备发现错误."""


class ProtocolError(YeelightProError):
    """协议错误."""


class TokenExpiredError(AuthenticationError):
    """Token 已过期."""


class RateLimitError(YeelightProError):
    """请求频率限制."""


class ServerError(YeelightProError):
    """服务器错误."""


_SAFE_CODE_RE = re.compile(r"\b(?:code|HTTP)\s+([0-9]{3,5})\b", re.IGNORECASE)


def safe_error_summary(err: BaseException) -> str:
    """Return a log-safe error summary without vendor payload details."""
    summary = type(err).__name__
    match = _SAFE_CODE_RE.search(str(err))
    if match:
        return f"{summary} code {match.group(1)}"
    return summary
