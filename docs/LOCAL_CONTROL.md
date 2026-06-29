# Local Control and Data Update Model

更新时间：2026-06-29

## 目标

本文说明 `ha_yeelight_pro` 当前的连接模式、本地网关边界和数据更新方式。本文只描述该 Home Assistant 自定义集成的实际能力，不承诺任何外部认证、品牌计划或独立技术底座。

## 当前连接模式

| 模式 | 当前用途 | 更新方式 | 说明 |
| --- | --- | --- | --- |
| Cloud | 易来账号、扫码登录、家庭和设备同步 | 轮询 + 可配置 WebSocket runtime | 适合普通云端账号体验 |
| Private deployment | 私有服务端、指定家庭和可选私有推送 URL | 轮询 + 可配置 WebSocket runtime | 实际网络边界取决于部署环境 |
| LAN gateway | 局域网网关 TCP runtime 和一次 UDP discovery fallback | 本地 TCP 会话 | 需要可访问的网关地址、端口和协议参数 |

## 数据更新方式

- 轮询是默认全量状态刷新路径，默认间隔来自 `scan_interval`。
- Cloud/private entry 可通过 `live_updates` 使用 WebSocket 事件通知。
- LAN entry 可通过 `local_gateway_control` 启用本地网关 runtime。
- LAN entry 在启用本地网关控制且未配置 host 时，会按局域网协议进行一次 UDP discovery fallback，再尝试建立 TCP 会话。
- Push/LAN 属性更新进入 runtime bridge 后，会按产品 schema 重新构建 canonical runtime state，避免绕过 schema-aware 状态转换。

## 本地网关边界

- 当前 LAN runtime 位于显式的 LAN 连接模式和 `local_gateway_control` 选项边界内。
- 当前未在 manifest 中声明 `zeroconf`、`dhcp`、`ssdp` 或 `bluetooth` 自动发现 matcher。
- 不伪造自动发现能力；如果设备不能稳定提供 Home Assistant 可用的发现信号，应通过手动配置或项目侧说明处理。
- 网关地址、token、设备 ID、MAC、私有 endpoint 和原始 payload 不应出现在日志、诊断或测试报告中。

## 验证模板

QA 可按每个设备或网关填写：

| 字段 | 内容 |
| --- | --- |
| 设备/网关型号 | 待填写 |
| 固件版本 | 待填写 |
| 连接模式 | Cloud / Private deployment / LAN gateway |
| 网关 host/port 是否手动配置 | 待填写 |
| 关键 HA 实体 | light / switch / cover / climate / sensor / event 等 |
| 控制验证 | 待填写 |
| 状态刷新验证 | 待填写 |
| WebSocket 或 LAN 更新验证 | 待填写 |
| 已知限制 | 待填写 |

## 研发下一步

- 继续用真实样板家庭审计覆盖控制、诊断、传感器、事件和状态投影。
- 继续保持 LAN discovery helper 与 runtime 的显式边界，不把未验证的发现能力写进 manifest。
- 对每个新增本地网关行为补充脱敏测试样本和 fail-closed 生产探针。
