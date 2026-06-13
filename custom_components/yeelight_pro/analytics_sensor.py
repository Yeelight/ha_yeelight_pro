"""House-level analytics diagnostic sensors for Yeelight Pro."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import EntityCategory, UnitOfEnergy
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .core.analytics_coordinator import AnalyticsSnapshot, YeelightProAnalyticsCoordinator
from .device_display import suggested_entity_object_id
from .house_metadata import house_device_info
from .identity import entity_unique_id

_VALUE_EXTRACTOR = Callable[[AnalyticsSnapshot], Any]
_ATTRIBUTES_EXTRACTOR = Callable[[AnalyticsSnapshot], dict[str, Any]]


@dataclass(frozen=True, slots=True)
class AnalyticsSensorDescription(SensorEntityDescription):
    """Metadata for one house-level analytics sensor."""

    value: _VALUE_EXTRACTOR = lambda snapshot: None
    attributes: _ATTRIBUTES_EXTRACTOR = lambda snapshot: {}


ANALYTICS_SENSOR_DESCRIPTIONS: tuple[AnalyticsSensorDescription, ...] = (
    AnalyticsSensorDescription(
        key="alarm_total",
        name="报警总数",
        icon="mdi:alarm-light",
        value=lambda snapshot: _number(
            _nested(snapshot.alarm_analysis, "statInfo", "alarmNum")
        ),
        attributes=lambda snapshot: {
            "date_code": snapshot.date_code,
            "stat_info": snapshot.alarm_analysis.get("statInfo"),
            "device_info": snapshot.alarm_analysis.get("deviceInfo"),
            "trend": _sanitized_points(snapshot.alarm_trend),
        },
    ),
    AnalyticsSensorDescription(
        key="alarm_high_risk_count",
        name="高危设备数量",
        icon="mdi:alert-circle",
        value=lambda snapshot: len(snapshot.alarm_top),
        attributes=lambda snapshot: {
            "date_code": snapshot.date_code,
            "top_devices": _sanitized_points(snapshot.alarm_top),
        },
    ),
    AnalyticsSensorDescription(
        key="energy_total",
        name="用电量",
        icon="mdi:lightning-bolt",
        value=lambda snapshot: _number(
            _nested(snapshot.energy_analysis, "used", "usedCnt")
        ),
        attributes=lambda snapshot: {
            "date_code": snapshot.date_code,
            "used": snapshot.energy_analysis.get("used"),
            "saved": snapshot.energy_analysis.get("saved"),
            "carbon_emission_saved": snapshot.energy_analysis.get("carbonEmissionSaved"),
            "saved_rate": snapshot.energy_analysis.get("savedRate"),
            "trend": _sanitized_points(snapshot.energy_trend),
        },
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    ),
    AnalyticsSensorDescription(
        key="user_action_count",
        name="用户操作次数",
        icon="mdi:gesture-tap-button",
        value=lambda snapshot: _action_total(snapshot.user_actions.get("summary")),
        attributes=lambda snapshot: {
            "date_code": snapshot.day_code,
            "summary": snapshot.user_actions.get("summary"),
            "details": _sanitized_points(_list_value(snapshot.user_actions.get("details"))),
            "monthly": _sanitized_action_stats(snapshot.monthly_user_actions),
            "yearly": _sanitized_action_stats(snapshot.yearly_user_actions),
        },
    ),
)


class AnalyticsSensorCoordinator(Protocol):
    """analytics sensor 需要的 coordinator 最小结构。"""

    data: AnalyticsSnapshot | None
    house_id: int
    entry_data: dict[str, Any]
    houses: list[dict[str, Any]]


class YeelightProAnalyticsSensor(CoordinatorEntity, SensorEntity):
    """Yeelight Pro 房屋级数据分析诊断传感器。"""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: AnalyticsSensorCoordinator,
        description: AnalyticsSensorDescription,
    ) -> None:
        """初始化 analytics sensor。"""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = entity_unique_id(
            coordinator,
            "analytics",
            description.key,
        )
        self._attr_translation_key = f"analytics_{description.key}"
        self._attr_name = description.name
        self._attr_icon = description.icon
        self._attr_device_class = description.device_class
        self._attr_native_unit_of_measurement = description.native_unit_of_measurement
        self._attr_state_class = description.state_class

    @property
    def device_info(self) -> dict[str, Any]:
        """返回关联的家庭设备信息。"""
        return house_device_info(self.coordinator)

    @property
    def suggested_object_id(self) -> str | None:
        """返回 HA 首次注册时使用的友好实体 ID 建议。"""
        return suggested_entity_object_id(
            self.device_info,
            entity_name=self.entity_description.name,
            fallback_id=f"house_{self.coordinator.house_id}_analytics_{self.entity_description.key}",
        )

    @property
    def native_value(self) -> Any:
        """返回聚合诊断值。"""
        snapshot = self.coordinator.data
        return self.entity_description.value(snapshot) if snapshot is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """返回趋势和明细，避免把每个趋势点展开成实体。"""
        snapshot = self.coordinator.data
        if snapshot is None:
            return {}
        return {
            key: sanitized
            for key, value in self.entity_description.attributes(snapshot).items()
            if (sanitized := _sanitize_attribute_value(value)) not in (None, [], {})
        }


async def async_setup_analytics_sensors(
    analytics_coordinator: YeelightProAnalyticsCoordinator | None,
) -> list[YeelightProAnalyticsSensor]:
    """Build analytics sensors when cloud analytics is available."""
    if analytics_coordinator is None:
        return []
    coordinator = getattr(analytics_coordinator, "_main_coordinator", None)
    if coordinator is not None:
        remove_listener = analytics_coordinator.async_add_listener(
            lambda: setattr(coordinator, "analytics_data", analytics_coordinator.data)
        )
        entry = getattr(analytics_coordinator, "_config_entry", None)
        if entry is not None:
            entry.async_on_unload(remove_listener)
    return [
        YeelightProAnalyticsSensor(analytics_coordinator, description)
        for description in ANALYTICS_SENSOR_DESCRIPTIONS
    ]


def _sanitize_attribute_value(value: Any) -> Any:
    """Strip raw identifiers from analytics attributes recursively."""
    if isinstance(value, list):
        return [_sanitize_attribute_value(item) for item in value]
    if isinstance(value, dict):
        return {
            key: _sanitize_attribute_value(item)
            for key, item in value.items()
            if isinstance(key, str) and _is_safe_attribute_key(key)
        }
    return value


def _sanitized_points(points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return analytics points without raw device/location identifiers."""
    return [
        {
            key: value
            for key, value in point.items()
            if _is_safe_attribute_key(key)
        }
        for point in points
    ]


