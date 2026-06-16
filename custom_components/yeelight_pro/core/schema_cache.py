"""Yeelight Pro 产品物模型缓存."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable, Mapping
from copy import deepcopy
import logging
import re
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from ..const import DOMAIN
from ..utils import to_int
from .exceptions import AuthenticationError, safe_error_summary

SchemaFetcher = Callable[[list[int]], Awaitable[dict[int, dict[str, Any]]]]
STORAGE_KEY = f"{DOMAIN}.product_schemas"
STORAGE_VERSION = 1
SAVE_DELAY = 10
PRODUCT_ID_KEYS = ("pid", "productId", "productID", "product_id", "productKey", "product_key")
_LOGGER = logging.getLogger(__name__)
_SENSITIVE_SCHEMA_STORAGE_KEYS = frozenset({
    "access_token",
    "accesstoken",
    "authorization",
    "device_id",
    "deviceid",
    "deviceids",
    "devices",
    "house_id",
    "houseid",
    "houseids",
    "houses",
    "localtoken",
    "mac",
    "mac_address",
    "macaddress",
    "password",
    "private_domain",
    "private_push_domain",
    "privatedomain",
    "privatepushdomain",
    "raw_payload",
    "rawpayload",
    "room_id",
    "roomid",
    "roomids",
    "roomname",
    "rooms",
    "token",
    "username",
})
_SENSITIVE_SCHEMA_STORAGE_VALUE_PATTERNS = (
    re.compile(r"\bbearer\s+[a-z0-9._~+/=-]+", re.IGNORECASE),
    re.compile(r"\b(?:access_)?token\s*[:=]", re.IGNORECASE),
    re.compile(r"\bauthorization\s*[:=]", re.IGNORECASE),
    re.compile(r"\bhouse(?:_?id)?\s*[:=]", re.IGNORECASE),
    re.compile(r"\bdevice(?:_?id)?\s*[:=]", re.IGNORECASE),
    re.compile(r"\broom(?:_?id)?\s*[:=]", re.IGNORECASE),
    re.compile(r"\bmac(?:_address)?\s*[:=]", re.IGNORECASE),
)


class ProductSchemaCache:
    """缓存稳定的产品 schema，避免轮询期因端点抖动导致拓扑退化."""

    def __init__(self, hass: HomeAssistant | None = None) -> None:
        """初始化内存缓存."""
        self._schemas: dict[int, dict[str, Any]] = {}
        self._store: Store[dict[str, Any]] | None = (
            Store(hass, STORAGE_VERSION, STORAGE_KEY, atomic_writes=True)
            if hass is not None
            else None
        )
        self._loaded = False

    async def async_load(self) -> None:
        """从 HA .storage 加载持久产品 schema 缓存."""
        if self._loaded:
            return
        self._loaded = True
        if self._store is None:
            return
        try:
            stored = await self._store.async_load()
        except Exception as err:
            _LOGGER.warning(
                "Failed to load Yeelight product schema cache: %s",
                safe_error_summary(err),
            )
            return
        if not isinstance(stored, Mapping):
            return
        self.update(_stored_schemas(stored))

    async def async_get(
        self,
        product_ids: Iterable[Any],
        fetcher: SchemaFetcher,
        *,
        force_refresh: bool = False,
    ) -> dict[int, dict[str, Any]]:
        """返回产品 schema，缺失 PID 才调用远端 fetcher."""
        await self.async_load()
        requested = normalize_product_ids(product_ids)
        missing = (
            requested
            if force_refresh
            else [pid for pid in requested if pid not in self._schemas]
        )
        if missing:
            self.update(await fetcher(missing))
            self.async_schedule_save()
        return self.get_many(requested)

    async def async_get_with_fallback(
        self,
        product_ids: Iterable[Any],
        fetcher: SchemaFetcher,
        *,
        force_refresh: bool = False,
    ) -> dict[int, dict[str, Any]]:
        """返回产品 schema；远端失败时回退到已缓存 schema."""
        requested = normalize_product_ids(product_ids)
        if not requested:
            return {}
        try:
            return await self.async_get(
                requested,
                fetcher,
                force_refresh=force_refresh,
            )
        except AuthenticationError:
            raise
        except Exception as err:
            cached = self.get_many(requested)
            missing = self.missing(requested)
            _LOGGER.warning(
                "Failed to fetch product schemas: %s; using %s cached schemas, "
                "%s product ids remain without schema",
                safe_error_summary(err),
                len(cached),
                len(missing),
            )
            return cached

    def update(self, schemas: Mapping[Any, Mapping[str, Any]]) -> None:
        """写入远端返回的 schema，忽略无效 PID 或无效载荷."""
        for raw_pid, schema in schemas.items():
            if not isinstance(schema, Mapping):
                continue
            pid = _schema_pid(raw_pid, schema)
            if pid is None:
                continue
            self._schemas[pid] = deepcopy(dict(schema))

    def get_many(self, product_ids: Iterable[Any]) -> dict[int, dict[str, Any]]:
        """读取多个产品 schema，返回副本避免调用方误改缓存."""
        result: dict[int, dict[str, Any]] = {}
        for pid in normalize_product_ids(product_ids):
            schema = self._schemas.get(pid)
            if schema is not None:
                result[pid] = deepcopy(schema)
        return result

    def missing(self, product_ids: Iterable[Any]) -> list[int]:
        """返回当前缓存缺失的 PID 列表."""
        return [
            pid
            for pid in normalize_product_ids(product_ids)
            if pid not in self._schemas
        ]

    @property
    def size(self) -> int:
        """返回已缓存产品数量."""
        return len(self._schemas)

    def async_schedule_save(self) -> None:
        """延迟保存产品 schema 缓存到 HA .storage."""
        if self._store is None or not self._loaded:
            return
        self._store.async_delay_save(self.as_storage_data, SAVE_DELAY)

    def as_storage_data(self) -> dict[str, Any]:
        """返回可持久化且不含设备/用户敏感信息的 schema 缓存."""
        schemas: dict[str, dict[str, Any]] = {}
        for pid, schema in sorted(self._schemas.items()):
            safe_schema = _json_safe_schema(schema)
            if safe_schema:
                schemas[str(pid)] = safe_schema
        return {"schemas": schemas}


def product_ids_from_items(items: Iterable[Mapping[str, Any]]) -> list[int]:
    """从设备/网关载荷提取稳定、去重的 PID 列表."""
    return normalize_product_ids(
        product_id_from_mapping(item) for item in items if isinstance(item, Mapping)
    )


def product_id_from_mapping(item: Mapping[str, Any]) -> int | None:
    """从云端载荷提取产品 ID，兼容常见字段别名."""
    for key in PRODUCT_ID_KEYS:
        pid = to_int(item.get(key))
        if pid is not None:
            return pid
    return None


def normalize_product_ids(values: Iterable[Any]) -> list[int]:
    """归一化 PID 列表，保持首次出现顺序."""
    seen: set[int] = set()
    result: list[int] = []
    for value in values:
        pid = to_int(value)
        if pid is None or pid in seen:
            continue
        seen.add(pid)
        result.append(pid)
    return result


def _schema_pid(raw_pid: Any, schema: Mapping[str, Any]) -> int | None:
    """优先使用 map key，缺失时回退到 schema 内的 pid 字段."""
    return to_int(raw_pid) or product_id_from_mapping(schema)


def _stored_schemas(stored: Mapping[str, Any]) -> Mapping[Any, Mapping[str, Any]]:
    """读取持久缓存中的 schema map，兼容未来扩展字段."""
    schemas = stored.get("schemas")
    return schemas if isinstance(schemas, Mapping) else {}


def _json_safe_schema(schema: Mapping[str, Any]) -> dict[str, Any]:
    """Return a JSON-safe schema object suitable for HA .storage."""
    safe = _json_safe_value(schema)
    return safe if isinstance(safe, dict) else {}


def _json_safe_value(value: Any) -> Any:
    """Return JSON-safe schema values and drop unsupported runtime objects."""
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for raw_key, raw_value in value.items():
            if not isinstance(raw_key, str) or _is_sensitive_schema_storage_key(raw_key):
                continue
            safe_value = _json_safe_value(raw_value)
            if safe_value is not None:
                result[raw_key] = safe_value
        return result
    if isinstance(value, list):
        return [
            safe_item
            for item in value
            if (safe_item := _json_safe_value(item)) is not None
        ]
    if isinstance(value, str):
        return None if _is_sensitive_schema_storage_text(value) else value
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return None


def _is_sensitive_schema_storage_key(key: str) -> bool:
    """Return true when a schema field is actually runtime/account context."""
    normalized = re.sub(r"[^a-z0-9]+", "", key.lower())
    return normalized in _SENSITIVE_SCHEMA_STORAGE_KEYS


def _is_sensitive_schema_storage_text(value: str) -> bool:
    """Return true when a string value looks like raw auth/topology context."""
    return any(pattern.search(value) for pattern in _SENSITIVE_SCHEMA_STORAGE_VALUE_PATTERNS)
