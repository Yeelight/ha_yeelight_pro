"""Device payload test doubles."""

from __future__ import annotations

from typing import Any, Mapping


class _FakeProduct:
    def __init__(self) -> None:
        self.model_id = "model-100"
        self.manufacturer = "Yeelight"
        self.model = "Fake Product"


class _FakeProductModel:
    def __init__(self) -> None:
        self.product = _FakeProduct()

    def to_dict(self) -> dict[str, Any]:
        return {"product": {"model_id": self.product.model_id}}


class _FakeDeviceInstance:
    def __init__(self, device_info: Mapping[str, Any] | None = None) -> None:
        self.device_info = device_info

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"device_id": 1, "components": []}
        if self.device_info is not None:
            payload["device_info"] = dict(self.device_info)
        return payload


class _ProductSchemaConverter:
    def __init__(self, *, raises: bool = False) -> None:
        self.raises = raises
        self.schemas: list[Mapping[str, Any]] = []

    def convert(self, schema: Mapping[str, Any]) -> _FakeProductModel:
        self.schemas.append(schema)
        if self.raises:
            raise ValueError(
                "bad schema token=secret-token "
                "https://api.yeelight.com/apis/iot/house/12345 device_id=67890"
            )
        return _FakeProductModel()


class _DeviceInstanceConverter:
    def __init__(self) -> None:
        self.payloads: list[Mapping[str, Any]] = []
        self.model_ids: list[str | None] = []
        self.device_infos: list[Mapping[str, Any] | None] = []

    def convert(
        self,
        payload: Mapping[str, Any],
        *,
        product_model: Any | None = None,
        model_id: str | None = None,
        device_info: Mapping[str, Any] | None = None,
    ) -> _FakeDeviceInstance:
        self.payloads.append(payload)
        self.model_ids.append(model_id)
        self.device_infos.append(device_info)
        return _FakeDeviceInstance(device_info)

