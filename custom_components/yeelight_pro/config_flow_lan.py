"""LAN-mode config-flow helpers for Yeelight Pro."""

from __future__ import annotations

from typing import Any, Protocol

from homeassistant.data_entry_flow import FlowResult

from .config_flow_helpers import (
    async_validate_lan_connection,
    flow_error_from_exception,
    lan_config_schema,
    lan_discovered_schema,
)
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_ACCOUNT_USER_ID,
    CONF_ACCOUNT_USERNAME,
    CONF_CLOUD_DOMAIN,
    CONF_CLOUD_REGION,
    CONF_CONNECTION_MODE,
    CONF_HOUSE_ID,
    CONF_HOUSE_NAME,
    CONF_LAN_GATEWAY_IP,
    CONF_LAN_GATEWAY_PORT,
    CONF_LAN_GATEWAY_PRODUCT_ID,
    CONF_LOCAL_GATEWAY_CONTROL,
    CONF_LOCAL_GATEWAY_HOST,
    CONF_LOCAL_GATEWAY_PORT,
    CONF_LOCAL_GATEWAY_PRODUCT_ID,
    CONF_OPEN_API_CLIENT_ID,
    CONF_PRIVATE_DOMAIN,
    CONF_REFRESH_TOKEN,
    CONF_SCAN_LOGIN_DEVICE,
    CONF_TOKEN_EXPIRES_IN,
    CONF_TOKEN_TYPE,
    CONNECTION_MODE_LAN,
    DEFAULT_LAN_GATEWAY_PORT,
)
from .entry_title import config_entry_title


class _LanConfigFlowProtocol(Protocol):
    """Config-flow attributes and methods required by LAN helpers."""

    _lan_gateway_ip: str
    _lan_gateway_port: int
    _lan_gateway_product_id: int | None
    _lan_discovered_list: list[tuple[str, int, str]]
    _lan_discovered_map: dict[str, tuple[str, int, int | None]]

    def async_show_form(self, **kwargs: Any) -> FlowResult:
        """Return a Home Assistant config-flow form."""

    def async_create_entry(self, **kwargs: Any) -> FlowResult:
        """Return a Home Assistant config-flow entry result."""

    async def async_set_unique_id(self, unique_id: str) -> None:
        """Set HA config-flow unique id."""

    def _abort_if_unique_id_configured(self) -> None:
        """Abort when the unique id already exists."""

    async def _create_lan_entry(self) -> FlowResult:
        """Create the LAN config-flow entry."""


class LanConfigFlowMixin:
    """Mixin implementing LAN-only config-flow steps."""

    async def async_step_lan_config(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Configure a local Yeelight Pro gateway."""
        flow = _lan_flow(self)
        errors: dict[str, str] = {}

        if user_input is not None:
            selected = str(user_input[CONF_LAN_GATEWAY_IP]).strip()
            if selected == "_manual":
                return await self.async_step_lan_manual()
            gateway = flow._lan_discovered_map.get(selected)
            if gateway is not None:
                (
                    flow._lan_gateway_ip,
                    flow._lan_gateway_port,
                    flow._lan_gateway_product_id,
                ) = gateway
                try:
                    await async_validate_lan_connection(
                        flow._lan_gateway_ip,
                        flow._lan_gateway_port,
                    )
                except Exception as err:
                    errors["base"] = flow_error_from_exception("lan config", err)
                if not errors:
                    return await flow._create_lan_entry()

        discovered = await _async_discover_lan_gateways()
        if not discovered:
            return await self.async_step_lan_manual()

        flow._lan_discovered_list = [
            (
                gateway.ip,
                DEFAULT_LAN_GATEWAY_PORT,
                f"{gateway.ip} (PID: {gateway.product_id}, MAC: {gateway.mac})",
            )
            for gateway in discovered
        ]
        flow._lan_discovered_map = {
            gateway.ip: (gateway.ip, DEFAULT_LAN_GATEWAY_PORT, gateway.product_id)
            for gateway in discovered
        }

        return flow.async_show_form(
            step_id="lan_config",
            data_schema=lan_discovered_schema(flow._lan_discovered_list),
            errors=errors,
        )

    async def async_step_lan_manual(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Configure a local Yeelight Pro gateway by address."""
        flow = _lan_flow(self)
        errors: dict[str, str] = {}

        if user_input is not None:
            flow._lan_gateway_ip = str(user_input[CONF_LAN_GATEWAY_IP]).strip()
            flow._lan_gateway_port = int(
                user_input.get(CONF_LAN_GATEWAY_PORT, DEFAULT_LAN_GATEWAY_PORT)
            )
            flow._lan_gateway_product_id = None
            try:
                await async_validate_lan_connection(
                    flow._lan_gateway_ip,
                    flow._lan_gateway_port,
                )
            except Exception as err:
                errors["base"] = flow_error_from_exception("lan config", err)
            if not errors:
                return await flow._create_lan_entry()

        return flow.async_show_form(
            step_id="lan_manual",
            data_schema=lan_config_schema(),
            errors=errors,
        )

    async def _create_lan_entry(self) -> FlowResult:
        """Create a LAN-only config entry."""
        flow = _lan_flow(self)
        unique_id = f"lan:{flow._lan_gateway_ip}:{flow._lan_gateway_port}"
        await flow.async_set_unique_id(unique_id)
        flow._abort_if_unique_id_configured()

        data = {
            CONF_CONNECTION_MODE: CONNECTION_MODE_LAN,
            CONF_CLOUD_DOMAIN: "",
            CONF_CLOUD_REGION: "",
            CONF_PRIVATE_DOMAIN: "",
            CONF_ACCESS_TOKEN: "",
            CONF_REFRESH_TOKEN: "",
            CONF_TOKEN_EXPIRES_IN: None,
            CONF_TOKEN_TYPE: "",
            CONF_HOUSE_ID: 0,
            CONF_HOUSE_NAME: "",
            CONF_OPEN_API_CLIENT_ID: "",
            CONF_ACCOUNT_USER_ID: None,
            CONF_ACCOUNT_USERNAME: "",
            CONF_SCAN_LOGIN_DEVICE: "",
            CONF_LAN_GATEWAY_IP: flow._lan_gateway_ip,
            CONF_LAN_GATEWAY_PORT: flow._lan_gateway_port,
            CONF_LAN_GATEWAY_PRODUCT_ID: flow._lan_gateway_product_id,
        }
        return flow.async_create_entry(
            title=config_entry_title(data),
            data=data,
            options={
                CONF_LOCAL_GATEWAY_CONTROL: True,
                CONF_LOCAL_GATEWAY_HOST: flow._lan_gateway_ip,
                CONF_LOCAL_GATEWAY_PORT: flow._lan_gateway_port,
                CONF_LOCAL_GATEWAY_PRODUCT_ID: flow._lan_gateway_product_id,
            },
        )


async def _async_discover_lan_gateways() -> list[Any]:
    """Return discovered LAN gateways, swallowing discovery transport failures."""
    from .lan_discovery import async_discover_all_lan_gateways

    try:
        return await async_discover_all_lan_gateways(timeout_seconds=3.0)
    except Exception:
        return []


def _lan_flow(flow: object) -> _LanConfigFlowProtocol:
    return flow  # type: ignore[return-value]
