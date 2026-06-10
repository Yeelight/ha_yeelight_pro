"""Config-flow reauthentication helpers for Yeelight Pro."""

from __future__ import annotations

from typing import Any, Protocol, cast

from homeassistant.data_entry_flow import FlowResult
from homeassistant.core import HomeAssistant

from .config_flow_account import account_identity
from .config_flow_helpers import (
    async_validate_auth,
    flow_error_from_exception,
    reauth_confirm_schema,
)
from .config_flow_scan_login import ScanLoginFlowState
from .config_flow_scan_login_region import scan_login_token_matches_region
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_ACCOUNT_USER_ID,
    CONF_ACCOUNT_USERNAME,
    CONF_CLOUD_DOMAIN,
    CONF_CLOUD_REGION,
    CONF_CONNECTION_MODE,
    CONF_OAUTH_CLIENT_ID,
    CONF_PRIVATE_DOMAIN,
    CONF_REFRESH_TOKEN,
    CONF_SCAN_LOGIN_DEVICE,
    CONF_TOKEN_EXPIRES_IN,
    CONF_TOKEN_TYPE,
    CONNECTION_MODE_CLOUD,
    DEFAULT_CLOUD_REGION,
)
from .entry_migration import normalize_entry_data


class _ReauthFlowProtocol(Protocol):
    """Config-flow attributes and methods required by reauth helpers."""

    hass: HomeAssistant
    _access_token: str | None
    _account_user_id: int | None
    _account_username: str
    _cloud_region: str
    _connection_mode: str | None
    _domain: str | None
    _open_api_client_id: str
    _reauth_entry_data: dict[str, Any]
    _reauth_in_progress: bool
    _refresh_token: str
    _scan_login_device: str
    _scan_login_state: ScanLoginFlowState
    _token_expires_in: int | None
    _token_type: str

    async def async_step_cloud_scan_login(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Show or poll cloud scan-login."""

    async def async_step_reauth_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Show manual token reauth."""

    def async_show_form(self, **kwargs: Any) -> FlowResult:
        """Return a Home Assistant config-flow form."""

    def async_show_progress_done(self, **kwargs: Any) -> FlowResult:
        """Return a Home Assistant config-flow progress-done result."""

    def async_update_reload_and_abort(self, *args: Any, **kwargs: Any) -> FlowResult:
        """Update the config entry and abort the flow."""

    def _get_reauth_entry(self) -> Any:
        """Return the Home Assistant config entry being reauthenticated."""


class ReauthConfigFlowMixin:
    """Mixin implementing cloud scan-login and private token reauth paths."""

    async def async_step_reauth(
        self,
        entry_data: dict[str, Any],
    ) -> FlowResult:
        """Start reauth, using scan-login for cloud entries."""
        flow = _reauth_flow(self)
        flow._reauth_entry_data = normalize_entry_data(entry_data)
        flow._connection_mode = flow._reauth_entry_data[CONF_CONNECTION_MODE]
        flow._cloud_region = flow._reauth_entry_data.get(
            CONF_CLOUD_REGION,
            DEFAULT_CLOUD_REGION,
        )
        flow._domain = flow._reauth_entry_data[
            CONF_CLOUD_DOMAIN
            if flow._connection_mode == CONNECTION_MODE_CLOUD
            else CONF_PRIVATE_DOMAIN
        ]
        if flow._connection_mode == CONNECTION_MODE_CLOUD:
            flow._reauth_in_progress = True
            flow._scan_login_device = flow._reauth_entry_data.get(
                CONF_SCAN_LOGIN_DEVICE,
                "",
            )
            return await flow.async_step_cloud_scan_login()
        return await flow.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Private deployment reauth keeps the manual Access Token form."""
        flow = _reauth_flow(self)
        errors: dict[str, str] = {}

        if user_input is not None:
            new_token = user_input[CONF_ACCESS_TOKEN]
            try:
                await async_validate_auth(
                    flow.hass,
                    domain=flow._domain or "",
                    access_token=new_token,
                    client_id=flow._reauth_entry_data.get(CONF_OAUTH_CLIENT_ID, ""),
                )
            except Exception as err:
                errors["base"] = flow_error_from_exception("reauth", err)
            else:
                entry = flow._get_reauth_entry()
                new_data = normalize_entry_data({
                    **entry.data,
                    CONF_ACCESS_TOKEN: new_token,
                })
                return flow.async_update_reload_and_abort(
                    entry,
                    data=new_data,
                )

        return flow.async_show_form(
            step_id="reauth_confirm",
            data_schema=reauth_confirm_schema(),
            errors=errors,
            description_placeholders={
                "domain": flow._domain,
            },
        )

    async def _async_finish_scan_login(self) -> FlowResult:
        """Finish scan-login for initial setup or cloud reauth."""
        flow = _reauth_flow(self)
        if not flow._reauth_in_progress:
            return flow.async_show_progress_done(next_step_id="cloud_houses")
        if not _same_reauth_account(
            flow._reauth_entry_data,
            account_user_id=flow._account_user_id,
            username=flow._account_username,
            client_id=flow._open_api_client_id,
            access_token=flow._access_token,
        ) or not _same_reauth_region(flow):
            flow._scan_login_state.qr_code = None
            flow._scan_login_state.poll_count = 0
            flow._scan_login_state.last_error = "invalid_auth"
            return flow.async_show_progress_done(next_step_id="cloud_scan_login")

        entry = flow._get_reauth_entry()
        new_data = normalize_entry_data({
            **entry.data,
            CONF_CLOUD_DOMAIN: flow._domain,
            CONF_CLOUD_REGION: flow._cloud_region,
            CONF_ACCESS_TOKEN: flow._access_token,
            CONF_REFRESH_TOKEN: flow._refresh_token,
            CONF_TOKEN_EXPIRES_IN: flow._token_expires_in,
            CONF_TOKEN_TYPE: flow._token_type,
            CONF_OAUTH_CLIENT_ID: flow._open_api_client_id,
            CONF_ACCOUNT_USER_ID: flow._account_user_id,
            CONF_ACCOUNT_USERNAME: flow._account_username,
            CONF_SCAN_LOGIN_DEVICE: flow._scan_login_device,
        })
        flow._reauth_in_progress = False
        return flow.async_update_reload_and_abort(
            entry,
            data=new_data,
        )


def _reauth_flow(value: Any) -> _ReauthFlowProtocol:
    """Return the config-flow object narrowed to the reauth protocol."""
    return cast(_ReauthFlowProtocol, value)


def _same_reauth_account(
    entry_data: dict[str, Any],
    *,
    account_user_id: int | None,
    username: str,
    client_id: str,
    access_token: str | None,
) -> bool:
    """Return whether scan-login credentials belong to the current entry account."""
    expected = _entry_account_identity(entry_data)
    if expected is None:
        return True
    return expected == _account_identity(
        account_user_id=account_user_id,
        username=username,
        client_id=client_id,
        access_token=access_token,
    )


def _same_reauth_region(flow: _ReauthFlowProtocol) -> bool:
    """Return whether scan-login token region can update this cloud entry."""
    qr_code = flow._scan_login_state.qr_code
    token = qr_code.token if qr_code is not None else None
    return scan_login_token_matches_region(token, flow._cloud_region)


def _entry_account_identity(entry_data: dict[str, Any]) -> tuple[str, str] | None:
    """Return the strongest stored account identity for a config entry."""
    return _account_identity(
        account_user_id=entry_data.get(CONF_ACCOUNT_USER_ID),
        username=entry_data.get(CONF_ACCOUNT_USERNAME, ""),
        client_id=entry_data.get(CONF_OAUTH_CLIENT_ID, ""),
        access_token=entry_data.get(CONF_ACCESS_TOKEN, ""),
    )


def _account_identity(
    *,
    account_user_id: int | None,
    username: Any,
    client_id: Any,
    access_token: Any,
) -> tuple[str, str] | None:
    """Return account identity in the same priority used by unique_id."""
    return account_identity(
        account_user_id=account_user_id,
        username=username,
        client_id=client_id,
        access_token=access_token,
    )


__all__ = [
    "ReauthConfigFlowMixin",
]
