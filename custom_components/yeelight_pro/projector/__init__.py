"""Yeelight Pro 投影模块.

将 canonical 数据投影为 Home Assistant 实体结构。
"""

from .binary_sensor import HABinarySensorProjection, project_binary_sensors
from .climate import HAClimateProjection, project_climate
from .cover import HACoverProjection, project_cover
from .device import (
    flatten_instance_state,
    project_device_info,
    project_device_info_model,
    project_payload_device_info,
)
from .event import HAEventProjection, HADeviceTriggerProjection, project_device_triggers, project_events
from .fan import HAFanProjection, project_fans
from .light import HALightProjection, LIGHT_COLOR_MODE_HINT_KEY, project_light
from .lock import HALockProjection, project_lock
from .sensor import HASensorProjection, project_sensors
from .switch import HASwitchProjection, project_switches
from .vacuum import HAVacuumProjection, project_vacuum

__all__ = [
    "flatten_instance_state",
    "HABinarySensorProjection",
    "HAClimateProjection",
    "HACoverProjection",
    "HADeviceTriggerProjection",
    "HAFanProjection",
    "HAEventProjection",
    "HALightProjection",
    "HALockProjection",
    "HASensorProjection",
    "HASwitchProjection",
    "HAVacuumProjection",
    "LIGHT_COLOR_MODE_HINT_KEY",
    "project_binary_sensors",
    "project_climate",
    "project_cover",
    "project_device_info",
    "project_device_info_model",
    "project_payload_device_info",
    "project_device_triggers",
    "project_events",
    "project_fans",
    "project_light",
    "project_lock",
    "project_sensors",
    "project_switches",
    "project_vacuum",
]
