"""Yeelight Pro 统一异常体系."""

from __future__ import annotations


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


def safe_error_summary(err: BaseException) -> str:
    """Return a log-safe error summary without vendor payload details."""
    return type(err).__name__
