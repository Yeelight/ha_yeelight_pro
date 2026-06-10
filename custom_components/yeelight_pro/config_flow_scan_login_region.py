"""Shared region guard for Yeelight APP scan-login config flows."""
from __future__ import annotations

from .scan_login_contract import YeelightAccountToken, normalize_cloud_region


def scan_login_token_matches_region(
    token: YeelightAccountToken | None,
    selected_region: str,
) -> bool:
    """Return whether a scan-login token can be used for the selected region."""
    token_region = token.region if token is not None else ""
    if not token_region:
        return True
    try:
        return normalize_cloud_region(selected_region) == normalize_cloud_region(
            token_region
        )
    except Exception:
        return False


__all__ = ["scan_login_token_matches_region"]
