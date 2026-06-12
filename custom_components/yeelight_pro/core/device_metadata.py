"""Build Home Assistant device-registry metadata from Yeelight topology."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..canonical.models import HAProductModel, ProductModel
from ..const import DOMAIN
from ..utils import to_str
from .device_classification import (
    friendly_model_id,
    is_generic_model_label,
)
from .firmware_metadata import firmware_version
from ..device_display import device_model_name

_DEVICE_NAME_KEYS = ("name", "deviceName", "device_name", "n")
_ROOM_NAME_KEYS = ("roomName", "room_name", "room")
_ROOM_ID_KEYS = ("roomId", "room_id", "roomid")
_ROOM_IDS_KEYS = ("roomIds", "room_ids", "roomids")
_AREA_ID_KEYS = ("areaId", "area_id", "areaid")
_GATEWAY_ID_KEYS = ("gatewayId", "gateway_id", "gatewayDeviceId")


def build_device_info(
    payload: Mapping[str, Any],
    *,
    product_model: HAProductModel,
    rooms: list[dict[str, Any]] | None = None,
    areas: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Return HA device_info enriched with Yeelight name/model/room metadata."""
    device_id = _first_text(payload, ("device_id", "deviceId", "id"))
    if device_id is None:
        return None

    room_name = _room_name(payload, rooms or [], areas or [])
    model = _model_name(payload, product_model)
    name = _device_name(payload, model, device_id)

    device_info: dict[str, Any] = {
        "identifiers": _device_identifiers(device_id),
        "manufacturer": _manufacturer(payload, product_model),
        "model": model,
        "model_id": _model_id(payload, product_model),
        "name": name,
        "default_name": name,
    }

    if room_name is not None:
        device_info["suggested_area"] = room_name
    if serial_number := _first_text(payload, ("serial_number", "serialNumber", "sn")):
        device_info["serial_number"] = serial_number
    if sw_version := firmware_version(payload):
        device_info["sw_version"] = sw_version
    if hw_version := _first_text(payload, ("hw_version", "hwVersion", "hardwareVersion")):
        device_info["hw_version"] = hw_version
    if mac := _first_text(payload, ("mac", "macAddress", "mac_address")):
        device_info["connections"] = [["mac", mac]]
    if via_device := _via_device(payload):
        device_info["via_device"] = [DOMAIN, via_device]

    return {key: value for key, value in device_info.items() if value is not None}


