"""Config flow for the Yeelight Pro integration."""
from __future__ import annotations

from typing import Any

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_ACCESS_TOKEN,
    CONF_ACCOUNT_USER_ID,
    CONF_ACCOUNT_USERNAME,
    CONF_CLOUD_AUTH_METHOD,
    CONF_CONNECTION_MODE,
    CONF_CLOUD_DOMAIN,
    CONF_CLOUD_REGION,
    CONF_DEVICE_IMPORT_FILTER,
    CONF_HOUSE_ID,
    CONF_HOUSE_NAME,
    CONF_OPEN_API_CLIENT_ID,
    CONF_PRIVATE_DOMAIN,
    CONF_REFRESH_TOKEN,
    CONF_SCAN_LOGIN_DEVICE,
    CONF_TOKEN_EXPIRES_IN,
    CONF_TOKEN_TYPE,
    CLOUD_AUTH_METHOD_SCAN_LOGIN,
    CONNECTION_MODE_CLOUD,
    CONNECTION_MODE_PRIVATE,
    DEFAULT_CLOUD_REGION,
    DOMAIN,
)
from .config_flow_account import (
    UNKNOWN_ACCOUNT_KEY,
    account_identity,
    account_key_from_identity,
)
from .config_flow_helpers import (
    async_load_house_choices,
    async_validate_auth,
    cloud_auth_method_schema,
    cloud_auth_schema,
    cloud_houses_schema,
    cloud_domain_for_region,
    cloud_region_schema,
    flow_error_from_exception,
    private_config_schema,
    user_schema,
)
from .config_flow_device_picker import (
    DevicePickerChoice,
    async_load_device_choices,
    cloud_devices_schema,
    device_import_filter_for_selected_devices,
    selected_device_ids_from_input,
)
from .config_flow_scan_login import (
    ScanLoginConfigFlowMixin,
    ScanLoginFlowState,
)
from .config_flow_reauth import ReauthConfigFlowMixin
from .entry_migration import (
    ENTRY_MINOR_VERSION,
    ENTRY_VERSION,
)
from .entry_title import config_entry_title
from .house_metadata import house_name_from_choice
from .options_flow import YeelightProOptionsFlow


