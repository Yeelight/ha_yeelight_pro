"""Import compatibility tests for projector public facades."""


def test_projector_light_old_import_path() -> None:
    """projector.light 必须继续导出旧路径对象."""
    from custom_components.yeelight_pro.projector.light import (
        HALightProjection,
        LIGHT_COLOR_MODE_HINT_KEY,
        NumericRange,
        project_light,
    )

    assert NumericRange.__name__ == "NumericRange"
    assert HALightProjection.__name__ == "HALightProjection"
    assert LIGHT_COLOR_MODE_HINT_KEY == "light_color_mode"
    assert callable(project_light)


def test_projector_fan_old_import_path() -> None:
    """projector.fan 必须继续导出旧路径对象."""
    from custom_components.yeelight_pro.projector.fan import (
        HAFanProjection,
        NumericRange,
        project_fans,
    )

    assert NumericRange.__name__ == "NumericRange"
    assert HAFanProjection.__name__ == "HAFanProjection"
    assert callable(project_fans)


def test_projector_switch_old_import_path() -> None:
    """projector.switch 必须继续导出旧路径对象."""
    from custom_components.yeelight_pro.projector.switch import (
        HASwitchProjection,
        project_switches,
    )

    assert HASwitchProjection.__name__ == "HASwitchProjection"
    assert callable(project_switches)


def test_projector_event_old_import_path() -> None:
    """projector.event 必须继续导出旧路径对象."""
    from custom_components.yeelight_pro.projector.event import (
        HADeviceTriggerProjection,
        HAEventProjection,
        project_device_triggers,
        project_events,
    )

    assert HADeviceTriggerProjection.__name__ == "HADeviceTriggerProjection"
    assert HAEventProjection.__name__ == "HAEventProjection"
    assert callable(project_device_triggers)
    assert callable(project_events)


def test_projector_sensor_old_import_path() -> None:
    """projector.sensor 必须继续导出旧路径对象."""
    from custom_components.yeelight_pro.projector.sensor import (
        HASensorProjection,
        project_sensors,
    )

    assert HASensorProjection.__name__ == "HASensorProjection"
    assert callable(project_sensors)


def test_projector_package_public_exports() -> None:
    """projector 包聚合导出必须保持稳定."""
    from custom_components.yeelight_pro.projector import (
        HADeviceTriggerProjection,
        HAEventProjection,
        HAFanProjection,
        HALightProjection,
        HASwitchProjection,
        LIGHT_COLOR_MODE_HINT_KEY,
        project_device_triggers,
        project_events,
        project_fans,
        project_light,
        project_switches,
    )

    assert HADeviceTriggerProjection.__name__ == "HADeviceTriggerProjection"
    assert HAEventProjection.__name__ == "HAEventProjection"
    assert HAFanProjection.__name__ == "HAFanProjection"
    assert HALightProjection.__name__ == "HALightProjection"
    assert HASwitchProjection.__name__ == "HASwitchProjection"
    assert LIGHT_COLOR_MODE_HINT_KEY == "light_color_mode"
    assert callable(project_device_triggers)
    assert callable(project_events)
    assert callable(project_fans)
    assert callable(project_light)
    assert callable(project_switches)
