"""Home Assistant-free client helpers for guarded production probes."""

from __future__ import annotations

from collections.abc import Mapping
import importlib.util
from pathlib import Path
import sys
import types
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COMPONENT_ROOT = ROOT / "custom_components" / "yeelight_pro"
PROBE_PACKAGE = "yeelight_pro_http_probe"
# Regression guard: production probes must not import homeassistant or schema_cache.


class ProbeYeelightClient:
    """Minimal Open API client used only by explicit production probes."""

    def __init__(
        self,
        *,
        domain: str,
        access_token: str,
        session: Any,
        client_id: str | None = None,
        timeout: int = 10,
    ) -> None:
        """Initialize the probe client without importing HA runtime modules."""
        self.domain = domain.rstrip("/")
        self.access_token = access_token
        self.client_id = client_id.strip() if isinstance(client_id, str) else ""
        self.session = session
        self.timeout = _client_timeout(timeout)

    @property
    def base_url(self) -> str:
        """Return the normalized Open API base URL."""
        if not self.domain.startswith(("http://", "https://")):
            return f"https://{self.domain}"
        return self.domain

    async def _request(
        self,
        method: str,
        path: str,
        *,
        with_auth: bool = True,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Send one Open API request through the shared request helper."""
        request_module = _load_client_request_module()
        return await request_module.request_json(
            self.session,
            self.timeout,
            method,
            f"{self.base_url.rstrip('/')}{path}",
            headers=request_module.build_client_headers(
                access_token=self.access_token,
                client_id=self.client_id,
                with_auth=with_auth,
            ),
            **kwargs,
        )

    async def get_devices(
        self,
        house_id: int,
        *,
        room_id: int | str | None = None,
    ) -> list[dict[str, object]]:
        """Read all device rows for a house through documented pagination."""
        paths = _load_client_paths_module()
        return await self._get_paginated_rows(
            paths.house_devices_path(house_id, room_id=room_id)
        )

    async def _get_paginated_rows(
        self,
        path_prefix: str,
        *,
        page_size: int | None = None,
    ) -> list[dict[str, object]]:
        """Read rows/total style Open API pages without schema-cache imports."""
        paths = _load_client_paths_module()
        page_size = int(page_size or _default_page_size())
        rows: list[dict[str, object]] = []
        page = 1
        while True:
            response = await self._request(
                "GET",
                paths.paginated_path(path_prefix, page=page, page_size=page_size),
            )
            data = response.get("data", {})
            if not isinstance(data, Mapping):
                break
            page_rows = _list_result(data)
            total = _int_or_none(data.get("total"))
            rows.extend(page_rows)
            if not page_rows or (total is not None and len(rows) >= total):
                break
            page += 1
        return rows


def load_yeelight_client() -> type[ProbeYeelightClient]:
    """Return the HA-free probe client class."""
    _ensure_probe_package()
    _load_client_request_module()
    _load_client_paths_module()
    return ProbeYeelightClient


def load_scan_login_contract() -> Any:
    """Load scan-login region helpers without importing Home Assistant."""
    _ensure_probe_package()
    for module_name, path in (
        (f"{PROBE_PACKAGE}.core.exceptions", COMPONENT_ROOT / "core" / "exceptions.py"),
        (f"{PROBE_PACKAGE}.core.http_errors", COMPONENT_ROOT / "core" / "http_errors.py"),
        (f"{PROBE_PACKAGE}.const", COMPONENT_ROOT / "const.py"),
    ):
        if module_name not in sys.modules:
            _load_probe_module(module_name, path)
    return _load_probe_module(
        f"{PROBE_PACKAGE}.scan_login_contract",
        COMPONENT_ROOT / "scan_login_contract.py",
    )



def _load_client_request_module() -> Any:
    """Load shared HTTP request helpers in an isolated HA-free namespace."""
    _ensure_probe_package()
    for module_name, path in (
        (f"{PROBE_PACKAGE}.core.exceptions", COMPONENT_ROOT / "core" / "exceptions.py"),
        (f"{PROBE_PACKAGE}.core.http_errors", COMPONENT_ROOT / "core" / "http_errors.py"),
    ):
        if module_name not in sys.modules:
            _load_probe_module(module_name, path)
    return _load_probe_module(
        f"{PROBE_PACKAGE}.core.client_request",
        COMPONENT_ROOT / "core" / "client_request.py",
    )


def _load_client_paths_module() -> Any:
    """Load path builders and their registry dependencies without HA."""
    _ensure_probe_package()
    for module_name, path in (
        (f"{PROBE_PACKAGE}.core.exceptions", COMPONENT_ROOT / "core" / "exceptions.py"),
        (f"{PROBE_PACKAGE}.capabilities.models", COMPONENT_ROOT / "capabilities" / "models.py"),
        (f"{PROBE_PACKAGE}.capabilities.data", COMPONENT_ROOT / "capabilities" / "data.py"),
        (f"{PROBE_PACKAGE}.capabilities.registry", COMPONENT_ROOT / "capabilities" / "registry.py"),
    ):
        if module_name not in sys.modules:
            _load_probe_module(module_name, path)
    return _load_probe_module(
        f"{PROBE_PACKAGE}.core.client_paths",
        COMPONENT_ROOT / "core" / "client_paths.py",
    )


def _load_const_module() -> Any:
    """Load constants without importing the Home Assistant package."""
    _ensure_probe_package()
    return _load_probe_module(f"{PROBE_PACKAGE}.const", COMPONENT_ROOT / "const.py")


def _ensure_probe_package() -> None:
    """Create isolated package namespaces for relative imports."""
    package = sys.modules.get(PROBE_PACKAGE)
    if package is None:
        package = types.ModuleType(PROBE_PACKAGE)
        package.__path__ = [str(COMPONENT_ROOT)]  # type: ignore[attr-defined]
        sys.modules[PROBE_PACKAGE] = package
    for name, path in (
        ("capabilities", COMPONENT_ROOT / "capabilities"),
        ("core", COMPONENT_ROOT / "core"),
    ):
        module_name = f"{PROBE_PACKAGE}.{name}"
        if module_name not in sys.modules:
            module = types.ModuleType(module_name)
            module.__path__ = [str(path)]  # type: ignore[attr-defined]
            sys.modules[module_name] = module


def _load_probe_module(module_name: str, path: Path) -> Any:
    """Load one integration module inside the isolated probe namespace."""
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"{path.name} module is unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _client_timeout(timeout: int) -> Any:
    """Build aiohttp timeout lazily so fail-closed imports stay cheap."""
    from aiohttp import ClientTimeout

    return ClientTimeout(total=timeout)


def _default_page_size() -> int:
    """Return the configured Open API page size from HA-free constants."""
    const = _load_const_module()
    return int(getattr(const, "DEFAULT_THING_MANAGE_PAGE_SIZE", 200))


def _list_result(data: Mapping[str, Any]) -> list[dict[str, object]]:
    """Read common Open API list fields."""
    rows = data.get("result")
    if rows is None:
        rows = data.get("rows")
    if rows is None:
        rows = data.get("list")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _int_or_none(value: Any) -> int | None:
    """Parse optional total count values."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


__all__ = [
    "ProbeYeelightClient",
    "load_scan_login_contract",
    "load_yeelight_client",
]
