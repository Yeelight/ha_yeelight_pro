# ha_yeelight_pro Works with Home Assistant 申请步骤与整改建议

更新时间：2026-06-22  
适用对象：PM、认证申请负责人、研发负责人、QA

## 1. 目标

本文用于指导 Yeelight 以 `ha_yeelight_pro` 为技术基础，推进 Works with Home Assistant（WWHA）认证申请。本文不代替官方协议、法务审查或 Home Assistant Partnerships 的最新答复。

建议将 WWHA 工作拆成两条并行线：

- 申请线：PM 与 Open Home Foundation / Home Assistant Partnerships 确认范围、协议、费用、测试安排和品牌使用边界。
- 工程线：研发补齐本地优先、Gold 质量等级、固件更新/提醒、发现能力、文档和测试证据。

## 2. 阶段路线

### HACS 与 Home Assistant Core 关系

当前已经提交 HACS 不会阻止后续提交 Home Assistant Core。两者可以并行推进：

- HACS 作为社区安装、试用和反馈渠道。
- Home Assistant Core 作为官方内置集成、Gold 质量等级和 WWHA 长期路径。

需要注意：如果未来 Core 接收同一个 `domain=yeelight_pro`，用户本地仍保留
`custom_components/yeelight_pro` 时，Home Assistant 会优先加载 custom
integration 并覆盖 Core 内置集成。因此 Core 接收后必须准备 HACS 迁移公告，
提示普通用户删除 custom integration 并重启 Home Assistant。

详细策略见 [CORE_MIGRATION_STRATEGY.md](CORE_MIGRATION_STRATEGY.md)。

### 阶段 0：内部决策

产出：

- 首批申请设备或 Hub 清单。
- 每个设备的销售区域、量产状态、销售链接和合规证书。
- 每个设备的关键功能清单。
- 每个设备的 Home Assistant 支持方式。
- Yeelight 内部负责人矩阵：PM、研发、QA、法务、品牌、客户支持。

验收标准：

- 不再以“认证 ha_yeelight_pro 集成”作为唯一目标，而是明确“通过 ha_yeelight_pro 支撑哪些设备/Hub 通过 WWHA”。

### 阶段 1：官方预沟通

动作：

1. 邮件联系 `partner@openhomefoundation.org`。
2. 附上 Yeelight 公司介绍、申请设备清单、仓库链接、release 链接和 HACS PR 链接。
3. 明确说明当前集成状态：HACS release package available，HACS default PR under review。
4. 询问 HACS 自定义集成是否可作为 WWHA 测试载体。
5. 询问是否必须进入 Home Assistant Core 并满足 Gold 质量等级。
6. 询问 Hub + 子设备的认证边界。

建议邮件要点：

```text
Yeelight would like to apply for Works with Home Assistant certification for selected Yeelight Pro devices/hubs.
The current Home Assistant integration is published at https://github.com/Yeelight/ha_yeelight_pro, with v1.0.4 release and HACS default repository PR #8516 under review.
We would like to confirm whether a HACS-distributed integration is acceptable for the certification test stage, or whether the integration must first be contributed to Home Assistant Core and reach Gold quality scale.
```

验收标准：

- 官方明确下一步流程、是否接受 HACS、是否要求 Core、样机要求、费用和协议。

### 阶段 2：工程差距关闭

建议将工程差距按 P0/P1/P2 推进。

P0：

- 证明首批认证设备在本地网络下可完成关键功能，不依赖云端。
- 明确云能力是否 opt-in；必要时调整默认配置和文档。
- 补齐固件更新或固件更新提醒路径。
- 梳理 Gold Quality Scale 清单，并维护
  [QUALITY_SCALE_GOLD_GAP_ANALYSIS.md](QUALITY_SCALE_GOLD_GAP_ANALYSIS.md) 或官方要求的等效对照文档。
- 准备官方测试账号、测试设备、固件版本和脱敏诊断样例。

P1：

