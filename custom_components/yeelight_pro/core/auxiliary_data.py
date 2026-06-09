"""Fetch auxiliary Yeelight Pro topology lists."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from .client import YeelightProClient
from .exceptions import AuthenticationError, safe_error_summary

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class AuxiliaryData:
    """Auxiliary topology lists that do not block primary device polling."""

    areas: list[dict[str, Any]]
    rooms: list[dict[str, Any]]
    groups: list[dict[str, Any]]
    scenes: list[dict[str, Any]]
    automations: list[dict[str, Any]]


async def async_fetch_auxiliary_data(
    client: YeelightProClient,
    house_id: int,
    current: AuxiliaryData,
) -> AuxiliaryData:
    """Fetch auxiliary lists, preserving the last successful value on soft failures."""
    return AuxiliaryData(
        areas=await _fetch_list(
            "areas",
            client.get_areas,
            house_id,
            current.areas,
        ),
        rooms=await _fetch_list(
            "rooms",
            client.get_rooms,
            house_id,
            current.rooms,
        ),
        groups=await _fetch_list(
            "groups",
            client.get_groups,
            house_id,
            current.groups,
        ),
        scenes=await _fetch_list(
            "scenes",
            client.get_scenes,
            house_id,
            current.scenes,
        ),
        automations=await _fetch_list(
            "automations",
            client.get_automations,
            house_id,
            current.automations,
        ),
    )


async def _fetch_list(
    label: str,
    fetcher: Any,
    house_id: int,
    current: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Fetch one auxiliary list with shared soft-failure handling."""
    try:
        value = await fetcher(house_id)
    except AuthenticationError:
        raise
    except Exception as err:
        _LOGGER.warning("Failed to fetch %s: %s", label, safe_error_summary(err))
        return current
    return value if isinstance(value, list) else current
