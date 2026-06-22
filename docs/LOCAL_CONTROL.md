# Local Control and Data Update Model

更新时间：2026-06-22

## 目标

本文说明 `ha_yeelight_pro` 的本地控制边界、数据更新方式和 WWHA 认证关注点。本文不作为任何设备完成官方认证的声明。

## 当前连接模式

| 模式 | 当前用途 | 本地性判断 | 认证备注 |
| --- | --- | --- | --- |
| Cloud | Yeelight 云端账号、扫码登录、家庭设备同步 | 依赖云端 | 不能作为 WWHA 本地关键功能的唯一链路 |
| Private deployment | 私有服务端和可选私有推送 URL | 取决于部署位置 | 需要项目侧说明部署和网络边界 |
| LAN gateway | 局域网网关 TCP runtime 和 UDP discovery helper | 本地网络 | 建议作为首批认证候选设备的主路径 |

## 数据更新方式

- 轮询是默认全量状态刷新路径，默认间隔来自 `scan_interval`。
- Cloud/private entry 可通过 `live_updates` 启用 WebSocket 事件通知。
- LAN entry 可通过 `local_gateway_control` 启用本地网关 runtime。
- LAN entry 在启用本地网关控制且未配置 host 时，会按局域网协议进行一次 UDP discovery fallback，再尝试建立 TCP 会话。

## WWHA 口径

WWHA 关注的是设备或 Hub 的本地可用性，不是单纯证明集成能通过云端控制设备。

申请材料中应证明：

- 首批认证设备的关键功能在本地网络下可用。
- 云端账号、云端控制和云端推送不是认证关键功能的唯一路径。
- 用户能理解何时使用 LAN、何时使用云端。
- 断开外网或不配置云账号时，认证设备的本地关键功能仍可演示。

## 当前研发风险

- `manifest.json` 当前为 `iot_class=cloud_polling`。
- `DEFAULT_LIVE_UPDATES=True` 需要重新评估，避免云事件通知默认开启被解释为非 opt-in。
- LAN discovery 已有 helper/runtime，但没有 `zeroconf`、`dhcp`、`ssdp` 或 `bluetooth` manifest matcher。
- 如果设备不能稳定提供 HA 原生 discovery 信号，不应在 manifest 中伪造 matcher。

## 首批认证设备本地验证模板

PM/QA 应按每个 SKU 填写：

| 字段 | 内容 |
| --- | --- |
| SKU/型号 | 待填写 |
| 固件版本 | 待填写 |
| 本地连接方式 | LAN gateway / 其他 |
| 是否需要云账号完成关键功能 | 待填写 |
| 关键功能 | 开关、亮度、色温、窗帘、温控、传感器、事件等 |
| HA 实体和服务 | 待填写 |
| 断网验证结果 | 待填写 |
| 固件更新或提醒方式 | 待填写 |
| 已知限制 | 待填写 |

## 研发下一步

- 将认证候选设备的 LAN setup 写成主路径，而不是云端 setup 的补充说明。
- 补充 config flow discovery step 或明确 exemption。
- 验证 discovery 信息是否可用于更新 host/port/product id。
- 复核 `live_updates` 默认值和文档表达。
- 将本地控制演示输出为脱敏证据包，禁止包含 token、house id、device id、MAC、host、port、私有 endpoint 或原始 payload。
