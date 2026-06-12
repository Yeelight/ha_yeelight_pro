"""Shared helpers for HA device registry tests."""

from __future__ import annotations

from typing import Any, Mapping


class DeviceRegistryCoordinator:
    """Minimal coordinator used by HA device registry sync tests."""

    data: Mapping[Any, Mapping[str, Any]]
    house_id: int | None

    def __init__(
        self,
        data: Mapping[Any, Mapping[str, Any]],
        gateways: Mapping[Any, Mapping[str, Any]] | None = None,
    ) -> None:
        self.data = data
        self.house_id = 12345
        self.entry_data = {"house_name": "绿地中央公园"}
        self._gateways = gateways or {}

    def get_gateway_devices(self) -> Mapping[Any, Mapping[str, Any]]:
        """Return gateway payloads."""
        return dict(self._gateways)


def device_payload(
    *,
    identifier: str,
    name: str = "客厅主灯",
    model: str = "智能筒灯",
    category: str | None = None,
    suggested_area: str = "客厅",
) -> dict[str, Any]:
    """Build a canonical device payload with registry metadata."""
    payload: dict[str, Any] = {
        "ha_device_instance": {
            "device_info": {
                "identifiers": [["yeelight_pro", identifier]],
                "manufacturer": "Yeelight",
                "model": model,
                "model_id": "YL-100",
                "name": name,
                "suggested_area": suggested_area,
            }
        }
    }
    if category is not None:
        payload["category"] = category
    return payload


def fallback_device_payload(
    *,
    identifier: str,
    name: str = "墙壁开关1",
    model: str = "墙壁开关",
    suggested_area: str = "客厅",
) -> dict:
    """Build a fallback metadata-only device payload."""
    return {
        "device_info": {
            "identifiers": [
                ["yeelight_pro", identifier],
                ["yeelight_pro", f"device:{identifier}"],
            ],
            "manufacturer": "Yeelight",
            "model": model,
            "model_id": "YL-201",
            "name": name,
            "suggested_area": suggested_area,
        },
        "device_id": int(identifier),
    }
