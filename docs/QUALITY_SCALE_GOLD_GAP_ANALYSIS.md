# Gold Quality Scale Gap Analysis

更新时间：2026-06-22

## 范围

本文是 `ha_yeelight_pro` 面向 Home Assistant Core 上游和 Works with Home Assistant 准备的研发差距表。它不是官方质量等级声明，也不表示当前集成已完成 Gold 目标。

状态定义：

- `done`：当前代码、测试或文档已有可审查证据。
- `partial`：已有基础能力，但仍存在 WWHA/Core 风险或缺少官方形式。
- `todo`：当前缺口明确，需要研发补齐。
- `exempt`：对该集成不适用，但需要在 Core/WWHA 沟通中确认。

## 当前总览

| 领域 | 状态 | 证据或缺口 |
| --- | --- | --- |
| 配置流 | done | `manifest.json` `config_flow=true`，配置流覆盖 cloud/private/LAN |
| diagnostics | done | `diagnostics.py`、诊断红线测试、local HA verifier |
| Repairs | partial | 已有拓扑变化 Repairs；固件提醒 Repairs 尚未闭环 |
| 本地可用 | partial | 有 LAN gateway runtime 和 UDP discovery helper；认证设备本地关键功能矩阵未冻结 |
| discovery | partial | 有 `lan_discovery.py` 和 LAN config flow；manifest 未声明 `zeroconf`/`dhcp`/`ssdp`/`bluetooth` matcher |
| discovery 更新网络信息 | todo | 需要验证发现信息是否可更新 host/port/product id |
| reconfigure flow | todo | 未发现 `async_step_reconfigure` |
| runtime data | todo | 当前主要使用 `hass.data[DOMAIN][entry_id]` |
| parallel updates | todo | 平台未统一声明 `PARALLEL_UPDATES` |
| 固件更新或提醒 | todo | 有 `fv` 固件版本解析，无 `update` 平台或提醒闭环 |
| 文档 | partial | README 完整度较高；Gold 需要独立 supported devices、limitations、troubleshooting、data update、automation examples |
| 测试覆盖 | partial | 仓库测试和 preflight 很强；Core/Gold 仍需按官方规则逐条对齐 |

## Bronze / Silver / Gold 规则对照

| 规则或能力 | 状态 | 当前证据 | 缺口和下一步 |
| --- | --- | --- | --- |
| Config flow | done | `custom_components/yeelight_pro/config_flow.py` | 继续保持 UI 配置路径，不新增 YAML-only 能力 |
| Unique ID | partial | 配置流和 identity helper 已存在 | Core 上游前复核所有 entry、device、entity unique id 的稳定性 |
| Device registry | done | `ha_device_registry.py`、网关/子设备拓扑测试 | 对首批认证 SKU 输出 device info 证据 |
| Entity registry cleanup | partial | `cleanup_registry` dry-run + audit-id confirm | Gold stale devices 口径需确认是否还要补 Repairs 或自动检测说明 |
| Diagnostics | done | `diagnostics.py`、redaction tests、local HA diagnostics verifier | 申请证据包只输出脱敏样例 |
| Repairs | partial | `repair_issues.py`，拓扑变化 aggregate diff | 补固件提醒或升级引导 Repairs 策略 |
| Reauthentication | done | `config_flow_reauth.py`、reauth tests | 保持 token 过期走 HA reauth |
| Options flow | done | `options_flow.py`、`config_flow_options.py` | 明确哪些字段属于 options，哪些属于 reconfigure |
| Reconfigure flow | todo | 未发现 `async_step_reconfigure` | 第二阶段实现，覆盖 host/auth/endpoint 等连接字段 |
| Runtime data | todo | 平台直接读 `hass.data[DOMAIN][entry_id]` | 第二阶段引入 runtime data helper，设置 `entry.runtime_data` 并镜像 `hass.data` |
| Parallel updates | todo | 未统一声明 | 第二阶段为 11 个平台补齐 `PARALLEL_UPDATES` 并加 preflight |
| Discovery | partial | `lan_discovery.py`、`config_flow_lan.py` | 不伪造 mDNS/DHCP；若只有 UDP，则在 config flow 中明确 discovery step |
| Discovery updates | todo | 尚未形成 host/port 更新闭环证据 | LAN discovery 返回稳定信息后补 config entry update 测试 |
| Data update documentation | partial | README runtime model 说明 polling/WebSocket/LAN | 需要独立 `LOCAL_CONTROL.md` 和用户文档链接 |
| Supported devices | todo | 当前只列 IoT category，不列 SKU | `SUPPORTED_DEVICES.md` 先作为 PM 填写模板 |
| Unsupported devices/features | todo | 当前缺少集中清单 | 在 `SUPPORTED_DEVICES.md` 维护 limitations |
| Troubleshooting | todo | README 有安装和验证命令，缺用户排障表 | 新增 `TROUBLESHOOTING.md` |
| Automation examples | todo | 当前缺独立自动化示例 | 新增 `AUTOMATION_EXAMPLES.md` |
| Entity categories | partial | 有 diagnostics/sensor/entity category 相关代码 | Core 上游前逐平台复核低频、诊断、高噪实体默认分类 |
| Entity disabled by default | partial | 有未知能力隐藏和 diagnostics 设计 | 对 analytics、低频诊断和高噪实体输出逐项证据 |
| Device class | partial | projector tests 覆盖多平台 | Core 上游前按实体平台逐项审查 |
| Translations | done | `strings.json`、`translations/en.json`、`translations/zh-Hans.json` | 新增 options/services 时保持三份同步 |
| Exception translations | partial | 有用户可见错误 redaction guard | Core 上游前补齐 HA issue translation 风格 |
| Icon translations | partial | 有实体和 selector 翻译 | Core 上游前按官方规则复核 |
| Firmware update | todo | `core/firmware_metadata.py` 解析 `fv` | 若 API 支持 OTA，做 `update` platform；否则做诊断 + Repairs/notification 提醒 |
| Local-only key functionality | partial | LAN runtime 存在，默认 `iot_class=cloud_polling` | WWHA 首批设备必须输出断云场景关键功能证据 |
| Cloud opt-in | partial | `live_updates` 是显式选项，但 `DEFAULT_LIVE_UPDATES=True` | P0 复核默认值和文档；认证口径应避免云能力成为默认关键路径 |

## P0 风险

1. `DEFAULT_LIVE_UPDATES=True` 与 WWHA “cloud opt-in” 口径存在解释风险。
2. `manifest.json` 当前 `iot_class=cloud_polling`，与本地优先认证路径存在张力。
3. 未发现 `async_step_reconfigure`。
4. 未使用 `ConfigEntry.runtime_data` 作为主 runtime data 路径。
5. 未统一声明 `PARALLEL_UPDATES`。
6. 无固件更新或提醒闭环。
7. 未冻结首批 WWHA 设备/SKU 清单。

## 推荐执行顺序

1. 先用本文作为 Gold gap source of truth，不在 README 宣称 Gold。
2. 补齐 Core/HACS 迁移策略、本地控制、支持设备、排障、自动化示例。
3. 增强 preflight，阻断提前宣称 WWHA、Gold、HACS/Core 已完成的过度声明。
4. 第二阶段再做 runtime data、parallel updates、reconfigure flow。
5. 第三阶段做 LAN discovery 信息更新、固件提醒/更新和 WWHA 证据包。