def _list_value(value: Any) -> list[dict[str, Any]]:
    """Return a list of dicts for optional analytics details."""
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _sanitized_action_stats(value: Any) -> dict[str, Any]:
    """Return monthly/yearly user-action summaries and trends without identifiers."""
    if not isinstance(value, dict):
        return {}
    result: dict[str, Any] = {}
    summary = _sanitize_attribute_value(value.get("summary"))
    if isinstance(summary, dict) and summary:
        result["summary"] = summary
    details = _sanitized_points(_list_value(value.get("details")))
    if details:
        result["details"] = details
    return result


def _is_safe_attribute_key(key: str) -> bool:
    """Return false for raw identifiers that should not be exposed as attributes."""
    normalized = key.replace("_", "").lower()
    return not (
        normalized.endswith("id")
        or normalized.endswith("ids")
        or normalized in {
            "deviceid",
            "deviceids",
            "roomid",
            "roomids",
            "areaid",
            "areaids",
            "houseid",
            "houseids",
            "gatewayid",
            "gatewayids",
        }
    )


def _nested(data: dict[str, Any], *keys: str) -> Any:
    """Read a nested analytics value."""
    value: Any = data
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _number(value: Any) -> int | float | None:
    """Normalize Open API numeric strings for HA sensor states."""
    if isinstance(value, bool) or value in (None, ""):
        return None
    if isinstance(value, int | float):
        return value
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return int(number) if number.is_integer() else number


def _action_total(summary: Any) -> int | None:
    """Sum documented user action counters from one summary object."""
    if not isinstance(summary, dict):
        return None
    total = 0
    for key in ("cNum", "ctNum", "lNum", "sceneNum", "pOnNum", "pOffNum"):
        value = _number(summary.get(key))
        if isinstance(value, int | float):
            total += int(value)
    return total