- 补齐自动发现能力或说明不可发现原因。
- 补齐 reconfigure flow。
- 补齐 supported/unsupported devices、known limitations、troubleshooting、data update、use cases、automation examples 文档：
  [SUPPORTED_DEVICES.md](SUPPORTED_DEVICES.md)、
  [LOCAL_CONTROL.md](LOCAL_CONTROL.md)、
  [TROUBLESHOOTING.md](TROUBLESHOOTING.md)、
  [AUTOMATION_EXAMPLES.md](AUTOMATION_EXAMPLES.md)。
- 核对所有实体分类、device class、默认禁用策略和翻译。
- 提供覆盖率结果和最新门禁输出。

P2：

- 优化 HACS README 的终端用户表达。
- 准备官方 Home Assistant Core 上游路径评估。
- 准备品牌资产提交 Home Assistant brands 仓库的材料。

验收标准：

- 工程侧能提供一套无需真实密钥泄露的认证证据包。
- 首批设备能在本地模式完成官方测试所需的关键功能。

### 阶段 3：协议、付款和样机测试

动作：

1. 法务审查 WWHA agreement。
2. 支付 500 CHF 年费。
3. 准备测试样机和供电/网络/账号材料。
4. 提供 Home Assistant 安装步骤和本地控制步骤。
5. 提供问题响应通道。

验收标准：

- 官方测试团队能独立安装集成并控制设备。
- 测试过程没有真实 token、house id、device id、MAC 或私有 endpoint 泄露到公开渠道。

### 阶段 4：反馈整改

动作：

- 将官方反馈拆成认证阻断项和体验优化项。
- 认证阻断项先修复并发布 patch release。
- 更新 release、HACS PR、文档和测试报告。
- 重新提交测试说明。

验收标准：

- 所有阻断项有明确修复版本。
- 回归测试和本地 HA verifier 通过。

### 阶段 5：审批和品牌使用

动作：

- 等官方确认通过后，再使用 WWHA badge。
- badge 使用范围必须遵循官方品牌授权。
- 对官网、包装、电商详情页、App 内介绍和 README 做统一审核。

验收标准：

- 对外宣传只覆盖已认证设备，不扩展到未认证 SKU 或整个生态。

## 3. 研发整改建议

### 3.1 明确本地优先路径

当前状态：

- README 表示集成支持 cloud、private deployment、LAN gateway。
- `manifest.json` 当前 `iot_class` 为 `cloud_polling`。
- WWHA 要求本地可用，云端只能作为额外 opt-in。

建议：

- 为认证设备定义“本地模式首选路径”，并在 README/认证文档中单独说明。
- 如果首批设备通过 LAN gateway 认证，建议文档将 LAN setup 放到认证设备章节的主路径，而不是云端主路径之后的补充能力。
- 评估是否需要按连接模式拆分 iot_class 表达；若最终进入 Home Assistant Core，需与官方确认多模式 hub 集成如何标注。
- 核对 `DEFAULT_LIVE_UPDATES` 和文档中的 opt-in 表述是否一致；如云推送默认开启，需要评估是否违反“cloud control opt-in only”的认证口径。

### 3.2 补齐 Gold Quality Scale 对照

当前状态：

- 仓库内未发现 `quality_scale.yaml`。
- 当前为 HACS 自定义集成，不是 Home Assistant Core 官方集成。

建议：

- 新建 Gold 对照表，逐项映射 Bronze/Silver/Gold rules。
- 对已满足项提供代码/测试/文档证据。
- 对暂不适用项写明 exemption 理由。
- 重点补齐或确认以下项：
  - `runtime-data`：当前主要使用 `hass.data[DOMAIN][entry_id]`，若走 Core/Gold，建议迁移到 `ConfigEntry.runtime_data`。
  - `parallel-updates`：当前未看到 `PARALLEL_UPDATES` 明确声明，建议各平台补齐。
  - `reconfiguration-flow`：当前有 options flow，但未看到 `async_step_reconfigure`，建议补齐。
  - `discovery` 和 `discovery-update-info`：LAN 场景应补齐发现机制或 exemption。
  - `entity-disabled-by-default`：对低频、调试、诊断或高噪实体明确默认禁用策略。
  - `exception-translations` 和 `icon-translations`：核对是否完整。

### 3.3 固件更新或提醒闭环

