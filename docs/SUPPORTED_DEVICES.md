# Supported Devices and Certification Scope

更新时间：2026-06-22

## 说明

本文是支持设备和 WWHA 申请范围模板。当前仓库尚未冻结首批认证 SKU，因此本文不得被解读为全部 Yeelight Pro 设备已完成官方认证。

## 当前集成支持边界

`ha_yeelight_pro` 当前按 Yeelight IoT category 和 capability evidence 投影 Home Assistant 实体。稳定品类边界见 `README.md` 和 `docs/IOT_SPEC_REGISTRY.md`：

- `light`
- `contact_sensor`
- `human_sensor`
- `light_sensor`
- `curtain`
- `temp_control`
- `relay_switch`
- `scene_panel`
- `gateway`
- `knob_switch`
- `other` 的保守只读传感器 fallback

上述品类支持不等于所有 SKU 均已通过 WWHA，也不等于每个 SKU 的所有功能都在 Home Assistant 中可控。

## WWHA 候选设备清单

PM 应在申请前冻结首批设备，并为每个设备补齐以下字段。

| SKU/型号 | 区域 | 固件版本 | 连接方式 | HA 关键功能 | 本地可用证据 | 固件更新/提醒 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 待填写 | 待填写 | 待填写 | 待填写 | 待填写 | 待填写 | 待填写 | candidate |

## 不支持或需确认的范围

| 范围 | 当前状态 | 说明 |
| --- | --- | --- |
| 全 Yeelight 生态一次性认证 | 不建议 | WWHA 更适合按设备或 Hub 分批申请 |
| 仅云端可控设备 | 认证风险高 | WWHA 要求本地可用，云端只能作为额外能力 |
| 无固件更新提醒的设备 | 认证风险高 | 需要 HA 内 OTA 或提醒路径 |
| 未公开销售设备 | 需确认 | 官方通常要求设备公众可购买 |
| 未提供 FCC/CE 或等效证书设备 | 需补齐 | 证书由产品/法务提供 |
| Zigbee/Matter/Z-Wave 设备 | 需额外证书 | 需满足对应联盟认证 |

## 设备能力矩阵模板

| 能力 | HA 表达 | 是否关键功能 | 测试方法 | 结果 |
| --- | --- | --- | --- | --- |
| 开关 | `light` / `switch` | 待填写 | 待填写 | 待填写 |
| 亮度 | `light.brightness` / `number` | 待填写 | 待填写 | 待填写 |
| 色温 | `light.color_temp` / `number` | 待填写 | 待填写 | 待填写 |
| 窗帘位置 | `cover` | 待填写 | 待填写 | 待填写 |
| 温控 | `climate` | 待填写 | 待填写 | 待填写 |
| 传感器状态 | `binary_sensor` / `sensor` | 待填写 | 待填写 | 待填写 |
| 面板/旋钮事件 | `event` / device trigger | 待填写 | 待填写 | 待填写 |
| 场景执行 | `button` / `select` | 待填写 | 待填写 | 待填写 |
| 固件版本 | device info / diagnostics | 待填写 | 待填写 | 待填写 |

## 发布口径

可以说：

- 当前集成按 Yeelight IoT category 支持多类设备投影。
- Yeelight 正在选择首批设备或 Hub 准备 WWHA 申请。

不要说：

- 全部 Yeelight Pro 设备均 Works with Home Assistant。
- 该清单中的候选设备已经可以使用 WWHA 标识。
- 某个 SKU 支持的所有厂商 App 功能都已在 Home Assistant 暴露。
