"""Entity-level error helpers for Yeelight Pro service calls."""

from __future__ import annotations

from typing import NoReturn

from homeassistant.exceptions import HomeAssistantError

from .core.exceptions import safe_error_summary


def raise_service_error(action: str, err: BaseException) -> NoReturn:
    """Raise a sanitized Home Assistant service error."""
    summary = safe_error_summary(err)
    raise HomeAssistantError(
        f"Yeelight Pro service failed: {action}: {summary}"
    ) from None
