# Yeelight Pro

[English](README.md) | [中文](README_zh.md)

Yeelight Pro 集成，支持将 Yeelight Pro 设备接入 Home Assistant。支持云端和私有部署两种模式。

## 功能特性

- 支持云端和私有部署两种模式
- 自动设备发现和状态同步（30 秒轮询）
- 支持 13 种实体平台
- 完整的设备控制能力

## 安装

### HACS 安装（推荐）

1. 打开 HACS
2. 搜索 "Yeelight Pro"
3. 点击安装
4. 重启 Home Assistant

### 手动安装

1. 下载最新版本
2. 解压到 `custom_components/yeelight_pro/`
3. 重启 Home Assistant

## 配置

### 云端模式

1. 进入 设置 → 设备与服务 → 添加集成
2. 搜索 "Yeelight Pro"
3. 选择 "Yeelight Pro 云端"
4. 输入 Access Token
5. 选择家庭
6. 完成配置

### 私有部署模式

1. 进入 设置 → 设备与服务 → 添加集成
2. 搜索 "Yeelight Pro"
3. 选择 "私有部署（Lucore）"
4. 输入服务器地址（如 `192.168.1.100:8080`）
5. 输入 Access Token
6. 输入家庭 ID
7. 完成配置

## 支持的设备类型

| 设备类型 | 实体平台 | 功能 |
| --- | --- | --- |
| 灯泡 | light | 亮度、色温、RGB 控制 |
| 开关 | switch | 开关控制 |
| 插座 | switch | 开关控制 |
| 风扇 | fan | 风速、摆头控制 |
| 窗帘 | cover | 位置控制 |
| 空调 | climate | 温度、模式控制 |
| 门锁 | lock | 锁定/解锁 |
| 传感器 | sensor | 温度、湿度、光照 |
| 人体传感器 | binary_sensor | 移动检测 |
| 门窗传感器 | binary_sensor | 门窗状态 |
| 遥控器 | event | 按钮事件 |
| 按钮 | button | 按钮操作 |
| 数字 | number | 数值设置 |
| 选择 | select | 选项选择 |

## 服务

### yeelight_pro.assign_areas

批量为设备分配区域。

**参数**：

- `devices`：设备 ID 列表
- `area_id`：区域 ID

### yeelight_pro.auto_assign_areas

根据设备名称中的房间关键词自动分配区域。

**参数**：

- `gateway_id`（可选）：限定指定网关下的设备

### yeelight_pro.debug_emit_event

向 Home Assistant 事件总线发射调试 Yeelight Pro 设备事件（仅用于开发调试）。

**参数**：

- `source_device_id`：源设备标识
- `component_id`：组件标识
- `event_type`：自定义事件类型名称
- `event_attributes`（可选）：附加事件属性

## 高级配置

### 自定义扫描间隔

默认扫描间隔为 30 秒。可以在配置选项中修改。

### 调试日志

在 `configuration.yaml` 中添加：

```yaml
logger:
  default: info
  logs:
    custom_components.yeelight_pro: debug
```

## 故障排除

### 无法连接

1. 检查网络连接
2. 验证服务器地址和端口
3. 检查 Access Token 是否有效

### 设备不显示

1. 检查设备是否在线
2. 检查设备是否在选定的家庭中
3. 查看日志获取详细错误信息

### 控制失败

1. 检查设备是否在线
2. 检查是否有权限控制该设备
3. 查看日志获取详细错误信息

## 支持

- [GitHub Issues](https://github.com/Yeelight/ha_yeelight_pro/issues)
- [文档](https://github.com/Yeelight/ha_yeelight_pro)

## 许可证

MIT License
