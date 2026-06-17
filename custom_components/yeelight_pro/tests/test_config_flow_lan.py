"""LAN config-flow contract tests."""

from __future__ import annotations

from typing import Any

import pytest

from custom_components.yeelight_pro.config_flow_lan import LanConfigFlowMixin
from custom_components.yeelight_pro.const import (
    CONF_LAN_GATEWAY_IP,
    CONF_LAN_GATEWAY_PRODUCT_ID,
    CONF_LAN_GATEWAY_PORT,
    CONF_LOCAL_GATEWAY_PRODUCT_ID,
    CONF_PRIVATE_PUSH_DOMAIN,
    CONF_PRIVATE_PUSH_PROXY,
    LAN_GATEWAY_PRODUCT_ID_GATEWAY,
    LAN_GATEWAY_PRODUCT_ID_WIFI_PANEL,
)


@pytest.mark.asyncio
async def test_create_lan_entry_preserves_discovered_product_id() -> None:
    """自动发现到 pid=2 时，entry data/options 应保留端点产品类型。"""
    flow = _LanFlowDouble()

    result = await flow._create_lan_entry()

    assert result["type"] == "create_entry"
    assert result["data"][CONF_LAN_GATEWAY_PRODUCT_ID] == 2
    assert result["data"][CONF_PRIVATE_PUSH_DOMAIN] == ""
    assert result["data"][CONF_PRIVATE_PUSH_PROXY] == ""
    assert result["options"][CONF_LOCAL_GATEWAY_PRODUCT_ID] == 2


@pytest.mark.asyncio
async def test_manual_lan_entry_preserves_selected_wifi_panel_product_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """手动输入全面屏 IP 时也必须保存 pid=2 以选择 device_* 方法族。"""
    flow = _LanFlowDouble()
    flow._lan_gateway_product_id = None
    monkeypatch.setattr(
        "custom_components.yeelight_pro.config_flow_lan.async_validate_lan_connection",
        _async_noop_validate,
    )

    result = await flow.async_step_lan_manual(
        {
            CONF_LAN_GATEWAY_IP: "192.168.1.102",
            CONF_LAN_GATEWAY_PORT: 65443,
            CONF_LAN_GATEWAY_PRODUCT_ID: str(LAN_GATEWAY_PRODUCT_ID_WIFI_PANEL),
        }
    )

    assert result["type"] == "create_entry"
    assert result["data"][CONF_LAN_GATEWAY_PRODUCT_ID] == LAN_GATEWAY_PRODUCT_ID_WIFI_PANEL
    assert (
        result["options"][CONF_LOCAL_GATEWAY_PRODUCT_ID]
        == LAN_GATEWAY_PRODUCT_ID_WIFI_PANEL
    )


@pytest.mark.asyncio
async def test_manual_lan_entry_defaults_to_gateway_product_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """未选择产品类型时按协议默认普通 Pro 网关 pid=1。"""
    flow = _LanFlowDouble()
    flow._lan_gateway_product_id = None
    monkeypatch.setattr(
        "custom_components.yeelight_pro.config_flow_lan.async_validate_lan_connection",
        _async_noop_validate,
    )

    result = await flow.async_step_lan_manual(
        {
            CONF_LAN_GATEWAY_IP: "192.168.1.103",
            CONF_LAN_GATEWAY_PORT: 65443,
        }
    )

    assert result["type"] == "create_entry"
    assert result["data"][CONF_LAN_GATEWAY_PRODUCT_ID] == LAN_GATEWAY_PRODUCT_ID_GATEWAY
    assert (
        result["options"][CONF_LOCAL_GATEWAY_PRODUCT_ID]
        == LAN_GATEWAY_PRODUCT_ID_GATEWAY
    )


async def _async_noop_validate(host: str, port: int) -> None:
    """Avoid opening a real TCP connection in config-flow unit tests."""


class _LanFlowDouble(LanConfigFlowMixin):
    """Small config-flow double for LAN entry creation."""

    def __init__(self) -> None:
        self._lan_gateway_ip = "192.168.1.102"
        self._lan_gateway_port = 65443
        self._lan_gateway_product_id: int | None = 2
        self.unique_id: str | None = None

    async def async_set_unique_id(self, unique_id: str) -> None:
        """Record the generated unique id."""
        self.unique_id = unique_id

    def _abort_if_unique_id_configured(self) -> None:
        """No-op duplicate guard for this unit test."""

    def async_create_entry(self, **kwargs: Any) -> dict[str, Any]:
        """Return a simple create-entry result."""
        return {"type": "create_entry", **kwargs}

    def async_show_form(self, **kwargs: Any) -> dict[str, Any]:
        """Return a simple form result."""
        return {"type": "form", **kwargs}
