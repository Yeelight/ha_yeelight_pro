"""Yeelight IoT 首版静态能力数据.

数据整理自 docs/iot 下的品类、组件、属性、事件和连接协议资料。
当前只内置 HA 投影需要的高频能力，低频组件保留在文档资料中。
"""

from __future__ import annotations

from .models import (
    IoTCategorySpec,
    IoTComponentSpec,
    IoTEventSpec,
    IoTPropertySpec,
    IoTProtocolSpec,
    PropertyCapability,
)


IOT_CATEGORY_SPECS: tuple[IoTCategorySpec, ...] = (
    IoTCategorySpec("light", 1, "灯类", "light", "照明设备"),
    IoTCategorySpec("contact_sensor", 2, "接触式传感器类", "binary_sensor", "门磁和接触检测"),
    IoTCategorySpec("human_sensor", 3, "人体感应传感器类", "binary_sensor", "人体移动或存在检测"),
    IoTCategorySpec("light_sensor", 4, "环境光传感器类", "sensor", "照度检测"),
    IoTCategorySpec("curtain", 5, "窗帘类", "cover", "窗帘和梦幻帘"),
    IoTCategorySpec("temp_control", 6, "温控类", "climate", "空调、地暖、新风和温控器"),
    IoTCategorySpec("relay_switch", 7, "继电器开关类", "switch", "继电器、墙壁开关和插卡取电"),
    IoTCategorySpec("scene_panel", 8, "情景面板类", "event", "情景按键和面板事件"),
    IoTCategorySpec("other", 9, "其他类", "sensor", "仅明确属性降级为诊断或传感器"),
    IoTCategorySpec("gateway", 10, "网关类", None, "拓扑父设备和连接诊断"),
    IoTCategorySpec("knob_switch", 11, "旋钮开关类", "event", "旋钮事件输入"),
)


