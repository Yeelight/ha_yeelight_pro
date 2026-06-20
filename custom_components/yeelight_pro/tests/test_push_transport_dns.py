"""DNS utility tests for the Yeelight Pro WebSocket transport."""

from __future__ import annotations

import pytest

from custom_components.yeelight_pro import push_transport_dns


@pytest.mark.asyncio
async def test_fake_ip_detection_matches_clash_docker_range() -> None:
    """fake-ip 检测只覆盖 Clash/Docker 常见 198.18.0.0/15 网段。"""
    assert push_transport_dns.is_fake_ip_address("198.18.0.8") is True
    assert push_transport_dns.is_fake_ip_address("198.19.255.254") is True
    assert push_transport_dns.is_fake_ip_address("198.20.0.1") is False
    assert push_transport_dns.is_fake_ip_address("203.0.113.8") is False
    assert push_transport_dns.is_fake_ip_address("ws-test.yeedev.com") is False