def build_fallback_device_info(
    payload: Mapping[str, Any],
    *,
    rooms: list[dict[str, Any]] | None = None,
    areas: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Build device_info when no full canonical product model can be inferred."""
    product_model = HAProductModel(
        schema_version="metadata-v1",
        product=ProductModel(
            model_id=_fallback_model_id(payload),
            manufacturer="Yeelight",
            model=_fallback_model_name(payload),
            category=_first_text(payload, ("iot_category", "category", "type")),
        ),
        components=[],
        device_actions=[],
        notes=[],
    )
    return build_device_info(
        payload,
        product_model=product_model,
        rooms=rooms,
        areas=areas,
    )


def enrich_payload_metadata(
    payload: dict[str, Any],
    *,
    product_model: HAProductModel,
    rooms: list[dict[str, Any]] | None = None,
    areas: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Attach registry-facing metadata to a normalized mutable payload."""
    device_info = build_device_info(
        payload,
        product_model=product_model,
        rooms=rooms,
        areas=areas,
    )
    if device_info is None:
        return None

    payload["device_info"] = device_info
    payload["name"] = device_info["name"]
    if model := device_info.get("model"):
        payload["model"] = model
    if suggested_area := device_info.get("suggested_area"):
        payload["room_name"] = suggested_area
    return device_info


def attach_fallback_payload_metadata(
    payload: dict[str, Any],
    *,
    rooms: list[dict[str, Any]] | None = None,
    areas: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Attach registry-facing metadata when canonical conversion is unavailable."""
    device_info = build_fallback_device_info(payload, rooms=rooms, areas=areas)
    if device_info is None:
        return None

    payload["device_info"] = device_info
    payload["name"] = device_info["name"]
    if model := device_info.get("model"):
        payload["model"] = model
    if model_id := device_info.get("model_id"):
        payload["model_id"] = model_id
    if suggested_area := device_info.get("suggested_area"):
        payload["room_name"] = suggested_area
    return device_info


def _device_identifiers(device_id: str) -> list[list[str]]:
    """Return identifiers that preserve old registry links and new fallback links."""
    legacy_identifier = [DOMAIN, device_id]
    fallback_identifier = [DOMAIN, f"device:{device_id}"]
    if legacy_identifier == fallback_identifier:
        return [legacy_identifier]
    return [legacy_identifier, fallback_identifier]


def _device_name(
    payload: Mapping[str, Any],
    model: str | None,
    device_id: str,
) -> str:
    """Resolve the user-facing Yeelight device name."""
    name = _first_text(payload, _DEVICE_NAME_KEYS)
    if name is not None:
        return name
    if model is not None:
        return f"{model} {device_id}"
    category = _first_text(payload, ("category", "type"))
    if category is not None:
        return f"Yeelight {category} {device_id}"
    return f"Yeelight Pro {device_id}"


def _manufacturer(
    payload: Mapping[str, Any],
    product_model: HAProductModel,
) -> str:
    return (
        _first_text(payload, ("manufacturer", "brand"))
        or product_model.product.manufacturer
        or "Yeelight"
    )


def _model_id(
    payload: Mapping[str, Any],
    product_model: HAProductModel,
) -> str | None:
    payload_copy = dict(payload)
    product_model_id = product_model.product.model_id
    if product_model_id and not product_model_id.startswith("runtime-"):
        payload_copy["model_id"] = product_model_id
    elif "model_id" not in payload_copy and product_model_id:
        payload_copy["model_id"] = product_model_id
    model_id = friendly_model_id(payload_copy)
    return None if model_id.startswith("runtime-") else model_id


def _model_name(
    payload: Mapping[str, Any],
    product_model: HAProductModel,
) -> str | None:
    return (
        _specific_text(payload, ("model", "modelName", "productName"))
        or _specific_product_model(payload, product_model)
        or _specific_nested_text(payload, "product_schema", ("name", "model", "modelName"))
        or device_model_name(payload)
    )


def _fallback_model_id(payload: Mapping[str, Any]) -> str:
    return friendly_model_id(payload)


def _fallback_model_name(payload: Mapping[str, Any]) -> str:
    return device_model_name(payload)


def _specific_product_model(
    payload: Mapping[str, Any],
    product_model: HAProductModel,
) -> str | None:
    model = product_model.product.model
    if model and not is_generic_model_label(model):
        return model
    return device_model_name(dict(payload, model=None))


def _room_name(
    payload: Mapping[str, Any],
    rooms: list[dict[str, Any]],
    areas: list[dict[str, Any]],
) -> str | None:
    explicit_name = _first_text(payload, _ROOM_NAME_KEYS)
    if explicit_name is not None:
        return explicit_name

    room_by_id = _name_by_id(rooms)
    for room_id in _room_ids(payload):
        if room_name := room_by_id.get(room_id):
            return room_name

    area_by_id = _name_by_id(areas)
    for area_id in _ids_from_keys(payload, _AREA_ID_KEYS):
        if area_name := area_by_id.get(area_id):
            return area_name

    area_by_room_id = _area_name_by_room_id(areas)
    for room_id in _room_ids(payload):
        if area_name := area_by_room_id.get(room_id):
            return area_name
    return None


def _via_device(payload: Mapping[str, Any]) -> str | None:
    gateway_id = _first_text(payload, _GATEWAY_ID_KEYS)
    if gateway_id is None or gateway_id == _first_text(payload, ("device_id", "id")):
        return None
    return gateway_id


def _room_ids(payload: Mapping[str, Any]) -> list[str]:
    ids = _ids_from_keys(payload, _ROOM_ID_KEYS)
    for key in _ROOM_IDS_KEYS:
        ids.extend(_list_text(payload.get(key)))
    return _dedupe(ids)


def _ids_from_keys(payload: Mapping[str, Any], keys: tuple[str, ...]) -> list[str]:
    return _dedupe(
        value
        for key in keys
        if (value := to_str(payload.get(key))) is not None
    )


def _name_by_id(items: list[dict[str, Any]]) -> dict[str, str]:
    names: dict[str, str] = {}
    for item in items:
        if not isinstance(item, Mapping):
            continue
        item_name = _first_text(item, ("name", "roomName", "areaName", "n"))
        if item_name is None:
            continue
        for item_id in _ids_from_keys(
            item,
            ("id", "roomId", "room_id", "areaId", "area_id", "roomid", "areaid"),
        ):
            names[item_id] = item_name
    return names


def _area_name_by_room_id(areas: list[dict[str, Any]]) -> dict[str, str]:
    names: dict[str, str] = {}
    for area in areas:
        if not isinstance(area, Mapping):
            continue
        area_name = _first_text(area, ("name", "areaName", "n"))
        if area_name is None:
            continue
        for room_id in _list_text(area.get("roomIds", area.get("room_ids"))):
            names.setdefault(room_id, area_name)
    return names


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        if value := to_str(payload.get(key)):
            return value
    return None


def _nested_text(
    payload: Mapping[str, Any],
    key: str,
    nested_keys: tuple[str, ...],
) -> str | None:
    nested = payload.get(key)
    if not isinstance(nested, Mapping):
        return None
    return _first_text(nested, nested_keys)


def _specific_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    """Return the first non-generic text value for product model metadata."""
    value = _first_text(payload, keys)
    if value is None or is_generic_model_label(value):
        return None
    return value


def _specific_nested_text(
    payload: Mapping[str, Any],
    key: str,
    nested_keys: tuple[str, ...],
) -> str | None:
    """Return the first non-generic nested product model value."""
    value = _nested_text(payload, key, nested_keys)
    if value is None or is_generic_model_label(value):
        return None
    return value


def _list_text(value: Any) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        return [text for item in value if (text := to_str(item)) is not None]
    text = to_str(value)
    return [text] if text is not None else []


def _dedupe(values: Any) -> list[str]:
    result: list[str] = []
    for value in values:
        text = to_str(value)
        if text is not None and text not in result:
            result.append(text)
    return result