IOT_COMPONENT_SPECS: tuple[IoTComponentSpec, ...] = (
    IoTComponentSpec(1, "gateway", "网关", "gateway", "global", "sensor", ("fm", "lf", "pl", "li", "lc", "cpt")),
    IoTComponentSpec(2, "switch light", "开关灯", "light", "normal", "light", ("p",)),
    IoTComponentSpec(3, "brightness light", "亮度灯", "light", "normal", "light", ("p", "l")),
    IoTComponentSpec(4, "color temperature light", "色温灯", "light", "normal", "light", ("p", "l", "ct")),
    IoTComponentSpec(5, "color light", "彩光灯", "light", "normal", "light", ("p", "l", "ct", "c", "m")),
    IoTComponentSpec(7, "human detection sensor", "人感传感器", "human_sensor", "normal", "binary_sensor", ("mv",), ("motion_detected", "motion_undetected")),
    IoTComponentSpec(9, "human occupancy sensor", "人在传感器", "human_sensor", "normal", "binary_sensor", ("mv",), ("motion_detected", "motion_undetected")),
    IoTComponentSpec(10, "human illuminance sensor", "光照传感器2", "light_sensor", "normal", "sensor", ("mv", "blp", "li")),
    IoTComponentSpec(12, "curtain", "窗帘", "curtain", "normal", "cover", ("cp", "tp", "rd", "li")),
    IoTComponentSpec(16, "wireless switch channel", "无线开关通道", "relay_switch", "normal", "switch", ("l", "sp"), ("click", "hold")),
    IoTComponentSpec(17, "knob switch", "旋钮开关", "knob_switch", "normal", "event", (), ("knob_spin",)),
    IoTComponentSpec(18, "scene control button", "情景按键", "scene_panel", "normal", "button", ("p", "m"), ("click", "hold")),
    IoTComponentSpec(19, "air conditioner", "空调", "temp_control", "normal", "climate", ("acp", "acm", "actt", "acf", "acct")),
    IoTComponentSpec(20, "switch control", "开关", "relay_switch", "normal", "switch", ("p",), ("click", "hold")),
    IoTComponentSpec(21, "contact sensor", "接触式传感器", "contact_sensor", "normal", "binary_sensor", ("alm", "dc"), ("door_open", "door_close", "door_alarm", "door_normal")),
    IoTComponentSpec(23, "human body infrared sensor", "人体红外传感器", "human_sensor", "normal", "binary_sensor", ("mv", "luminance"), ("motion_detected", "motion_undetected", "human_enter", "human_leave")),
    IoTComponentSpec(24, "ambient light sensor", "环境光传感器", "light_sensor", "normal", "sensor", ("luminance",)),
    IoTComponentSpec(39, "zebra blinds", "梦幻帘", "curtain", "normal", "cover", ("cp", "tp", "li")),
    IoTComponentSpec(42, "fresh air", "新风", "temp_control", "normal", "fan", ("vmcp", "vmcf")),
    IoTComponentSpec(43, "floor heating", "地暖", "temp_control", "normal", "climate", ("rfhp", "rfhct", "rfhtt")),
    IoTComponentSpec(44, "basic", "基础组件", None, "global", "sensor", ("o",)),
    IoTComponentSpec(48, "battery", "电池组件", None, "global", "sensor", ("bl", "bc", "bcg")),
    IoTComponentSpec(59, "angle color temperature light", "角度色温灯", "light", "normal", "light", ("p", "l", "ct")),
    IoTComponentSpec(63, "temp control", "温控器组件", "temp_control", "normal", "climate", ("p", "t", "tgt", "fa", "he")),
    IoTComponentSpec(66, "dali energy", "dali能量组件", None, "global", "sensor", ("ap", "ae", "ot", "sys_s", "esv", "esvf", "temp", "ocp", "lsot", "lsv", "lsc", "pf")),
    IoTComponentSpec(67, "dali scene control button", "dali情景按键", "scene_panel", "normal", "button", ("ep", "st", "rt"), ("click", "hold")),
    IoTComponentSpec(68, "dali human detection sensor", "dali人感传感器", "human_sensor", "normal", "binary_sensor", ("mv",)),
    IoTComponentSpec(69, "dali illuminance sensor", "dali光感传感器", "light_sensor", "normal", "sensor", ("luminance",)),
    IoTComponentSpec(71, "dali knob switch", "dali旋钮开关组件", "knob_switch", "normal", "event", ("ep", "rt")),
    IoTComponentSpec(72, "color light without temperature", "无色温彩光灯组件", "light", "normal", "light", ("p", "l", "c")),
    IoTComponentSpec(76, "power meter", "电量组件", None, "global", "sensor", ("curp", "iec")),
)


