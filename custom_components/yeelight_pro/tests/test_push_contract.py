"""Yeelight Pro push WebSocket send-side contract tests."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import pytest

from custom_components.yeelight_pro.push_contract import (
    DEFAULT_PUSH_BASE_URL,
    PUSH_HEARTBEAT_INTERVAL_SECONDS,
    PUSH_HEARTBEAT_TIMEOUT_SECONDS,
    PUSH_RECONNECT_MAX_DELAY_SECONDS,
    PUSH_RECONNECT_MIN_DELAY_SECONDS,
    PUSH_RECONNECT_MULTIPLIER,
    PushMessageBuilder,
    PushReconnectPolicy,
    build_heartbeat_message,
    build_push_url,
    build_subscribe_message,
    heartbeat_is_stale,
)


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("fake-token", f"{DEFAULT_PUSH_BASE_URL}/fake-token"),
        ("Bearer fake-token", f"{DEFAULT_PUSH_BASE_URL}/fake-token"),
        ("bearer fake-token", f"{DEFAULT_PUSH_BASE_URL}/fake-token"),
        ("BEARER fake-token", f"{DEFAULT_PUSH_BASE_URL}/fake-token"),
    ],
)
def test_build_push_url_removes_bearer_prefix(token: str, expected: str) -> None:
    """WebSocket URL 使用不含 Bearer 前缀的 token path."""
    assert build_push_url(token) == expected


def test_build_push_url_uses_custom_base_url_without_trailing_slash() -> None:
    """自定义 endpoint 不应因尾部斜杠生成双斜杠 path."""
    url = build_push_url("fake-token", base_url="wss://example.test/ws/")

    assert url == "wss://example.test/ws/fake-token"


@pytest.mark.parametrize(
    "base_url",
    [
        "http://example.test/events",
        "https://example.test/events",
        "eventsource://example.test/events",
        "text/event-stream",
    ],
)
def test_build_push_url_rejects_non_websocket_event_endpoints(base_url: str) -> None:
    """易来事件通知只有 WebSocket，push endpoint 必须是 ws:// 或 wss://。"""
    with pytest.raises(ValueError, match="require a WebSocket URL"):
        build_push_url("fake-token", base_url=base_url)


def test_build_push_url_accepts_private_http_websocket_endpoint() -> None:
    """私有部署开发环境可能是 http 根 URL，对应 ws:// push endpoint."""
    assert (
        build_push_url("fake-token", base_url="ws://private.example/ws")
        == "ws://private.example/ws/fake-token"
    )


@pytest.mark.parametrize("token", ["", "   ", "Bearer", "Bearer   "])
def test_build_push_url_rejects_empty_token(token: str) -> None:
    """空 token 必须拒绝，异常消息不包含 token 材料."""
    with pytest.raises(ValueError, match="push token is required"):
        build_push_url(token)


def test_build_subscribe_message_matches_open_platform_contract() -> None:
    """subscribe frame 精确匹配开放平台 WebSocket 文档契约."""
    assert build_subscribe_message(1, timestamp=1722133937) == {
        "id": 1,
        "method": "subscribe",
        "params": {"type": 2},
        "timestamp": 1722133937,
        "version": "1.0",
    }


def test_build_heartbeat_message_matches_open_platform_contract() -> None:
    """heartbeat frame 不包含 params 字段."""
    assert build_heartbeat_message(2, timestamp=1722133937) == {
        "id": 2,
        "method": "heartbeat",
        "timestamp": 1722133937,
        "version": "1.0",
    }


@pytest.mark.parametrize(
    "message_builder",
    [build_subscribe_message, build_heartbeat_message],
)
def test_push_messages_default_timestamp_is_seconds_int(
    message_builder: Callable[[int], dict[str, Any]],
) -> None:
    """默认 timestamp 应为当前秒级整数."""
    now = int(time.time())
    message = message_builder(1)

    assert isinstance(message["timestamp"], int)
    assert now - 2 <= message["timestamp"] <= now + 2