当前状态：

- 未看到 `update` 平台或固件更新提醒的明确闭环。

建议：

- 优先评估 Yeelight Pro API/局域网协议是否能提供设备固件版本、可用版本、更新状态和触发 OTA。
- 如果能触发 OTA，建议实现 Home Assistant `update` 平台。
- 如果不能触发 OTA，至少实现固件版本诊断实体和 Repairs/notification 提醒，说明用户应通过 Yeelight APP 或设备端完成固件更新。
- 文档中明确哪些设备支持 HA 内 OTA，哪些仅支持提醒。

### 3.4 自动发现和安装体验

当前状态：

- LAN 模式有网关配置和探针脚本，运行时可做 UDP 发现尝试。
- `manifest.json` 未声明 `zeroconf`、`dhcp`、`ssdp`、`bluetooth` 等 discovery matcher。

建议：

- 如果 Yeelight Pro 网关/面板在局域网可通过 Zeroconf、SSDP、DHCP hostname/OUI、UDP 广播稳定识别，优先补齐 HA 原生 discovery。
- 如果只能通过私有 UDP 协议发现，评估是否可在 config flow 中提供 discover step，并在 Gold 对照中说明限制。
- 支持 discovery 信息更新网络地址，避免设备 IP 变化后用户手动重配。

### 3.5 文档补强

当前 README 已覆盖安装、配置、功能、服务和运行时模型，但 Gold/WWHA 建议补齐以下面向用户的材料：

- 支持设备/Hub 清单，按 SKU、区域、固件版本列出。
- 不支持设备/功能清单。
- 本地模式安装步骤。
- 云端能力说明，并明确 cloud 为额外能力。
- 数据更新方式：轮询、WebSocket、本地推送、刷新间隔。
- 示例自动化：灯光、窗帘、场景面板、传感器、断线恢复。
- 已知限制：云端账号、局域网发现、固件更新、私有部署、设备过滤等。
- 故障排查：认证失败、设备不出现、实体不可用、局域网网关连接失败、诊断导出。
- 隐私说明：diagnostics 和 issue 模板如何脱敏。
- 卸载和 registry cleanup 说明。

### 3.6 测试和证据包

建议申请前固定一版“认证候选门禁”：

```bash
cd extensions/ha_yeelight_pro
python3 -m compileall -q custom_components/yeelight_pro scripts hacs_publish.py
ruff check custom_components/yeelight_pro scripts hacs_publish.py
mypy --ignore-missing-imports --explicit-package-bases --exclude custom_components/yeelight_pro/tests custom_components/yeelight_pro scripts hacs_publish.py
pytest -q
python3 validate_hacs.py
python3 scripts/check_release_zip.py
python3 scripts/sync_local_ha_runtime.py
python3 scripts/verify_local_ha.py
python3 scripts/verify_local_ha_soak.py
python3 scripts/verify_local_ha_recovery.py
```

生产探针仅在授权环境运行，并保留 fail-closed：

```bash
python3 scripts/verify_push_websocket.py
python3 scripts/verify_scan_login.py
python3 scripts/verify_cloud_devices.py
python3 scripts/verify_lan_gateway.py
```

对外证据只输出聚合和脱敏结果，不输出 token、URL、house id、device id/name、room、MAC、host、port 或原始 payload。

## 4. PM 注意事项

### 4.1 对外口径

可以说：

- Yeelight has published a Home Assistant integration candidate for Yeelight Pro.
- The integration is available as a GitHub release and is under HACS default repository review.
- Yeelight is preparing selected devices/hubs for Works with Home Assistant certification.

不要说：

- Yeelight Pro 已完成 Works with Home Assistant 官方审批。
- HACS 审核结果等同于 WWHA 官方审批结果。
- 所有 Yeelight 设备均 Works with Home Assistant。
- 云端控制设备默认满足 WWHA。

### 4.2 申请范围

建议按设备批次申请，不要一次性申请整个 Yeelight Pro 生态。首批范围应满足：

- 本地控制链路稳定。
- 关键功能在 HA 中完整可控。
- 设备公开销售。
- 证书齐全。
- 固件版本可控。
- QA 可以长期复测。