IOT_PROPERTY_SPECS: tuple[IoTPropertySpec, ...] = (
    IoTPropertySpec("p", "power", "bool", "read_write", "application", "device", PropertyCapability("p", control_key="power"), ("switch control", "switch light", "brightness light", "color temperature light", "color light", "color light without temperature")),
    IoTPropertySpec("sp", "switch power", "bool", "read_write", "application", "device", PropertyCapability("sp", control_key="switch_power"), ("wireless switch channel",)),
    IoTPropertySpec("o", "online", "bool", "read", "application", "gateway", PropertyCapability("o", control_key="online"), ("basic",)),
    IoTPropertySpec("l", "brightness", "int", "read_write", "application", "device", PropertyCapability("l", unit="%", control_key="brightness"), ("brightness light", "color temperature light", "color light", "color light without temperature", "wireless switch channel"), value_range=(1, 100, 1)),
    IoTPropertySpec("ct", "color temperature", "int", "read_write", "application", "device", PropertyCapability("ct", unit="K", control_key="color_temperature"), ("color temperature light", "color light"), unit="K", value_range=(2700, 6500, None)),
    IoTPropertySpec("c", "color", "int", "read_write", "application", "device", PropertyCapability("c", unit="rgb", control_key="rgb_color"), ("color light", "color light without temperature")),
    IoTPropertySpec("c_waf", "waf color", "string", "read_write", "application", "device", PropertyCapability("c_waf", control_key="waf_color")),
    IoTPropertySpec("c_xy", "xy color", "string", "read_write", "application", "device", PropertyCapability("c_xy", control_key="xy_color")),
    IoTPropertySpec("m", "mode", "enum", "read", "application", "device", components=("color light", "scene control button")),
    IoTPropertySpec("t", "current temperature", "int", "read", "application", "device", PropertyCapability("t", device_class="temperature", unit="°C"), ("temp control",), unit="°C"),
    IoTPropertySpec("temp", "temperature", "int", "read", "application", "device", PropertyCapability("temp", device_class="temperature", unit="°C"), unit="°C"),
    IoTPropertySpec("h", "humidity", "int", "read", "application", "device", PropertyCapability("h", device_class="humidity", unit="%"), unit="%"),
    IoTPropertySpec("luminance", "luminance", "int", "read", "application", "device", PropertyCapability("luminance", device_class="illuminance", unit="lx"), ("ambient light sensor", "human body infrared sensor", "dali illuminance sensor"), unit="lx"),
    IoTPropertySpec("mv", "motion", "bool", "read", "application", "device", PropertyCapability("mv", device_class="motion"), ("human detection sensor", "human occupancy sensor", "human body infrared sensor")),
    IoTPropertySpec("dc", "door closed", "bool", "read", "application", "device", PropertyCapability("dc", device_class="door"), ("contact sensor",)),
    IoTPropertySpec("alm", "alarm", "bool", "read", "application", "device", PropertyCapability("alm", device_class="tamper"), ("contact sensor",)),
    IoTPropertySpec("tp", "target position", "int", "read_write", "application", "device", PropertyCapability("tp", unit="%", control_key="target_position"), ("curtain", "zebra blinds"), unit="%", value_range=(0, 100, 1)),
    IoTPropertySpec("cp", "current position", "int", "read", "application", "device", PropertyCapability("cp", unit="%", control_key="current_position"), ("curtain", "zebra blinds"), unit="%"),
    IoTPropertySpec("actt", "ac target temperature", "int", "read_write", "application", "device", PropertyCapability("actt", device_class="temperature", unit="°C", control_key="target_temperature"), ("air conditioner",), unit="°C"),
    IoTPropertySpec("acct", "ac current temperature", "int", "read", "application", "device", PropertyCapability("acct", device_class="temperature", unit="°C"), ("air conditioner",), unit="°C"),
    IoTPropertySpec("acp", "ac power", "bool", "read_write", "application", "device", PropertyCapability("acp", control_key="climate_power"), ("air conditioner",)),
    IoTPropertySpec("acm", "ac mode", "int", "read_write", "application", "device", components=("air conditioner",)),
    IoTPropertySpec("acf", "ac fan", "int", "read_write", "application", "device", PropertyCapability("acf", control_key="fan_speed"), ("air conditioner",)),
    IoTPropertySpec("blp", "backlight power", "bool", "read_write", "application", "device", components=("human illuminance sensor",)),
    IoTPropertySpec("rd", "reverse direction", "int", "read_write", "config", "device", components=("curtain", "zebra blinds")),
    IoTPropertySpec("li", "indicator switch", "int", "read_write", "config", "device", components=("gateway", "human illuminance sensor", "curtain", "zebra blinds")),
    IoTPropertySpec("lc", "lan control", "int", "read_write", "config", "gateway", components=("gateway",)),
    IoTPropertySpec("pl", "physical link", "int", "read", "config", "gateway", components=("gateway",)),
    IoTPropertySpec("lf", "up time", "int", "read", "config", "gateway", components=("gateway",)),
    IoTPropertySpec("fm", "memory free", "int", "read", "config", "gateway", components=("gateway",)),
    IoTPropertySpec("cpt", "connectivity protocols type", "int", "read", "config", "gateway", components=("gateway",)),
    IoTPropertySpec("vmcp", "fresh air power", "bool", "read_write", "application", "device", components=("fresh air",)),
    IoTPropertySpec("vmcf", "fresh air fan speed", "int", "read_write", "application", "device", components=("fresh air",)),
    IoTPropertySpec("rfhp", "floor heating power", "bool", "read_write", "application", "device", PropertyCapability("rfhp", control_key="floor_heating_power"), ("floor heating",)),
    IoTPropertySpec("rfhct", "floor heating current temperature", "int", "read", "application", "device", PropertyCapability("rfhct", device_class="temperature", unit="°C"), ("floor heating",), unit="°C"),
    IoTPropertySpec("rfhtt", "floor heating target temperature", "int", "read_write", "application", "device", PropertyCapability("rfhtt", device_class="temperature", unit="°C", control_key="target_temperature"), ("floor heating",), unit="°C"),
    IoTPropertySpec("curp", "current power", "int", "read", "application", "device", PropertyCapability("curp", device_class="power", unit="W"), ("power meter",), unit="W"),
    IoTPropertySpec("ap", "active power", "int", "read", "application", "device", PropertyCapability("ap", device_class="power", unit="W"), ("dali energy",), unit="W"),
    IoTPropertySpec("ae", "active energy", "int", "read", "application", "device", PropertyCapability("ae", device_class="energy", unit="Wh"), ("dali energy",), unit="Wh"),
    IoTPropertySpec("iec", "energy consumption", "int", "read", "application", "device", PropertyCapability("iec", device_class="energy", unit="Wh"), ("power meter",), unit="Wh"),
    IoTPropertySpec("ot", "operating time", "int", "read", "application", "gateway", components=("dali energy",), unit="s"),
    IoTPropertySpec("sys_s", "system starts", "int", "read", "application", "gateway", components=("dali energy",)),
    IoTPropertySpec("esv", "external supply voltage", "int", "read", "application", "gateway", components=("dali energy",), unit="0.1V"),
    IoTPropertySpec("esvf", "external supply voltage frequency", "int", "read", "application", "gateway", components=("dali energy",), unit="Hz"),
    IoTPropertySpec("ocp", "output current percent", "int", "read", "application", "gateway", components=("dali energy",), unit="%"),
    IoTPropertySpec("lsot", "light source on time", "int", "read", "application", "gateway", components=("dali energy",), unit="s"),
    IoTPropertySpec("lsv", "light source voltage", "int", "read", "application", "gateway", components=("dali energy",), unit="0.1V"),
    IoTPropertySpec("lsc", "light source current", "int", "read", "application", "gateway", components=("dali energy",), unit="mA"),
    IoTPropertySpec("pf", "power factor", "int", "read", "application", "gateway", components=("dali energy",)),
    IoTPropertySpec("bl", "battery level", "int", "read", "application", "device", PropertyCapability("bl", device_class="battery", unit="%"), ("battery",), unit="%", value_range=(0, 100, 1)),
    IoTPropertySpec("bc", "battery chargeable", "bool", "read", "application", "device", components=("battery",)),
    IoTPropertySpec("bcg", "battery charging", "bool", "read", "application", "device", components=("battery",)),
    IoTPropertySpec("lv", "fan level", "int", "read_write", "application", "device", PropertyCapability("lv", control_key="fan_level")),
    IoTPropertySpec("tgt", "target temperature", "int", "read_write", "application", "device", components=("temp control",), unit="°C", value_range=(0, 50, 1)),
    IoTPropertySpec("fa", "fan mode", "enum", "read_write", "application", "device", components=("temp control",)),
    IoTPropertySpec("he", "heating mode", "enum", "read_write", "application", "device", components=("temp control",)),
    IoTPropertySpec("ep", "event priority", "int", "read_write", "config", "gateway", components=("dali scene control button", "dali knob switch")),
    IoTPropertySpec("st", "short timers", "int", "read_write", "config", "gateway", components=("dali scene control button",)),
    IoTPropertySpec("rt", "repeat timers", "int", "read_write", "config", "gateway", components=("dali scene control button", "dali knob switch")),
)


