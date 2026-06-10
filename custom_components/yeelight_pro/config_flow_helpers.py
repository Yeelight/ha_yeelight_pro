"""Yeelight Pro 配置流程辅助函数."""
from __future__ import annotations

import logging
from typing import Any, Mapping

import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import selector

from .const import (
    CONF_ACCESS_TOKEN,
    CONF_CLOUD_AUTH_METHOD,
    CONF_CLOUD_REGION,
    CONF_CONNECTION_MODE,
    CONF_HOUSE_ID,
    CONF_PRIVATE_DOMAIN,
    CLOUD_AUTH_METHOD_ACCESS_TOKEN,
    CLOUD_AUTH_METHOD_SCAN_LOGIN,
    CLOUD_REGIONS,
    CONNECTION_MODE_CLOUD,
    CONNECTION_MODE_PRIVATE,
    DEFAULT_CLOUD_REGION,
    DEFAULT_PRIVATE_DOMAIN,
)
from .config_flow_options import (
    device_picker_context as device_picker_context,
    entry_options as entry_options,
    merge_options_device_picker as merge_options_device_picker,
    merge_options as merge_options,
    options_confirm_schema as options_confirm_schema,
    options_device_picker_requested as options_device_picker_requested,
    options_schema as options_schema,
    selected_device_ids_from_options as selected_device_ids_from_options,
    visible_option_change_count as visible_option_change_count,
)
from .core.client import YeelightProClient
from .core.exceptions import AuthenticationError, ConnectionError
from .scan_login_contract import iot_base_url

_LOGGER = logging.getLogger(__name__)


def flow_error_from_exception(stage: str, err: Exception) -> str:
    """将客户端异常映射为 Home Assistant config-flow 错误码."""
    if isinstance(err, AuthenticationError):
        return "invalid_auth"
    if isinstance(err, ConnectionError):
        return "cannot_connect"
    _LOGGER.error("Unexpected error during %s: %s", stage, type(err).__name__)
    return "unknown"


def house_choices(houses: list[dict[str, Any]]) -> dict[Any, str]:
    """归一化开放平台不同字段形态的家庭选择项."""
    choices: dict[Any, str] = {}
    for house in houses:
        house_id = house.get("id") or house.get("houseId") or house.get("house_id")
        if house_id is None:
            continue
        name = house.get("name") or house.get("houseName") or house.get("house_name")
        choices[house_id] = str(name or f"House {house_id}")
    return dict(sorted(choices.items(), key=lambda item: str(item[1])))


def user_schema() -> vol.Schema:
    """返回连接模式选择表单 schema."""
    return vol.Schema({
        vol.Required(CONF_CONNECTION_MODE): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[CONNECTION_MODE_CLOUD, CONNECTION_MODE_PRIVATE],
                mode=selector.SelectSelectorMode.DROPDOWN,
                translation_key="connection_mode",
            )
        )
    })


def cloud_auth_method_schema() -> vol.Schema:
    """返回云端认证方式选择表单 schema."""
    return vol.Schema({
        vol.Required(
            CONF_CLOUD_AUTH_METHOD,
            default=CLOUD_AUTH_METHOD_SCAN_LOGIN,
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    CLOUD_AUTH_METHOD_SCAN_LOGIN,
                    CLOUD_AUTH_METHOD_ACCESS_TOKEN,
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
                translation_key="cloud_auth_method",
            )
        )
    })


def cloud_region_schema() -> vol.Schema:
    """返回 Yeelight 云端区域选择表单 schema."""
    return vol.Schema({
        vol.Required(CONF_CLOUD_REGION, default=DEFAULT_CLOUD_REGION): (
            selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=CLOUD_REGIONS,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key="cloud_region",
                )
            )
        )
    })


def cloud_domain_for_region(region: str) -> str:
    """返回区域对应的 Yeelight IoT Open API 域名。"""
    return iot_base_url(region)


def cloud_auth_schema() -> vol.Schema:
    """返回云端 token 认证表单 schema."""
    return vol.Schema({vol.Required(CONF_ACCESS_TOKEN): str})


def cloud_houses_schema(choices: Mapping[Any, str]) -> vol.Schema:
    """返回云端家庭选择表单 schema."""
    return vol.Schema({vol.Required(CONF_HOUSE_ID): vol.In(dict(choices))})


def private_config_schema() -> vol.Schema:
    """返回私有部署配置表单 schema."""
    return vol.Schema({
        vol.Required(CONF_PRIVATE_DOMAIN, default=DEFAULT_PRIVATE_DOMAIN): str,
        vol.Required(CONF_ACCESS_TOKEN): str,
        vol.Required(CONF_HOUSE_ID, default=1): vol.All(
            vol.Coerce(int),
            vol.Range(min=1),
        ),
    })


def reauth_confirm_schema() -> vol.Schema:
    """返回重新认证 token 表单 schema."""
    return cloud_auth_schema()


async def async_validate_auth(
    hass: HomeAssistant,
    *,
    domain: str,
    access_token: str,
    client_id: str | None = None,
) -> None:
    """对配置的 Yeelight 端点执行认证校验."""
    client = _client(
        hass,
        domain=domain,
        access_token=access_token,
        client_id=client_id,
    )
    await client.validate_auth()


async def async_load_house_choices(
    hass: HomeAssistant,
    *,
    domain: str,
    access_token: str,
    client_id: str | None = None,
) -> dict[Any, str]:
    """加载并归一化可选家庭列表."""
    client = _client(
        hass,
        domain=domain,
        access_token=access_token,
        client_id=client_id,
    )
    return house_choices(await client.get_houses())


def _client(
    hass: HomeAssistant,
    *,
    domain: str,
    access_token: str,
    client_id: str | None = None,
) -> YeelightProClient:
    """构造用于配置流程校验的 Yeelight 客户端."""
    return YeelightProClient(
        domain=domain,
        access_token=access_token,
        client_id=client_id,
        session=async_get_clientsession(hass),
    )


def _required_text(value: Any) -> str:
    """返回去首尾空白后的非空文本."""
    if not isinstance(value, str) or not value.strip():
        raise vol.Invalid("required")
    return value.strip()
