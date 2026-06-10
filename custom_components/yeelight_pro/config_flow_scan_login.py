"""Config-flow helpers for Yeelight APP scan login."""
from __future__ import annotations

import asyncio
from typing import Any, Protocol, cast

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_ACCESS_TOKEN,
    CONF_ACCOUNT_USER_ID,
    CONF_ACCOUNT_USERNAME,
    CONF_OAUTH_CLIENT_ID,
    CONF_REFRESH_TOKEN,
    CONF_SCAN_LOGIN_REFRESH,
    CONF_TOKEN_EXPIRES_IN,
    CONF_TOKEN_TYPE,
)
from .config_flow_helpers import cloud_domain_for_region, flow_error_from_exception
from .config_flow_scan_login_helpers import (
    SCAN_LOGIN_POLL_INTERVAL_SECONDS,
    ScanLoginFlowState,
    _async_create_task,
    async_poll_scan_login_until_login,
    async_scan_login_device_id,
    cloud_scan_login_schema,
    cloud_scan_login_schema_for_qrcode,
    scan_login_account_key,
    scan_login_description_placeholders,
    scan_login_entry_data,
    scan_login_needs_refresh,
)
from .config_flow_scan_login_region import scan_login_token_matches_region
from .scan_login_contract import ScanLoginStatus, YeelightScanLoginQrCode


class _ScanLoginFlowProtocol(Protocol):
    """Config-flow attributes required by scan-login helpers."""

    hass: HomeAssistant
    _access_token: str | None
    _account_user_id: int | None
    _account_username: str
    _cloud_region: str
    _domain: str | None
    _open_api_client_id: str
    _refresh_token: str
    _scan_login_account_key: str
    _scan_login_device: str
    _scan_login_poll_interval_seconds: float
    _scan_login_poll_task_ref: asyncio.Future[YeelightScanLoginQrCode] | None
    _scan_login_state: ScanLoginFlowState
    _token_expires_in: int | None
    _token_type: str

    def async_show_form(self, **kwargs: Any) -> FlowResult:
        """Return a Home Assistant config-flow form."""

    def async_show_progress(self, **kwargs: Any) -> FlowResult:
        """Return a Home Assistant config-flow progress result."""

    def async_show_progress_done(self, **kwargs: Any) -> FlowResult:
        """Return a Home Assistant config-flow progress-done result."""

    async def _async_finish_scan_login(self) -> FlowResult:
        """Finish scan-login after token metadata is stored."""
        ...


