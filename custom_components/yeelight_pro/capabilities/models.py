"""Yeelight IoT 能力注册表模型."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class IoTCategorySpec:
    """Yeelight IoT 品类定义."""

    category: str
    category_id: int
    name: str
    platform: str | None
    description: str


@dataclass(frozen=True, slots=True)
class IoTComponentSpec:
    """Yeelight IoT 组件定义."""

    component_id: int
    alias: str
    name: str
    category: str | None
    component_type: str
    platform_hint: str | None = None
    properties: tuple[str, ...] = ()
    events: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PropertyCapability:
    """一个属性在 Home Assistant 中的含义."""

    prop: str
    device_class: str | None = None
    unit: str | None = None
    control_key: str | None = None


@dataclass(frozen=True, slots=True)
class IoTPropertySpec:
    """Yeelight IoT 属性定义."""

    prop: str
    full_name: str
    data_type: str
    access: str
    category: str
    handler: str
    capability: PropertyCapability | None = None
    components: tuple[str, ...] = ()
    unit: str | None = None
    value_range: tuple[int | float | None, int | float | None, int | float | None] | None = None
    value_list: Mapping[str, Any] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        """冻结枚举值映射，避免运行期被意外修改."""
        object.__setattr__(self, "value_list", MappingProxyType(dict(self.value_list)))

    @property
    def readable(self) -> bool:
        """属性是否可读."""
        access = self.access.lower()
        return "read" in access or "读" in self.access

    @property
    def writable(self) -> bool:
        """属性是否可写."""
        access = self.access.lower()
        return "write" in access or "写" in self.access

    @property
    def description(self) -> str | None:
        """返回易来 CSV 中的官方中文描述."""
        return IOT_PROPERTY_DESCRIPTIONS.get(self.prop)

    @property
    def display_name(self) -> str:
        """返回适合 Home Assistant 展示的属性名称."""
        if self.description:
            return _clean_property_description(self.description)
        return self.full_name or self.prop


@dataclass(frozen=True, slots=True)
class IoTEventSpec:
    """Yeelight IoT 事件定义."""

    event_type: str
    normalized: str
    event_id: int | None = None
    description: str | None = None
    aliases: tuple[str, ...] = ()
    components: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class IoTProtocolSpec:
    """Yeelight IoT 连接协议定义."""

    protocol_id: int
    key: str
    name: str
    description: str
    bridge_protocol: bool = False


@dataclass(frozen=True, slots=True)
class IoTProductSpec:
    """Yeelight IoT 产品构成定义."""

    pid: int
    name: str
    global_components: tuple[str, ...]
    normal_components: tuple[str, ...]
    normal_component_count: str | None
    protocol: str | None
    bridge_protocols: tuple[str, ...] = ()
    normal_component_counts: tuple[tuple[str, int], ...] = ()


@dataclass(frozen=True, slots=True)
class ControlKey:
    """组件属性控制 key 解析结果."""

    component_index: int | None
    prop_name: str


def _clean_property_description(value: str) -> str:
    """把 CSV 描述裁成适合实体名的短标签."""
    text = str(value).strip()
    for separator in ("（", "(", "，", ",", "；", ";", "：", ":"):
        text = text.split(separator, 1)[0].strip()
    return text or value


IOT_PROPERTY_DESCRIPTIONS: Mapping[str, str] = MappingProxyType({
    "3rdPartySyncBitmask": "同步三方设定",
    "acct": "空调当前温度",
    "acd": "延时开关剩余时间（毫秒）",
    "acdfltr": "空调挡风板角度",
    "acf": "空调风速",
    "acm": "空调模式",
    "aco": "是否在线",
    "acp": "空调开关",
    "acrc": "儿童锁",
    "actt": "空调设定目标温度",
    "ae": "总有功",
    "alm": "告警（是否被拆）",
    "angle": "光束角",
    "ap": "有功功率",
    "bc": "是否可充电",
    "bcg": "电池正在充电",
    "bhm": "浴霸模式（1:干燥 2:除雾 3:快速除雾 4:极速加热 5:其他模式）",
    "bl": "当前电量",
    "blp": "背光灯开关",
    "bp": "上电后状态",
    "c": "颜色",
    "c_n_c": "组件数目设置",
    "ch_num": "组件数目",
    "cp": "当前开合度",
    "cpt": "当前接入协议",
    "cra": "当前旋转角度",
    "ct": "色温",
    "ct_rdy": "是否支持色温",
    "curp": "当前功率",
    "dali_hds_cnt": "dali设备的人感组件数量",
    "dali_is_cnt": "dali设备的光感组件数量",
    "dali_scb_cnt": "dali设备的按键组件数量",
    "dc": "是否接触",
    "dd": "默认渐变时长",
    "ddt": "dali dt",
    "delay_time": "延时时间",
    "dev_alarm": "设备异常告警信息 具体内容网关自行设置",
    "deviceKey": "设备key",
    "dim_curve": "功率亮度曲线：0表示对数函数，1表示线性函数",
    "dntm": "夜间模式（设备专用）",
    "do": "延时关闭（0-120min）",
    "dpt": "dali开关类型 1 默认模式，2 亮度模式",
    "dt": "是否支持手拉",
    "dver": "DALI版本",
    "ebl": "环境亮度等级",
    "eip": "外网ip",
    "esv": "供电电压 单位0.1V",
    "esvf": "供电电压频率 单位Hz",
    "extend": "投射配置",
    "fa": "风扇档位：0: 关闭, 1: 低档, 2: 中档, 3: 高档",
    "fade_rate": "渐变步长",
    "fblck": "重置锁定开关",
    "fbnum": "重置次数",
    "fm": "剩余内存",
    "fv": "固件版本号",
    "gtin": "gtin",
    "hb_interval": "心跳间隔（暂未使用）",
    "he": "加热档位：0: 关闭, 1: 低档, 2: 中档, 3: 高档",
    "height": "高度",
    "hk": "当前网关是否已入网绑定到HomeKit",
    "hr_all_nodes_sync_state": "三方同步到海尔设备状态",
    "hr_all_scenes_sync_state": "三方情景同步到海尔状态",
    "hr_login": "海尔云是否连接",
    "hrbk": "通过海尔智家oauth获取到的用户token",
    "hrdm": "海尔云平台连接域名",
    "hrln": "设备绑定到海尔云状态",
    "hrpt": "海尔云平台连接端口",
    "icon": "图标",
    "iec": "阶段电量，默认5分钟",
    "io": "是否为输入/输出组件，enum values {dummy, input, output, inout}, 后台定义组件时自动计算",
    "ip": "ip地址",
    "jdef": "点动默认状态",
    "jen": "是否开启点动",
    "jtm": "点动持续时间",
    "keys_visible": "按键是否显示",
    "l": "亮度",
    "lc": "局域网控制开关",
    "level_limit_rdy": "是否支持功率限制",
    "lf": "上电时间",
    "li": "指示灯开关",
    "life": "设备预期寿命 单位小时",
    "lsc": "输出电流 单位mA",
    "lsot": "开灯时长 单位秒",
    "lsv": "输出电压 单位0.1V",
    "ltk": "本地key",
    "lumi_setting": "照度设置",
    "luminance": "照度",
    "m": "模式（2-色温 1-色彩）",
    "mac": "mac地址",
    "max_level": "设备的最大输出等级",
    "mei_all_nodes_sync_state": "网关同步时子设备同步状态",
    "mei_all_scenes_sync_state": "美的情景同步状态",
    "mei_did": "美的设备id",
    "mei_info": "美的设备身份信息",
    "mei_login": "当前网关是否已登录到美的云",
    "meibk": "bindkey",
    "meiln": "当前网关是否已入网绑定到美的云",
    "mfl": "当前网关是否已入网绑定到matter",
    "mibk": "mi bind key, Yeelight Pro mesh 网关在米家的 bind key",
    "micd": "mi country domain, Yeelight Pro mesh 网关在米家的 country domain",
    "midk": "mi device key, Yeelight Pro mesh 网关的在米家的device key",
    "miid": "mi did, Yeelight Pro mesh 网关在米家的 did",
    "miln": "mi linked, Yeelight Pro mesh网关是否绑定米家标志",
    "mimac": "小米mac地址",
    "min_level": "设备的最小输出等级",
    "mock": "mock成什么",
    "mp": "互斥锁",
    "mp_buttons": "多功能屏的主屏快捷键配置信息",
    "mp_devices": "多功能屏中投射的子设备配置信息",
    "mp_keys": "多功能屏的情景按键配置信息",
    "mp_nightmode": "多功能屏-复杂逻辑使用",
    "mp_scenes": "多功能屏设备情景按键列表",
    "mpml": "音乐播放器歌单ID",
    "mpmp": "音乐播放器播放/暂停",
    "mpmr": "音乐播放器音乐律动",
    "mppm": "音乐播放器播放模式",
    "mv": "有人经过",
    "name": "名称",
    "nightMode": "夜间模式配置",
    "ntDelay": "夜间模式延时",
    "ntEnd": "夜间模式结束时间",
    "ntOn": "是否开启夜间",
    "ntScreenMode": "屏保模式",
    "ntStart": "夜间模式开启时间",
    "o": "是否在线",
    "ocp": "输出电流百分比",
    "open_type": "开启方向",
    "ot": "系统运行时间 单位秒",
    "p": "开关",
    "pe": "终点是否设定",
    "pf": "功率因数",
    "pi": "起点是否设定",
    "pl": "有线/wifi",
    "plugins": "网关三方插件信息",
    "power_on_level": "上电默认亮度的配置，需要同时包含亮度、色温、色彩三个值",
    "psk": "wifi密码",
    "rd": "电机方向是否反转",
    "retrans": "重传次数（未使用）",
    "rfhct": "地暖当前温度",
    "rfhp": "地暖开关",
    "rfhtt": "地暖设定目标温度",
    "rg": "角度旋转力度",
    "rl": "是否开启relay",
    "rmt": "遥控器信息",
    "rrd": "角度是否反转",
    "rs": "开关方向是否已校准",
    "rst": "房间大小：0-小于4平，1-4-6平，2-6-8平，3-大于8平",
    "run_power": "设备运行功率 单位瓦",
    "run_speed": "运行速度",
    "run_speed_rdy": "是否支持运行速度",
    "sa": "摆动角度（60-120）",
    "sbp": "上电状态",
    "sdt": "继电器后边所接的设备类型",
    "sens_range": "感应范围，传感器感应范围大小",
    "sens_shield": "识别范围",
    "showGroupDevices": "是否显示组内设备",
    "slisaon": "是否开启闪断",
    "slisaon_rdy": "是否支持闪断",
    "sonos_mgr": "sonos开启关闭命令",
    "sp": "开关",
    "srb": "开关自回弹",
    "ss": "摆动类型：1-循环摆动，0-固定角度",
    "ssid": "wifi：id",
    "support_fblck": "是否支持重置锁定",
    "support_fbnum": "支持重置锁定的数量",
    "support_rl": "是否支持relay",
    "sys_s": "系统启动次数",
    "system_failure_level": "设备异常时灯亮度，需要同时包含亮度、色温、色彩三个值",
    "t": "当前温度",
    "temp": "温度",
    "temp_hidden": "temperature_hidden，在屏幕上隐藏温度信息. false：展示, true：隐藏；",
    "tgt": "目标温度",
    "time_hidden": "time_hidden 在屏幕上隐藏时间信息；false：展示；true：隐藏",
    "tp": "目标开合度",
    "tra": "目标旋转角度",
    "trs": "调光方向上是否校准",
    "ttl": "time to live（未使用）",
    "tx_power": "发射功率",
    "ve": "换气档位：0: 关闭, 1: 低档, 2: 中档, 3: 高档",
    "vmcf": "风速",
    "vmcp": "开关",
    "vol": "音量",
    "weather_hidden": "weather_hidden 在屏幕上隐藏天气信息；false：展示；true：隐藏",
})
