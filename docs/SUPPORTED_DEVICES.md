# Supported Device Categories and Capability Scope

更新时间：2026-06-29

## 说明

本文说明 `ha_yeelight_pro` 当前按 Yeelight IoT category 和 capability evidence 投影 Home Assistant 实体的范围。它不是 SKU 白名单，也不表示每个设备都会暴露厂商 App 中的全部能力。

## 当前集成支持边界

`ha_yeelight_pro` 不把 Yeelight IoT category 直接等同于 Home Assistant platform。实体投影优先使用 product schema、component identity、runtime state 和 registry-known property 证据。

稳定品类边界：

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

上述品类支持表示当前集成有对应投影策略；实际实体数量和控制能力仍取决于设备返回的 schema、属性、事件、hydration 状态和用户的导入过滤设置。

## 能力矩阵模板

| 能力 | HA 表达 | 证据来源 | 测试方法 | 结果 |
| --- | --- | --- | --- | --- |
| 开关 | `light` / `switch` | writable power property 或明确组件身份 | 待填写 | 待填写 |
| 亮度 | `light.brightness` / `number` | schema range / known property | 待填写 | 待填写 |
| 色温 | `light.color_temp` / `number` | schema range / known property | 待填写 | 待填写 |
| 窗帘位置 | `cover` | curtain component / position property | 待填写 | 待填写 |
| 温控 | `climate` | temp-control component / target state | 待填写 | 待填写 |
| 传感器状态 | `binary_sensor` / `sensor` | readable telemetry / known binary state | 待填写 | 待填写 |
| 面板/旋钮事件 | `event` / device trigger | product schema event / registry event | 待填写 | 待填写 |
| 场景执行 | `button` / `select` | cloud scene list | 待填写 | 待填写 |
| 固件版本 | device info / diagnostic sensor | firmware metadata / known property | 待填写 | 待填写 |

## 不支持或需确认的范围

| 范围 | 当前状态 | 说明 |
| --- | --- | --- |
| 未知可写属性泛化控制 | 不支持 | 没有官方写入语义时，不生成 switch/select/number/text/button |
| 未知 no-parameter action button | 不支持 | 缺少官方 action 执行 API、payload 和错误语义 |
| House transfer | 不支持 | 该操作具有所有权和拓扑破坏性，不暴露 helper、service 或实体 |
| 设备导入过滤清理既有实体 | 不支持 | 过滤只 gate 新设备来源实体，不修改既有 registry |
| 自动删除 registry 条目 | 不支持 | stale cleanup 只通过显式 dry-run + audit-id confirm 禁用 stale entities |
| mDNS/SSDP/DHCP 自动发现 | 未声明 | 当前 manifest 未声明这些 discovery matcher |

## 发布口径

可以说：

- 当前集成按 Yeelight IoT category 和 capability evidence 支持多类设备投影。
- 实体覆盖取决于设备 schema、运行时属性、事件证据和用户导入过滤设置。
- 未知能力默认采用保守策略，避免暴露不可验证的控制项。

不要说：

- 所有 Yeelight Pro 设备都完整支持。
- 某个 SKU 的所有厂商 App 功能都已在 Home Assistant 暴露。
- 未知 writable 属性会自动生成可控实体。