class YeelightProConfigFlow(
    ReauthConfigFlowMixin,
    ScanLoginConfigFlowMixin,
    config_entries.ConfigFlow,
    domain=DOMAIN,
):  # type: ignore[call-arg]
    """Yeelight Pro 配置流程."""

    VERSION = ENTRY_VERSION
    MINOR_VERSION = ENTRY_MINOR_VERSION

    def __init__(self):
        """初始化配置流程."""
        self._connection_mode = None
        self._domain = None
        self._access_token = None
        self._refresh_token = ""
        self._token_expires_in: int | None = None
        self._token_type = ""
        self._house_id = None
        self._house_name = ""
        self._cloud_region = DEFAULT_CLOUD_REGION
        self._cloud_auth_method = CLOUD_AUTH_METHOD_SCAN_LOGIN
        self._account_user_id: int | None = None
        self._account_username = ""
        self._scan_login_device = ""
        self._scan_login_state = ScanLoginFlowState()
        self._scan_login_poll_task_ref = None
        self._scan_login_account_key = UNKNOWN_ACCOUNT_KEY
        self._open_api_client_id = ""
        self._device_choices: tuple[DevicePickerChoice, ...] = ()
        self._house_choices: dict[Any, str] = {}
        self._selected_device_ids: list[str] = []
        self._reauth_entry_data: dict[str, Any] = {}
        self._reauth_in_progress = False

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """用户初始步骤：选择连接模式."""
        if user_input is not None:
            self._connection_mode = user_input[CONF_CONNECTION_MODE]

            if self._connection_mode == CONNECTION_MODE_CLOUD:
                return await self.async_step_cloud_region()
            else:
                return await self.async_step_private_config()

        return self.async_show_form(
            step_id="user",
            data_schema=user_schema(),
        )

    async def async_step_cloud_region(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """云端区域选择步骤."""
        if user_input is not None:
            self._cloud_region = user_input[CONF_CLOUD_REGION]
            self._domain = cloud_domain_for_region(self._cloud_region)
            return await self.async_step_cloud_auth_method()

        return self.async_show_form(
            step_id="cloud_region",
            data_schema=cloud_region_schema(),
        )

    async def async_step_cloud_auth_method(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """云端认证方式选择步骤."""
        if user_input is not None:
            self._cloud_auth_method = user_input[CONF_CLOUD_AUTH_METHOD]
            if self._cloud_auth_method == CLOUD_AUTH_METHOD_SCAN_LOGIN:
                return await self.async_step_cloud_scan_login()
            return await self.async_step_cloud_auth()

        return self.async_show_form(
            step_id="cloud_auth_method",
            data_schema=cloud_auth_method_schema(),
        )

    async def async_step_cloud_auth(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """云端认证步骤."""
        errors = {}

        if user_input is not None:
            try:
                self._access_token = user_input[CONF_ACCESS_TOKEN]
                await async_validate_auth(
                    self.hass,
                    domain=self._domain,
                    access_token=self._access_token,
                )
                return await self.async_step_cloud_houses()
            except Exception as err:
                errors["base"] = flow_error_from_exception("cloud auth", err)

        return self.async_show_form(
            step_id="cloud_auth",
            data_schema=cloud_auth_schema(),
            errors=errors,
            description_placeholders={
                "domain": self._domain,
            },
        )

    async def async_step_cloud_houses(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """云端家庭选择步骤."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._house_id = user_input[CONF_HOUSE_ID]
            self._house_name = house_name_from_choice(
                self._house_choices,
                self._house_id,
            )
            return await self.async_step_cloud_devices()

        try:
            house_choices = await async_load_house_choices(
                self.hass,
                domain=self._domain,
                access_token=self._access_token,
                client_id=self._open_api_client_id,
            )
        except Exception as err:
            errors["base"] = flow_error_from_exception("cloud houses", err)
            house_choices = {}
        self._house_choices = dict(house_choices)

        if not house_choices and not errors:
            return self.async_abort(reason="no_houses_found")

        return self.async_show_form(
            step_id="cloud_houses",
            data_schema=cloud_houses_schema(house_choices),
            errors=errors,
        )

    async def async_step_cloud_devices(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """云端真实设备选择步骤."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._selected_device_ids = selected_device_ids_from_input(
                user_input,
                self._device_choices,
            )
            return await self._create_entry()

        try:
            self._device_choices = await async_load_device_choices(
                self.hass,
                domain=self._domain,
                access_token=self._access_token,
                house_id=self._house_id,
                client_id=self._open_api_client_id,
            )
        except Exception as err:
            errors["base"] = flow_error_from_exception("cloud devices", err)
            self._device_choices = ()

        self._selected_device_ids = selected_device_ids_from_input(
            None,
            self._device_choices,
        )
        return self.async_show_form(
            step_id="cloud_devices",
            data_schema=cloud_devices_schema(
                self._device_choices,
                self._selected_device_ids,
            ),
            errors=errors,
        )

    async def async_step_private_config(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """私有部署配置步骤."""
        errors = {}

        if user_input is not None:
            try:
                self._domain = user_input[CONF_PRIVATE_DOMAIN]
                self._access_token = user_input[CONF_ACCESS_TOKEN]
                self._house_id = user_input[CONF_HOUSE_ID]
                self._house_name = ""
                await async_validate_auth(
                    self.hass,
                    domain=self._domain,
                    access_token=self._access_token,
                )
                return await self._create_entry()
            except Exception as err:
                errors["base"] = flow_error_from_exception("private config", err)

        return self.async_show_form(
            step_id="private_config",
            data_schema=private_config_schema(),
            errors=errors,
        )

    async def _create_entry(self) -> FlowResult:
        """创建配置条目."""
        # 生成唯一 ID
        unique_id = (
            f"{self._connection_mode}:{self._cloud_region}:"
            f"{self._cloud_account_key()}:{self._house_id}"
            if self._connection_mode == CONNECTION_MODE_CLOUD
            else f"{self._connection_mode}:{self._domain}:{self._house_id}"
        )
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        data = {
            CONF_CONNECTION_MODE: self._connection_mode,
            CONF_CLOUD_DOMAIN: self._domain if self._connection_mode == CONNECTION_MODE_CLOUD else "",
            CONF_CLOUD_REGION: (
                self._cloud_region
                if self._connection_mode == CONNECTION_MODE_CLOUD
                else ""
            ),
            CONF_PRIVATE_DOMAIN: self._domain if self._connection_mode == CONNECTION_MODE_PRIVATE else "",
            CONF_ACCESS_TOKEN: self._access_token,
            CONF_REFRESH_TOKEN: self._refresh_token,
            CONF_TOKEN_EXPIRES_IN: self._token_expires_in,
            CONF_TOKEN_TYPE: self._token_type,
            CONF_HOUSE_ID: self._house_id,
            CONF_HOUSE_NAME: self._house_name,
            CONF_OPEN_API_CLIENT_ID: self._open_api_client_id,
            CONF_ACCOUNT_USER_ID: self._account_user_id,
            CONF_ACCOUNT_USERNAME: self._account_username,
            CONF_SCAN_LOGIN_DEVICE: self._scan_login_device,
        }
        return self.async_create_entry(
            title=config_entry_title(data),
            data=data,
            options=self._entry_options(),
        )

    def _entry_options(self) -> dict[str, Any]:
        """返回创建 entry 时需要初始化的 options."""
        if self._connection_mode != CONNECTION_MODE_CLOUD:
            return {}
        return {
            CONF_DEVICE_IMPORT_FILTER: device_import_filter_for_selected_devices(
                self._selected_device_ids,
                self._device_choices,
            )
        }

    def _cloud_account_key(self) -> str:
        """返回不泄露 token 的云端账号隔离片段。"""
        if (
            isinstance(self._scan_login_account_key, str)
            and self._scan_login_account_key
            and self._scan_login_account_key != UNKNOWN_ACCOUNT_KEY
        ):
            return self._scan_login_account_key
        return account_key_from_identity(account_identity(
            account_user_id=self._account_user_id,
            username=self._account_username,
            client_id=self._open_api_client_id,
            access_token=self._access_token,
        ))

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """返回配置条目的 options flow."""
        return YeelightProOptionsFlow(config_entry)
