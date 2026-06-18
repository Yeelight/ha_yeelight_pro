"""Private-deployment config-flow helpers for Yeelight Pro."""

from __future__ import annotations

from typing import Any, Protocol

from homeassistant.data_entry_flow import FlowResult

from .config_flow_helpers import (
    flow_error_from_exception,
    private_config_schema,
)
from .const import (
    CONF_PRIVATE_DOMAIN,
    CONF_PRIVATE_PUSH_DOMAIN,
)
from .deployment_urls import deployment_push_base_url, deployment_root_url


class _PrivateConfigFlowProtocol(Protocol):
    """Config-flow attributes and methods required by private helpers."""

    _domain: str | None
    _private_push_domain: str

    def async_show_form(self, **kwargs: Any) -> FlowResult:
        """Return a Home Assistant config-flow form."""

    async def async_step_cloud_auth_method(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Continue into the shared cloud/private auth method flow."""


class PrivateConfigFlowMixin:
    """Mixin implementing private deployment URL configuration."""

    async def async_step_private_config(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Configure private deployment API and optional push endpoints."""
        flow = _private_flow(self)
        errors: dict[str, str] = {}

        if user_input is not None:
            domain = str(user_input.get(CONF_PRIVATE_DOMAIN, "")).strip()
            if not domain:
                errors[CONF_PRIVATE_DOMAIN] = "required"
            else:
                try:
                    flow._domain = deployment_root_url(domain)
                    push_domain = str(
                        user_input.get(CONF_PRIVATE_PUSH_DOMAIN, "")
                    ).strip()
                    flow._private_push_domain = (
                        deployment_push_base_url(push_domain) if push_domain else ""
                    )
                    return await flow.async_step_cloud_auth_method()
                except Exception as err:
                    errors["base"] = flow_error_from_exception("private config", err)

        return flow.async_show_form(
            step_id="private_config",
            data_schema=private_config_schema(),
            errors=errors,
        )


def _private_flow(flow: object) -> _PrivateConfigFlowProtocol:
    return flow  # type: ignore[return-value]