class ScanLoginConfigFlowMixin:
    """Mixin implementing Yeelight APP scan-login config-flow steps."""

    _scan_login_poll_interval_seconds = SCAN_LOGIN_POLL_INTERVAL_SECONDS

    async def async_step_cloud_scan_login(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Show QR code and route submitted forms into continuous polling."""
        flow = self._scan_login_flow()
        errors: dict[str, str] = {}
        refresh = bool(user_input and user_input.get(CONF_SCAN_LOGIN_REFRESH))
        try:
            await self._async_ensure_scan_login_qrcode(
                refresh=refresh
            )
            qr_code = flow._scan_login_state.qr_code
            if user_input is not None and not refresh and qr_code is not None:
                if not qr_code.pollable:
                    errors["base"] = "scan_login_expired"
                else:
                    return await self.async_step_cloud_scan_login_wait()
        except Exception as err:
            errors["base"] = flow_error_from_exception("cloud scan login", err)

        if flow._scan_login_state.last_error:
            errors["base"] = flow._scan_login_state.last_error
            flow._scan_login_state.last_error = None

        return flow.async_show_form(
            step_id="cloud_scan_login",
            data_schema=cloud_scan_login_schema_for_qrcode(
                self._scan_login_qrcode_content()
            ),
            errors=errors,
            description_placeholders=scan_login_description_placeholders(
                flow._scan_login_state,
            ),
        )

    async def async_step_cloud_scan_login_wait(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Continuously poll the QR code until the APP grants or it expires."""
        flow = self._scan_login_flow()
        task = self._scan_login_poll_task()
        if task is None:
            qr_code = flow._scan_login_state.qr_code
            if qr_code is None:
                return flow.async_show_progress_done(next_step_id="cloud_scan_login")
            task = self._start_scan_login_poll_task(qr_code)

        if not task.done():
            return flow.async_show_progress(
                step_id="cloud_scan_login_wait",
                progress_action="cloud_scan_login_wait",
                description_placeholders=scan_login_description_placeholders(
                    flow._scan_login_state,
                ),
                progress_task=task,
            )

        flow._scan_login_poll_task_ref = None
        try:
            qr_code = await task
        except TimeoutError:
            flow._scan_login_state.last_error = "scan_login_expired"
            return flow.async_show_progress_done(next_step_id="cloud_scan_login")
        except Exception as err:
            flow._scan_login_state.last_error = flow_error_from_exception(
                "cloud scan login polling",
                err,
            )
            return flow.async_show_progress_done(next_step_id="cloud_scan_login")

        flow._scan_login_state.qr_code = qr_code
        if qr_code.status == ScanLoginStatus.LOGIN:
            if not scan_login_token_matches_region(qr_code.token, flow._cloud_region):
                _reset_scan_login_with_invalid_auth(flow)
                return flow.async_show_progress_done(next_step_id="cloud_scan_login")
            self._store_scan_login_token(qr_code.token)
            return await flow._async_finish_scan_login()
        return flow.async_show_progress_done(next_step_id="cloud_scan_login")

    async def _async_ensure_scan_login_qrcode(self, *, refresh: bool) -> None:
        """Create or refresh the current five-minute scan-login QR code."""
        flow = self._scan_login_flow()
        if not flow._scan_login_device:
            flow._scan_login_device = await async_scan_login_device_id(flow.hass)
        if refresh:
            self._cancel_scan_login_poll_task()
        if refresh or scan_login_needs_refresh(flow._scan_login_state.qr_code):
            flow._scan_login_state.qr_code = (
                await self._scan_login_client().create_scan_login_qrcode(
                    region=flow._cloud_region,
                    device=flow._scan_login_device,
                )
            )
            flow._scan_login_state.poll_count = 0

    def _scan_login_poll_task(
        self,
    ) -> asyncio.Future[YeelightScanLoginQrCode] | None:
        """Return the active scan-login polling task if one exists."""
        task = self._scan_login_flow()._scan_login_poll_task_ref
        return task if isinstance(task, asyncio.Future) else None

    def _start_scan_login_poll_task(
        self,
        qr_code: YeelightScanLoginQrCode,
    ) -> asyncio.Task[YeelightScanLoginQrCode]:
        """Start the QR polling task using Home Assistant's task helper."""
        flow = self._scan_login_flow()
        coro = async_poll_scan_login_until_login(
            self._scan_login_client(),
            region=flow._cloud_region,
            qr_code=qr_code,
            state=flow._scan_login_state,
            poll_interval_seconds=flow._scan_login_poll_interval_seconds,
        )
        task = _async_create_task(flow.hass, coro)
        flow._scan_login_poll_task_ref = task
        return task

    def _cancel_scan_login_poll_task(self) -> None:
        """Cancel stale scan-login polling when a new QR code is requested."""
        flow = self._scan_login_flow()
        task = self._scan_login_poll_task()
        if task is not None and not task.done():
            task.cancel()
        flow._scan_login_poll_task_ref = None

    def _scan_login_client(self):
        """Return a Yeelight client for the account scan-login API."""
        flow = self._scan_login_flow()
        from homeassistant.helpers.aiohttp_client import async_get_clientsession

        from .core.client import YeelightProClient

        return YeelightProClient(
            domain=flow._domain or cloud_domain_for_region(flow._cloud_region),
            access_token="",
            session=async_get_clientsession(flow.hass),
        )

    def _scan_login_qrcode_content(self) -> str:
        """Return QR content for Home Assistant's native QR selector."""
        qr_code = self._scan_login_flow()._scan_login_state.qr_code
        return qr_code.qrcode_content if qr_code is not None else ""

    def _store_scan_login_token(self, token: Any) -> None:
        """Persist scan-login token metadata into the config-flow state."""
        flow = self._scan_login_flow()
        if token is None:
            raise ValueError("Yeelight scan-login token is required")
        data = scan_login_entry_data(token, device=flow._scan_login_device)
        flow._access_token = data[CONF_ACCESS_TOKEN]
        flow._refresh_token = data.get(CONF_REFRESH_TOKEN, "")
        flow._token_expires_in = data.get(CONF_TOKEN_EXPIRES_IN)
        flow._token_type = data.get(CONF_TOKEN_TYPE, "")
        flow._open_api_client_id = data.get(CONF_OAUTH_CLIENT_ID, "")
        flow._account_user_id = data.get(CONF_ACCOUNT_USER_ID)
        flow._account_username = data.get(CONF_ACCOUNT_USERNAME, "")
        flow._scan_login_account_key = scan_login_account_key(token)

    def _scan_login_flow(self) -> _ScanLoginFlowProtocol:
        """Return self narrowed to the config-flow protocol."""
        return cast(_ScanLoginFlowProtocol, self)


def _reset_scan_login_with_invalid_auth(flow: _ScanLoginFlowProtocol) -> None:
    """Reset region/account-invalid scan-login state before returning to QR step."""
    flow._scan_login_state.qr_code = None
    flow._scan_login_state.poll_count = 0
    flow._scan_login_state.last_error = "invalid_auth"


__all__ = [
    "SCAN_LOGIN_POLL_INTERVAL_SECONDS",
    "ScanLoginConfigFlowMixin",
    "ScanLoginFlowState",
    "async_poll_scan_login_until_login",
    "async_scan_login_device_id",
    "cloud_scan_login_schema",
    "cloud_scan_login_schema_for_qrcode",
    "scan_login_account_key",
    "scan_login_description_placeholders",
    "scan_login_entry_data",
    "scan_login_needs_refresh",
]
