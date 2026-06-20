"""Deployment URL derivation tests."""
from __future__ import annotations

from custom_components.yeelight_pro.deployment_urls import (
    deployment_account_base_url,
    deployment_iot_base_url,
    deployment_private_push_base_url,
    deployment_push_base_url,
    deployment_root_url,
)


def test_deployment_root_url_accepts_root_and_adds_default_scheme() -> None:
    """私有部署用户输入根 URL 时应规范化为带协议的根地址."""
    assert deployment_root_url("private.example") == "https://private.example"
    assert deployment_root_url(" http://private.example/ ") == "http://private.example"


def test_deployment_root_url_accepts_legacy_api_prefixes() -> None:
    """旧版 /apis/iot 或 /apis/account 前缀应剥离为部署根 URL."""
    assert (
        deployment_root_url("http://private.example/apis/iot/")
        == "http://private.example"
    )
    assert (
        deployment_root_url("https://private.example/apis/account")
        == "https://private.example"
    )


def test_deployment_api_base_urls_are_derived_from_root() -> None:
    """Open API 和 Account API 应从同一个部署根 URL 派生."""
    assert (
        deployment_iot_base_url("https://private.example")
        == "https://private.example/apis/iot"
    )
    assert (
        deployment_account_base_url("https://private.example/apis/iot")
        == "https://private.example/apis/account"
    )


def test_deployment_push_base_url_is_derived_from_root() -> None:
    """私有部署 WebSocket push endpoint 应规范化为 ws path."""
    assert (
        deployment_push_base_url("private.example")
        == "wss://private.example/ws"
    )
    assert (
        deployment_push_base_url("https://push.private.example")
        == "wss://push.private.example/ws"
    )
    assert (
        deployment_push_base_url("wss://push.private.example/ws")
        == "wss://push.private.example/ws"
    )
    assert (
        deployment_push_base_url("http://push.private.example/apis/iot")
        == "ws://push.private.example/ws"
    )
    assert (
        deployment_push_base_url("192.168.8.9:7779")
        == "ws://192.168.8.9:7779/ws"
    )
    assert (
        deployment_push_base_url("localhost:7779")
        == "ws://localhost:7779/ws"
    )


def test_deployment_push_base_url_uses_known_private_dev_host() -> None:
    """Current private dev API host uses the direct dev push endpoint."""
    assert (
        deployment_push_base_url("api-dev.yeedev.com")
        == "ws://192.168.1.202:7779/ws"
    )
    assert (
        deployment_push_base_url("ws-dev.yeedev.com")
        == "ws://192.168.1.202:7779/ws"
    )
    assert (
        deployment_push_base_url("https://api-dev.yeedev.com/apis/iot")
        == "ws://192.168.1.202:7779/ws"
    )
    assert (
        deployment_push_base_url("192.168.1.202:7779")
        == "ws://192.168.1.202:7779/ws"
    )


def test_deployment_push_base_url_uses_known_private_test_host() -> None:
    """Current private test API host uses a direct private test push endpoint."""
    assert (
        deployment_push_base_url("api-test.yeedev.com")
        == "ws://192.168.0.89:7779/ws"
    )
    assert (
        deployment_push_base_url("ws-test.yeedev.com")
        == "ws://192.168.0.89:7779/ws"
    )
    assert (
        deployment_push_base_url("http://api-test.yeedev.com/apis/iot")
        == "ws://192.168.0.89:7779/ws"
    )
    assert (
        deployment_push_base_url("ws://192.168.0.89:7779/ws")
        == "ws://192.168.0.89:7779/ws"
    )


def test_deployment_private_push_base_url_repairs_known_cross_route() -> None:
    """Known internal API hosts must not keep a push URL from another lab route."""
    assert (
        deployment_private_push_base_url(
            "http://api-dev.yeedev.com",
            "ws://192.168.0.89:7779/ws",
        )
        == "ws://192.168.1.202:7779/ws"
    )
    assert (
        deployment_private_push_base_url(
            "http://api-test.yeedev.com",
            "ws://192.168.1.202:7779/ws",
        )
        == "ws://192.168.0.89:7779/ws"
    )


def test_deployment_private_push_base_url_preserves_custom_override() -> None:
    """Custom private deployments keep the user-provided WebSocket endpoint."""
    assert (
        deployment_private_push_base_url(
            "https://private.example",
            "ws://192.168.8.9:7779",
        )
        == "ws://192.168.8.9:7779/ws"
    )
