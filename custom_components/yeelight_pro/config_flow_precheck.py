"""Network precheck helpers for Yeelight Pro config flows."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Literal

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .core.client import YeelightProClient
from .core.exceptions import AuthenticationError, ConnectionError, safe_error_summary

PrecheckTarget = Literal["cloud", "private", "lan"]
PrecheckStatus = Literal["ok", "failed"]
PrecheckErrorType = Literal["auth", "network", "invalid_config", "unknown"]
ClientFactory = Callable[..., YeelightProClient]


@dataclass(frozen=True, slots=True)
class NetworkPrecheckResult:
    """Sanitized outcome of a config-flow network precheck."""

    target: PrecheckTarget
    status: PrecheckStatus
    error_type: PrecheckErrorType | None = None
    error_code: str | None = None
    error_summary: str | None = None

    @property
    def ok(self) -> bool:
        """Return whether the precheck succeeded."""
        return self.status == "ok"


async def async_precheck_cloud_connection(
    hass: HomeAssistant,
    *,
    domain: str,
    access_token: str,
    client_id: str | None = None,
    house_id: int | None = None,
    client_factory: ClientFactory | None = None,
) -> NetworkPrecheckResult:
    """Validate Yeelight cloud auth and optional house Open API reachability."""
    client = (client_factory or _client)(
        hass,
        domain=domain,
        access_token=access_token,
        client_id=client_id,
    )
    return await _async_precheck_client("cloud", client, house_id=house_id)


async def async_precheck_private_connection(
    hass: HomeAssistant,
    *,
    domain: str,
    access_token: str,
    client_id: str | None = None,
    house_id: int | None = None,
    client_factory: ClientFactory | None = None,
) -> NetworkPrecheckResult:
    """Validate a private Yeelight Open API endpoint and optional house reachability."""
    client = (client_factory or _client)(
        hass,
        domain=domain,
        access_token=access_token,
        client_id=client_id,
    )
    return await _async_precheck_client("private", client, house_id=house_id)


async def async_precheck_lan_connection(
    host: str,
    port: int,
    *,
    validator: Callable[[str, int], Awaitable[None]],
) -> NetworkPrecheckResult:
    """Validate LAN gateway TCP reachability without exposing endpoint details."""
    if not isinstance(host, str) or not host.strip():
        return _failure("lan", "invalid_config", "invalid_host")
    if not isinstance(port, int) or not 1 <= port <= 65535:
        return _failure("lan", "invalid_config", "invalid_port")
    try:
        await validator(host.strip(), port)
    except ConnectionError as err:
        return _failure("lan", "network", "cannot_connect", err)
    except Exception as err:
        return _failure("lan", "unknown", "unknown", err)
    return NetworkPrecheckResult(target="lan", status="ok")


def precheck_error_code(result: NetworkPrecheckResult) -> str | None:
    """Return the Home Assistant config-flow error code for a failed precheck."""
    if result.ok:
        return None
    if result.error_type == "auth":
        return "invalid_auth"
    if result.error_type in {"network", "invalid_config"}:
        return "cannot_connect"
    return "unknown"


async def _async_precheck_client(
    target: PrecheckTarget,
    client: YeelightProClient,
    *,
    house_id: int | None = None,
) -> NetworkPrecheckResult:
    """Run a client precheck and classify expected Yeelight failures."""
    try:
        await client.validate_auth()
        if house_id is not None:
            if not isinstance(house_id, int) or house_id < 1:
                return _failure(target, "invalid_config", "invalid_house")
            await client.get_house_snapshot(house_id)
    except AuthenticationError as err:
        return _failure(target, "auth", "invalid_auth", err)
    except ConnectionError as err:
        return _failure(target, "network", "cannot_connect", err)
    except Exception as err:
        return _failure(target, "unknown", "unknown", err)
    return NetworkPrecheckResult(target=target, status="ok")


def _failure(
    target: PrecheckTarget,
    error_type: PrecheckErrorType,
    error_code: str,
    err: Exception | None = None,
) -> NetworkPrecheckResult:
    """Build a sanitized failed precheck result."""
    return NetworkPrecheckResult(
        target=target,
        status="failed",
        error_type=error_type,
        error_code=error_code,
        error_summary=safe_error_summary(err) if err is not None else None,
    )


def _client(
    hass: HomeAssistant,
    *,
    domain: str,
    access_token: str,
    client_id: str | None = None,
) -> YeelightProClient:
    """Build the short-lived config-flow client used by prechecks."""
    return YeelightProClient(
        domain=domain,
        access_token=access_token,
        client_id=client_id,
        session=async_get_clientsession(hass),
    )


__all__ = [
    "NetworkPrecheckResult",
    "async_precheck_cloud_connection",
    "async_precheck_lan_connection",
    "async_precheck_private_connection",
    "precheck_error_code",
]
