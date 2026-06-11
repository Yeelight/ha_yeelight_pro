"""Runtime state merge helper tests."""

from __future__ import annotations

from typing import Any, cast

import pytest

from custom_components.yeelight_pro.core.runtime_state import (
    RuntimeStateStore,
    component_matches_index,
    merge_runtime_state_into_loaded_payloads,
    merge_runtime_state_into_payload,
    online_from_params,
    split_indexed_runtime_key,
)


def test_runtime_state_store_saves_updates_and_applies_to_device() -> None:
    """store 应保存运行时覆盖，并能应用到新 normalize 的设备."""
    store = RuntimeStateStore()
    store.store_update(
        1,
        {"p": False, "o": False},
        devices={},
        gateways={},
        data={},
        rebuild_canonical=lambda _device: None,
    )
    device: dict[str, Any] = {
        "id": 1,
        "params": {"p": True},
        "online": True,
    }

    returned = store.apply_to_device(device)

    assert returned is device
    assert device["params"] == {"p": False, "o": False}
    assert device["online"] is False
    assert store.overrides[1]["params"] == {"p": False, "o": False}
    with pytest.raises(TypeError):
        cast(Any, store.overrides)[2] = {"params": {}}


def test_runtime_state_store_syncs_loaded_payloads() -> None:
    """store_update 应同步当前已加载 payload，并避免重复 canonical 重建."""
    store = RuntimeStateStore()
    device: dict[str, Any] = {
        "id": 1,
        "params": {"p": True},
        "product_schema": {"pid": 100},
    }
    rebuilt: list[dict[str, Any]] = []

    store.store_update(
        1,
        {"p": False},
        devices={1: device},
        gateways={1: device},
        data={1: device},
        rebuild_canonical=rebuilt.append,
    )

    assert store.overrides[1]["params"] == {"p": False}
    assert device["params"] == {"p": False}
    assert rebuilt == [device]


def test_merge_runtime_state_into_payload_updates_flat_and_canonical_state() -> None:
    """运行时状态应同步 legacy params 与手工 canonical 组件状态."""
    device: dict[str, Any] = {
        "id": 1,
        "params": "invalid",
        "online": True,
        "ha_device_instance": {
            "online": True,
            "components": [
                {
                    "component_id": "light_1",
                    "available": True,
                    "state": {"p": True},
                }
            ],
        },
    }

    merge_runtime_state_into_payload(
        device,
        {"p": False, "l": 80},
        online=False,
    )

    assert device["params"] == {"p": False, "l": 80}
    assert device["online"] is False
    instance = device["ha_device_instance"]
    assert instance["online"] is False
    assert instance["components"][0]["available"] is False
    assert instance["components"][0]["state"] == {"p": False, "l": 80}


def test_merge_runtime_state_parses_string_online_values() -> None:
    """WebSocket/LAN 增量在线状态字符串也必须按布尔语义解析."""
    device: dict[str, Any] = {
        "id": 1,
        "online": True,
        "ha_device_instance": {
            "online": True,
            "components": [
                {
                    "component_id": "light_1",
                    "available": True,
                    "state": {"p": True},
                }
            ],
        },
    }

    merge_runtime_state_into_payload(device, {}, online="false")

    assert device["online"] is False
    instance = device["ha_device_instance"]
    assert instance["online"] is False
    assert instance["components"][0]["available"] is False


def test_merge_runtime_state_into_payload_routes_indexed_component_keys() -> None:
    """indexed key 只能写入匹配组件，避免多路组件互相污染."""
    device: dict[str, Any] = {
        "id": 1,
        "ha_device_instance": {
            "components": [
                {"index": 1, "state": {"p": True}},
                {"component_id": "relay_2", "state": {"p": False}},
            ],
        },
    }

    merge_runtime_state_into_payload(device, {"1-p": False, "2-p": True})

    components = device["ha_device_instance"]["components"]
    assert components[0]["state"] == {"p": False}
    assert components[1]["state"] == {"p": True}


def test_merge_runtime_state_replaces_invalid_component_state() -> None:
    """组件 state 异常时应恢复为 dict，保证后续投影读取稳定."""
    device: dict[str, Any] = {
        "id": 1,
        "ha_device_instance": {
            "components": [
                {
                    "index": 1,
                    "state": None,
                }
            ],
        },
    }

    merge_runtime_state_into_payload(device, {"p": True})

    assert device["ha_device_instance"]["components"][0]["state"] == {"p": True}


def test_merge_runtime_state_into_loaded_payloads_deduplicates_same_object() -> None:
    """同一个 payload 同时位于 devices/gateways/data 时只触发一次重建."""
    device: dict[str, Any] = {
        "id": 1,
        "params": {"p": True},
        "product_schema": {"pid": 100},
    }
    rebuilt: list[dict[str, Any]] = []

    merge_runtime_state_into_loaded_payloads(
        device_id=1,
        params={"p": False},
        online=True,
        devices={1: device},
        gateways={1: device},
        data={1: device},
        rebuild_canonical=rebuilt.append,
    )

    assert device["params"] == {"p": False}
    assert device["online"] is True
    assert rebuilt == [device]


def test_merge_runtime_state_into_loaded_payloads_ignores_missing_payloads() -> None:
    """未加载设备收到状态时不应创建空 payload 或抛错."""
    merge_runtime_state_into_loaded_payloads(
        device_id=404,
        params={"p": True},
        online=None,
        devices={},
        gateways={},
        data={},
        rebuild_canonical=lambda _device: None,
    )


def test_runtime_state_index_helpers_support_plain_and_indexed_keys() -> None:
    """运行时 key helper 应兼容 plain key 与组件 indexed key."""
    assert split_indexed_runtime_key("p") == (None, "p")
    assert split_indexed_runtime_key("1-p") == ("1", "p")
    assert split_indexed_runtime_key("01-sp") == ("01", "sp")
    assert split_indexed_runtime_key("abc-p") == (None, "abc-p")
    assert split_indexed_runtime_key("1-") == (None, "1-")

    assert component_matches_index({"index": 1}, "1") is True
    assert component_matches_index({"component_id": "relay_2"}, "2") is True
    assert component_matches_index({"componentId": "relay_3"}, "3") is True
    assert component_matches_index({"index": 4}, "1") is False


def test_online_from_params_uses_yeelight_online_property() -> None:
    """在线状态仅由 o 属性表达，缺失时保持未知."""
    assert online_from_params({"o": False}) is False
    assert online_from_params({"o": "true"}) is True
    assert online_from_params({"p": True}) is None