### 4.3 合规材料

每个申请设备建议准备：

- SKU/型号/硬件版本。
- 固件版本。
- 销售区域和销售链接。
- FCC/CE 或等效证书。
- Zigbee/Matter/Z-Wave 联盟证书，如适用。
- 用户手册和安装指南。
- 隐私政策和数据处理说明。
- 固件更新说明。
- Home Assistant 支持矩阵。

## 5. 推荐任务拆分

| 优先级 | 任务 | 负责人建议 | 完成标准 |
| --- | --- | --- | --- |
| P0 | 明确认证 SKU/Hub 清单 | PM/产品 | 输出首批设备清单和关键功能矩阵 |
| P0 | 向官方确认 HACS/Core/Gold 边界 | PM | 获得官方书面回复 |
| P0 | 本地控制演示闭环 | 研发/QA | 无云或云 opt-in 场景下关键功能可用 |
| P0 | 固件更新/提醒方案 | 研发/产品 | 确定 `update` 平台或提醒路径 |
| P0 | Gold Quality Scale 对照 | 研发 | 输出逐项证据和缺口 |
| P1 | 自动发现/网络信息更新 | 研发 | config flow 可发现或有明确 exemption |
| P1 | 终端用户文档补强 | PM/研发 | README/官方申请材料覆盖 Gold 文档项 |
| P1 | 认证证据包 | QA/研发 | 最新门禁、日志、diagnostics 均脱敏 |
| P2 | Home Assistant Core 上游评估 | 研发/PM | 判断是否必须上游及预计工作量 |

## 6. 当前最可能需要的代码改动

下面不是立即必须执行的改动，而是基于官方要求和当前代码状态的风险清单。

1. 增加或整理 `quality_scale.yaml`，并逐项补齐 Gold 证据。
2. 将 runtime data 从 `hass.data` 迁移或兼容到 `ConfigEntry.runtime_data`。
3. 为各平台补齐 `PARALLEL_UPDATES`。
4. 增加 `async_step_reconfigure` 或官方认可的 reconfigure flow。
5. 增加 LAN discovery matcher 或更明确的 config flow discovery step。
6. 增加固件版本/更新能力；无法 OTA 时增加固件提醒闭环。
7. 调整云能力默认值，确保云控制和云推送是清晰 opt-in。
8. 将认证设备的本地模式文档提升为首要路径。
9. 补齐支持设备、已知限制、故障排查、自动化示例、数据更新方式文档。
10. 若官方要求进入 Home Assistant Core，准备 brands、官方 docs、manifest、tests、coverage、依赖透明度、strict typing 等上游材料。

## 7. 申请前最终检查清单

- 首批认证设备清单已冻结。
- 每个设备的 key functionality 已在 HA 中可演示。
- 不配置云账号时，本地关键功能仍可用。
- 云端能力不是认证关键路径，且对用户是可选择能力。
- 固件更新或提醒闭环已可演示。
- FCC/CE 或等效证书齐全。
- HACS PR 状态和 release 状态已更新到最新。
- 官方已确认 HACS/Core/Gold 路径。
- 认证候选版本 release、tag、manifest version、CHANGELOG 一致。
- 所有提交材料均不包含 token、house id、device id、MAC、私有 endpoint 或原始 payload。
- 对外宣传未提前使用 WWHA badge。

## 8. 参考资料

- Works with Home Assistant 官方页面：<https://works-with.home-assistant.io/>
- Integration Quality Scale：<https://developers.home-assistant.io/docs/core/integration-quality-scale/>
- Integration Quality Scale Rules：<https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/>
- Integration manifest：<https://developers.home-assistant.io/docs/creating_integration_manifest>
- HACS 发布说明：<https://www.hacs.xyz/docs/publish/start/>
- `ha_yeelight_pro` 仓库：<https://github.com/Yeelight/ha_yeelight_pro>
- `v1.0.4` release：<https://github.com/Yeelight/ha_yeelight_pro/releases/tag/v1.0.4>
- HACS default PR #8516：<https://github.com/hacs/default/pull/8516>
