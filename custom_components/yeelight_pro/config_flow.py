"""Config flow for the Yeelight Pro integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_ACCESS_TOKEN,
    CONF_CONNECTION_MODE,
    CONF_CLOUD_DOMAIN,
    CONF_HOUSE_ID,
    CONF_PRIVATE_DOMAIN,
    CONNECTION_MODE_CLOUD,
    CONNECTION_MODE_PRIVATE,
    DEFAULT_CLOUD_DOMAIN,
    DEFAULT_PRIVATE_DOMAIN,
    DOMAIN,
)
from .core.client import YeelightProClient
from .core.exceptions import AuthenticationError, ConnectionError

_LOGGER = logging.getLogger(__name__)


class YeelightProConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Yeelight Pro 配置流程."""

    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self):
        """初始化配置流程."""
        self._connection_mode = None
        self._domain = None
        self._access_token = None
        self._house_id = None

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """用户初始步骤：选择连接模式."""
        if user_input is not None:
            self._connection_mode = user_input[CONF_CONNECTION_MODE]

            if self._connection_mode == CONNECTION_MODE_CLOUD:
                self._domain = DEFAULT_CLOUD_DOMAIN
                return await self.async_step_cloud_auth()
            else:
                return await self.async_step_private_config()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_CONNECTION_MODE): vol.In({
                    CONNECTION_MODE_CLOUD: "Yeelight Pro 云端（推荐）",
                    CONNECTION_MODE_PRIVATE: "私有部署（Lucore）",
                })
            }),
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

                # 验证 token
                session = async_get_clientsession(self.hass)
                client = YeelightProClient(
                    domain=self._domain,
                    access_token=self._access_token,
                    session=session,
                )
                await client.validate_auth()

                # 获取家庭列表
                return await self.async_step_cloud_houses()

            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except ConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during cloud auth")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="cloud_auth",
            data_schema=vol.Schema({
                vol.Required(CONF_ACCESS_TOKEN): str,
            }),
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
        if user_input is not None:
            self._house_id = user_input[CONF_HOUSE_ID]
            return await self._create_entry()

        # 获取家庭列表
        session = async_get_clientsession(self.hass)
        client = YeelightProClient(
            domain=self._domain,
            access_token=self._access_token,
            session=session,
        )
        houses = await client.get_houses()

        if not houses:
            return self.async_abort(reason="no_houses_found")

        return self.async_show_form(
            step_id="cloud_houses",
            data_schema=vol.Schema({
                vol.Required(CONF_HOUSE_ID): vol.In({
                    h["id"]: h["name"] for h in houses
                }),
            }),
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

                # 验证连接
                session = async_get_clientsession(self.hass)
                client = YeelightProClient(
                    domain=self._domain,
                    access_token=self._access_token,
                    session=session,
                )
                await client.validate_auth()

                return await self._create_entry()

            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except ConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during private config")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="private_config",
            data_schema=vol.Schema({
                vol.Required(
                    CONF_PRIVATE_DOMAIN,
                    default=DEFAULT_PRIVATE_DOMAIN,
                ): str,
                vol.Required(CONF_ACCESS_TOKEN): str,
                vol.Required(
                    CONF_HOUSE_ID,
                    default=1,
                ): vol.All(vol.Coerce(int), vol.Range(min=1)),
            }),
            errors=errors,
        )

    async def _create_entry(self) -> FlowResult:
        """创建配置条目."""
        # 生成唯一 ID
        unique_id = f"{self._connection_mode}:{self._domain}:{self._house_id}"
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        # 创建条目
        title = f"Yeelight Pro ({self._domain})"
        if self._connection_mode == CONNECTION_MODE_PRIVATE:
            title = f"Yeelight Pro Private ({self._domain})"

        return self.async_create_entry(
            title=title,
            data={
                CONF_CONNECTION_MODE: self._connection_mode,
                CONF_CLOUD_DOMAIN: self._domain if self._connection_mode == CONNECTION_MODE_CLOUD else "",
                CONF_PRIVATE_DOMAIN: self._domain if self._connection_mode == CONNECTION_MODE_PRIVATE else "",
                CONF_ACCESS_TOKEN: self._access_token,
                CONF_HOUSE_ID: self._house_id,
            },
        )

    async def async_step_reauth(
        self,
        entry_data: dict[str, Any],
    ) -> FlowResult:
        """触发 reauth 流程，保存原始配置数据."""
        self._reauth_entry_data = entry_data
        self._connection_mode = entry_data.get(CONF_CONNECTION_MODE, CONNECTION_MODE_CLOUD)
        self._domain = entry_data.get(
            CONF_CLOUD_DOMAIN if self._connection_mode == CONNECTION_MODE_CLOUD else CONF_PRIVATE_DOMAIN,
            "",
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """reauth 确认步骤：用户输入新的 Access Token."""
        errors: dict[str, str] = {}

        if user_input is not None:
            new_token = user_input[CONF_ACCESS_TOKEN]
            try:
                session = async_get_clientsession(self.hass)
                client = YeelightProClient(
                    domain=self._domain,
                    access_token=new_token,
                    session=session,
                )
                await client.validate_auth()
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except ConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during reauth")
                errors["base"] = "unknown"
            else:
                # 更新配置条目的 token
                entry = self._get_reauth_entry()
                new_data = {**entry.data, CONF_ACCESS_TOKEN: new_token}
                return self.async_update_reload_and_abort(
                    entry,
                    data=new_data,
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({
                vol.Required(CONF_ACCESS_TOKEN): str,
            }),
            errors=errors,
            description_placeholders={
                "domain": self._domain,
            },
        )
