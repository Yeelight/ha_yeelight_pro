"""Shared helpers for Yeelight Pro scene rows."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .utils import to_str


def scene_row_id(scene: Mapping[str, Any]) -> str | None:
    """Return the executable Yeelight scene id from API row variants."""
    return to_str(
        scene.get("id")
        or scene.get("sceneId")
        or scene.get("scene_id")
    )


def scene_row_name(scene: Mapping[str, Any], scene_id: str) -> str:
    """Return a user-facing scene name with a stable fallback."""
    return to_str(scene.get("name") or scene.get("sceneName") or scene.get("scene_name")) or (
        f"场景 {scene_id}"
    )


__all__ = ["scene_row_id", "scene_row_name"]