def test_push_message_builder_increments_ids_across_message_types() -> None:
    """builder 在 subscribe 与 heartbeat 间共享递增 id."""
    builder = PushMessageBuilder()

    subscribe = builder.next_subscribe(timestamp=1722133937)
    heartbeat = builder.next_heartbeat(timestamp=1722133938)
    next_heartbeat = builder.next_heartbeat(timestamp=1722133939)

    assert subscribe["id"] == 1
    assert heartbeat["id"] == 2
    assert next_heartbeat["id"] == 3
    assert subscribe["method"] == "subscribe"
    assert heartbeat["method"] == "heartbeat"


def test_push_heartbeat_timing_constants_match_open_platform_contract() -> None:
    """心跳时序必须匹配开放平台文档：建议 20 秒，60 秒超时."""
    assert PUSH_HEARTBEAT_INTERVAL_SECONDS == 20
    assert PUSH_HEARTBEAT_TIMEOUT_SECONDS == 60


@pytest.mark.parametrize(
    ("last_heartbeat_at", "now", "expected"),
    [
        pytest.param(None, 100.0, True, id="missing"),
        pytest.param(40.0, 99.0, False, id="before-timeout"),
        pytest.param(40.0, 100.0, True, id="at-timeout"),
        pytest.param(40.0, 101.0, True, id="after-timeout"),
    ],
)
def test_heartbeat_is_stale_uses_documented_timeout(
    last_heartbeat_at: float | None,
    now: float,
    expected: bool,
) -> None:
    """未来 transport loop 应复用同一超时判断，避免硬编码漂移."""
    assert heartbeat_is_stale(last_heartbeat_at=last_heartbeat_at, now=now) is expected


def test_push_reconnect_policy_is_bounded_by_documented_timeout() -> None:
    """未来 transport 重连退避上限不得超过开放平台心跳超时窗口."""
    assert PUSH_RECONNECT_MIN_DELAY_SECONDS == 1.0
    assert PUSH_RECONNECT_MULTIPLIER == 2.0
    assert PUSH_RECONNECT_MAX_DELAY_SECONDS == PUSH_HEARTBEAT_TIMEOUT_SECONDS

    policy = PushReconnectPolicy()

    assert [policy.delay_for_attempt(attempt) for attempt in range(1, 8)] == [
        1.0,
        2.0,
        4.0,
        8.0,
        16.0,
        32.0,
        60.0,
    ]
    assert policy.delay_for_attempt(20) == 60.0


@pytest.mark.parametrize(
    ("previous_delay", "expected"),
    [
        (None, 1.0),
        (0.0, 1.0),
        (1.0, 2.0),
        (32.0, 60.0),
        (60.0, 60.0),
    ],
)
def test_push_reconnect_policy_next_delay_is_pure_and_bounded(
    previous_delay: float | None,
    expected: float,
) -> None:
    """next_delay 只计算下一次等待时间，不调度 timer 或打开连接."""
    assert PushReconnectPolicy().next_delay(previous_delay) == expected


@pytest.mark.parametrize(
    "policy_kwargs",
    [
        {"min_delay_seconds": 0},
        {"min_delay_seconds": -1},
        {"min_delay_seconds": 2, "max_delay_seconds": 1},
        {"multiplier": 1},
    ],
)
def test_push_reconnect_policy_rejects_invalid_values(
    policy_kwargs: dict[str, float],
) -> None:
    """无效退避参数必须在 helper 边界被拒绝."""
    with pytest.raises(ValueError, match="reconnect"):
        PushReconnectPolicy(**policy_kwargs)


def test_push_reconnect_policy_requires_one_based_attempts() -> None:
    """attempt 从 1 开始，避免真实 transport 后续出现 off-by-one."""
    with pytest.raises(ValueError, match="one-based"):
        PushReconnectPolicy().delay_for_attempt(0)