IOT_EVENT_SPECS: tuple[IoTEventSpec, ...] = (
    IoTEventSpec("点击", "click", 1, "面板点击", ("keyclick", "key_click", "single_click", "click", "panel.click"), ("wireless switch channel", "scene control button", "switch control", "dali scene control button")),
    IoTEventSpec("长按", "hold", 2, "面板长按", ("longpress", "long_press", "keyhold", "hold", "panel.hold"), ("wireless switch channel", "scene control button", "switch control", "dali scene control button")),
    IoTEventSpec("按住后松开", "release_after_hold", 3, "按住后松开", ("releaseafterhold", "release_after_hold", "release_after_long_press", "keyreleaseafterlongpress", "panel.release")),
    IoTEventSpec("分离", "door_open", 4, "接触传感器打开", ("dooropen", "door_open", "contact.open"), ("contact sensor",)),
    IoTEventSpec("接触", "door_close", 5, "接触传感器闭合", ("doorclose", "door_close", "contact.close"), ("contact sensor",)),
    IoTEventSpec("告警", "door_alarm", 6, "接触传感器告警", ("dooralarm", "door_alarm", "contact.alarm"), ("contact sensor",)),
    IoTEventSpec("告警恢复正常", "door_normal", 7, "接触传感器恢复正常", ("doornormal", "door_normal", "contact.normal"), ("contact sensor",)),
    IoTEventSpec("有人移动", "motion_detected", 8, "人体移动", ("motiontrue", "motion_true", "motiondetected", "motion_detected", "motion.true"), ("human detection sensor", "human occupancy sensor")),
    IoTEventSpec("无人移动", "motion_undetected", 9, "无人移动", ("motionfalse", "motion_false", "motionundetected", "motion_undetected", "motion.false"), ("human detection sensor", "human occupancy sensor")),
    IoTEventSpec("旋转", "knob_spin", 10, "旋钮旋转", ("freespin", "free_spin", "holdspin", "hold_spin", "knobspin", "knob_spin", "knob.spin", "spin", "rotate"), ("knob switch",)),
    IoTEventSpec("传感器报警", "power_alarm", 14, "传感器报警", ("poweralarm", "power_alarm")),
    IoTEventSpec("传感器正常", "power_normal", 15, "传感器恢复正常", ("powernormal", "power_normal")),
    IoTEventSpec("有人进入", "human_enter", 22, "有人进入", ("humanenter", "human_enter", "human enter", "approach.true"), ("human body infrared sensor",)),
    IoTEventSpec("有人离开", "human_leave", 23, "有人离开", ("humanleave", "human_leave", "human leave", "approach.false"), ("human body infrared sensor",)),
    IoTEventSpec("多圈旋转", "multi_spin", None, "多圈旋转", ("multispin", "multi_spin")),
    IoTEventSpec("绝对旋转", "absolut_spin", None, "绝对旋转", ("absolutspin", "absolut_spin", "absolute_spin")),
)


IOT_PROTOCOL_SPECS: tuple[IoTProtocolSpec, ...] = (
    IoTProtocolSpec(-1, "none", "不连接", "不通过 Yeelight IoT 网络连接"),
    IoTProtocolSpec(0, "direct", "直连", "网关、屏幕或直连设备"),
    IoTProtocolSpec(1, "mesh", "mesh协议", "蓝牙 Mesh 设备或桥接协议", bridge_protocol=True),
    IoTProtocolSpec(2, "matter", "matter协议", "Matter 桥接元数据", bridge_protocol=True),
    IoTProtocolSpec(3, "dali", "dali协议", "DALI 网关和 DALI 输入/照明设备", bridge_protocol=True),
    IoTProtocolSpec(4, "thread", "thread协议", "Thread 桥接元数据", bridge_protocol=True),
)


NODE_TYPE_MAP: dict[str, int] = {
    "room": 1,
    "device": 2,
    "area": 3,
    "group": 4,
    "house": 5,
}
