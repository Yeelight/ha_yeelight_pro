"""Shared constants for switch projection helpers."""

from __future__ import annotations

import re

RAW_SWITCH_KEY_RE = re.compile(r"^(?P<index>\d+)-(?P<prop>p|sp)$")

__all__ = ["RAW_SWITCH_KEY_RE"]
