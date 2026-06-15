"""LAN config-flow contract tests."""

from __future__ import annotations

from typing import Any

import pytest

from custom_components.yeelight_pro.config_flow_lan import LanConfigFlowMixin
from custom_components.yeelight_pro.const import (
    CONF_LAN_GATEWAY_PRODUCT_ID,
    CONF_LOCAL_GATEWAY_PRODUCT_ID,
)


@pytest.mark.asyncio
async def test_create_lan_entry_preserves_discovered_product_id() -> None:
    """自动发现到 pid=2 时，entry data/options 应保留端点产品类型。"""
    flow = _LanFlowDouble()

    result = await flow._create_lan_entry()

    assert result["type"] == "create_entry"
    assert result["data"][CONF_LAN_GATEWAY_PRODUCT_ID] == 2
    assert result["options"][CONF_LOCAL_GATEWAY_PRODUCT_ID] == 2


class _LanFlowDouble(LanConfigFlowMixin):
    """Small config-flow double for LAN entry creation."""

    def __init__(self) -> None:
        self._lan_gateway_ip = "192.168.1.102"
        self._lan_gateway_port = 65443
        self._lan_gateway_product_id = 2
        self.unique_id: str | None = None

    async def async_set_unique_id(self, unique_id: str) -> None:
        """Record the generated unique id."""
        self.unique_id = unique_id

    def _abort_if_unique_id_configured(self) -> None:
        """No-op duplicate guard for this unit test."""

    def async_create_entry(self, **kwargs: Any) -> dict[str, Any]:
        """Return a simple create-entry result."""
        return {"type": "create_entry", **kwargs}
