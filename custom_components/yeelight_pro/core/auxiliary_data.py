"""Fetch auxiliary Yeelight Pro topology lists."""

from __future__ import annotations

from collections.abc import Mapping
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
    houses: list[dict[str, Any]]
    scenes: list[dict[str, Any]]


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
        houses=await _fetch_house_snapshot(
            client,
            house_id,
            current.houses,
        ),
        scenes=await _fetch_list(
            "scenes",
            client.get_scenes,
            house_id,
            current.scenes,
        ),
    )


async def _fetch_house_snapshot(
    client: YeelightProClient,
    house_id: int,
    current: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Fetch one house snapshot as a topology row."""
    try:
        value = await client.get_house_snapshot(house_id)
    except AuthenticationError:
        raise
    except Exception as err:
        _LOGGER.warning("Failed to fetch house snapshot: %s", safe_error_summary(err))
        return current
    data = value.get("data") if isinstance(value, dict) else None
    rows = _snapshot_rows(data)
    if rows:
        return rows
    row = _mapping_row(value)
    return [row] if row else current


def _snapshot_rows(value: Any) -> list[dict[str, Any]]:
    """Normalize documented house snapshot data into topology rows."""
    row = _mapping_row(value)
    if row is not None:
        return [row]
    if isinstance(value, list):
        return [row for item in value if (row := _mapping_row(item)) is not None]
    return []


def _mapping_row(value: Any) -> dict[str, Any] | None:
    """Return a string-keyed mapping row when the API payload is an object."""
    return dict(value) if isinstance(value, Mapping) else None


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
