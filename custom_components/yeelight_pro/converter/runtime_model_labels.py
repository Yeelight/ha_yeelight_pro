"""Runtime-inferred model labels derived from capability evidence."""

from __future__ import annotations

_CAPABILITY_MODEL_LABELS = {
    "contact_sensor": "门磁传感器",
    "human_sensor": "人体传感器",
    "light_sensor": "照度传感器",
    "curtain": "窗帘",
    "temp_control": "温控设备",
    "relay_switch": "开关控制器",
    "knob_switch": "旋钮开关",
    "scene_panel": "情景面板",
}


def capability_model_name(runtime_category: str | None, fallback: str) -> str:
    """Return a concrete model label from runtime capability evidence."""
    if runtime_category in _CAPABILITY_MODEL_LABELS:
        return _CAPABILITY_MODEL_LABELS[runtime_category]
    return runtime_category or fallback


__all__ = ["capability_model_name"]
