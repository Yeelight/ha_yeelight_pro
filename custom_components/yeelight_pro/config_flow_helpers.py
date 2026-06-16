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
    CONF_LAN_GATEWAY_IP,
    CONF_LAN_GATEWAY_PORT,
    CONF_LAN_GATEWAY_PRODUCT_ID,
    CONF_PRIVATE_DOMAIN,
    CLOUD_AUTH_METHOD_ACCESS_TOKEN,
    CLOUD_AUTH_METHOD_SCAN_LOGIN,
    CLOUD_REGIONS,
    CONNECTION_MODE_CLOUD,
    CONNECTION_MODE_LAN,
    CONNECTION_MODE_PRIVATE,
    DEFAULT_CLOUD_REGION,
    DEFAULT_LAN_GATEWAY_PORT,
    LAN_GATEWAY_PRODUCT_ID_GATEWAY,
    LAN_GATEWAY_PRODUCT_IDS,
)
from .config_flow_options import (
    entry_options as entry_options,
    merge_options as merge_options,
    options_confirm_schema as options_confirm_schema,
    options_schema as options_schema,
    visible_option_change_count as visible_option_change_count,
)
from .core.client import YeelightProClient
from .core.exceptions import AuthenticationError, ConnectionError
from .config_flow_precheck import (
    async_precheck_cloud_connection,
    precheck_error_code,
)
from .deployment_urls import deployment_iot_base_url
from .scan_login_contract import iot_base_url
from .house_metadata import house_name_from_choice
from .house_metadata import friendly_house_name

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
    unnamed_count = 0
    for house in houses:
        house_id = house.get("id") or house.get("houseId") or house.get("house_id")
        if house_id is None:
            continue
        name = (
            house.get("name")
            or house.get("houseName")
            or house.get("house_name")
            or house.get("projectName")
            or house.get("project_name")
        )
        friendly_name = friendly_house_name(name)
        if friendly_name:
            label = friendly_name
        else:
            unnamed_count += 1
            label = (
                house_name_from_choice({}, house_id)
                if unnamed_count == 1
                else f"{house_name_from_choice({}, house_id)} {unnamed_count}"
            )
        choices[house_id] = label
    return dict(sorted(choices.items(), key=lambda item: str(item[1])))


def user_schema() -> vol.Schema:
    """返回连接模式选择表单 schema."""
    return vol.Schema({
        vol.Required(CONF_CONNECTION_MODE): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    CONNECTION_MODE_CLOUD,
                    CONNECTION_MODE_PRIVATE,
                    CONNECTION_MODE_LAN,
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
                translation_key="connection_mode",
            )
        )
    })


def cloud_auth_method_schema() -> vol.Schema:
    """返回认证方式选择表单 schema."""
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
    """返回 token 认证表单 schema."""
    return vol.Schema({vol.Required(CONF_ACCESS_TOKEN): str})


def cloud_houses_schema(choices: Mapping[Any, str]) -> vol.Schema:
    """返回家庭选择表单 schema."""
    return vol.Schema({vol.Required(CONF_HOUSE_ID): vol.In(dict(choices))})


def private_config_schema() -> vol.Schema:
    """返回私有部署 URL 配置表单 schema."""
    return vol.Schema({
        vol.Required(CONF_PRIVATE_DOMAIN, default=""): str,
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
    house_id: int | None = None,
) -> None:
    """对配置的 Yeelight 端点执行认证校验."""
    result = await async_precheck_cloud_connection(
        hass,
        domain=domain,
        access_token=access_token,
        client_id=client_id,
        house_id=house_id,
        client_factory=_client,
    )
    if result.ok:
        return
    if result.error_code == "invalid_auth":
        raise AuthenticationError(result.error_summary or "Authentication failed")
    if result.error_code == "cannot_connect":
        raise ConnectionError(result.error_summary or "Connection failed")
    raise RuntimeError(result.error_summary or precheck_error_code(result) or "unknown")


async def async_validate_private_auth(
    hass: HomeAssistant,
    *,
    domain: str,
    access_token: str,
    client_id: str | None = None,
    house_id: int | None = None,
) -> None:
    """对私有部署端点执行认证和连通性预检."""
    result = await async_precheck_cloud_connection(
        hass,
        domain=deployment_iot_base_url(domain),
        access_token=access_token,
        client_id=client_id,
        house_id=house_id,
        client_factory=_client,
    )
    if result.ok:
        return
    if result.error_code == "invalid_auth":
        raise AuthenticationError(result.error_summary or "Authentication failed")
    if result.error_code == "cannot_connect":
        raise ConnectionError(result.error_summary or "Connection failed")
    raise RuntimeError(result.error_summary or precheck_error_code(result) or "unknown")


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



def lan_config_schema(discovered_ip: str | None = None) -> vol.Schema:
    """返回局域网网关配置表单 schema（手动输入模式）."""
    return vol.Schema({
        vol.Required(
            CONF_LAN_GATEWAY_IP,
            default=discovered_ip or "",
        ): str,
        vol.Optional(
            CONF_LAN_GATEWAY_PORT,
            default=DEFAULT_LAN_GATEWAY_PORT,
        ): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
        vol.Optional(
            CONF_LAN_GATEWAY_PRODUCT_ID,
            default=str(LAN_GATEWAY_PRODUCT_ID_GATEWAY),
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[str(pid) for pid in LAN_GATEWAY_PRODUCT_IDS],
                mode=selector.SelectSelectorMode.DROPDOWN,
                translation_key="lan_gateway_product_id",
            )
        ),
    })


def lan_discovered_schema(
    discovered_gateways: list[tuple[str, int, str]],
) -> vol.Schema:
    """返回已发现网关的选择表单 schema。

    discovered_gateways: [(ip, port, display_label), ...]
    """
    # 构建选项列表：已发现网关 + "手动输入"
    options = [ip for ip, _port, _label in discovered_gateways]
    options.append("_manual")
    return vol.Schema({
        vol.Required(CONF_LAN_GATEWAY_IP): vol.In({
            ip: label for ip, _port, label in discovered_gateways
        } | {"_manual": "手动输入网关地址"}),
    })


async def async_validate_lan_connection(
    host: str,
    port: int,
    *,
    timeout: float = 5.0,
) -> None:
    """验证能否与局域网网关建立 TCP 连接."""
    import asyncio

    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout,
        )
        writer.close()
        wait_closed = getattr(writer, "wait_closed", None)
        if callable(wait_closed):
            await wait_closed() # pyright: ignore[reportGeneralTypeIssues]
    except (OSError, asyncio.TimeoutError) as err:
        raise ConnectionError(f"无法连接到局域网网关 {host}:{port}") from err
