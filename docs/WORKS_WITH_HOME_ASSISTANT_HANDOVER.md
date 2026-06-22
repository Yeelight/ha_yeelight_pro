# ha_yeelight_pro Works with Home Assistant 交底文档

更新时间：2026-06-22  
适用对象：PM、认证申请负责人、法务/品牌负责人、研发负责人  
项目仓库：<https://github.com/Yeelight/ha_yeelight_pro>

## 1. 结论摘要

`ha_yeelight_pro` 目前已经具备面向 Home Assistant 社区发布的基础形态：公开 GitHub 仓库、`v1.0.4` release、HACS zip 资产、HACS 默认仓库 PR、配置流、双语文档、issue 模板、CI/验证入口和本地 Home Assistant 验证脚本。

但 `Works with Home Assistant`（下文简称 WWHA）不是对“一个 HACS 集成”本身做简单备案，而是围绕具体终端设备或 Hub 的认证。官方要求强调本地可用、隐私、可持续、设备可公开购买、固件更新能力，以及本地网络/Bluetooth 类接入对应集成需要满足 Gold 或更高质量等级。因此，`ha_yeelight_pro` 可以作为认证的技术支撑材料，但后续申请必须以明确设备清单、连接路径、测试样机和合规证书为主线推进。

当前建议阶段判断：

- HACS 社区发布：已进入公开发布候选/审核阶段。
- WWHA 认证：处于申请准备阶段，尚不能判断为已满足认证条件。
- 技术优先级：先确认认证范围和 Home Assistant 官方对 HACS 自定义集成的接受边界；同时补齐本地优先、Gold 质量等级、固件更新/提醒、设备发现、官方文档和认证样机证据。

HACS 与 Home Assistant Core 可以并行推进，不冲突。HACS 可继续作为社区安装和反馈渠道；若官方要求 Gold/Core 路径，后续仍可将同一 `domain=yeelight_pro` 上游到 Home Assistant Core。需要提前管理的风险是：Core 接收后，仍安装 `custom_components/yeelight_pro` 的用户会覆盖 Core 内置集成，因此需要 HACS 退场或迁移公告。详细策略见 [CORE_MIGRATION_STRATEGY.md](CORE_MIGRATION_STRATEGY.md)。

## 2. 官方规则摘录

以下内容来自 2026-06-22 查阅的官方资料，申请前应由 PM 再次复核最新页面。

### 2.1 WWHA 认证对象和流程

官方 WWHA 页面说明该计划用于帮助 Home Assistant 用户识别体验最佳的设备，并且只有认证合作伙伴可以使用 Works With 标识。

官方流程分为 6 步：

1. 选择要认证的产品。
2. 签署 WWHA agreement。
3. 支付 500 瑞士法郎年费。
4. Home Assistant 专家团队测试设备。
5. 获得测试反馈并迭代。
6. 审批通过后获得 WWHA badge。

官方要求包括：

- 认证对象是终端设备或 Hub，不认证单纯 Zigbee/Z-Wave stick 或不带匹配终端设备的连接桥。
- 设备需要面向公众可购买；众筹或预售产品需到制造阶段后才会测试。
- 设备必须本地可用，不能依赖独立云连接；云控制只能作为额外且 opt-in 的能力。
- 设备应可在 Home Assistant 中访问固件更新；如果做不到，必须提供固件更新提醒方式。
- Zigbee/Matter/Z-Wave 设备需分别满足对应联盟认证。
- 本地网络或 Bluetooth 接入需要 Gold 或更高集成质量等级。
- 所有设备需要 FCC/CE 或等效认证。
- 合作伙伴需要认可 Privacy、Choice、Sustainability 价值观。

官方联系入口：`partner@openhomefoundation.org`。

### 2.2 Integration Quality Scale

Home Assistant Developer Docs 将集成质量分为 Bronze、Silver、Gold、Platinum。WWHA 设备对应的集成至少需要 Gold。

Gold 层级的核心特征包括：

- 具备 Silver 的可靠性、错误恢复、活跃维护、重认证和详细文档。
- 终端体验完整、直观，尽可能支持自动发现。
- 支持 UI reconfigure/options。
- 支持翻译。
- 面向终端用户的完整文档。
- 尽可能通过 Home Assistant 支持设备固件/软件更新。
- 自动化测试覆盖整个集成。
- 是 WWHA 设备集成要求的最低等级。

规则页面列出的 Gold 关键规则包括：创建设备、实现 diagnostics、支持 discovery、支持 discovery 信息更新、文档说明数据更新方式、示例自动化、已知限制、支持/不支持设备、支持功能、故障排查、使用场景、动态设备、EntityCategory、device class、低频/高噪实体默认禁用、实体翻译、异常翻译、图标翻译、reconfigure flow、Repairs、移除 stale devices。

### 2.3 HACS 发布要求

HACS 官方发布文档要求仓库必须是 GitHub public repository，并包含：

- 仓库 description。
- GitHub topics。
- README，说明如何使用。
- 根目录 `hacs.json`。

`ha_yeelight_pro` 当前已经具备 HACS 发布所需的核心结构，并已提交 HACS 默认仓库 PR。

## 3. ha_yeelight_pro 当前事实

### 3.1 发布和公开状态

截至 2026-06-22：

- GitHub 仓库：<https://github.com/Yeelight/ha_yeelight_pro>
- 当前 release：`v1.0.4`
- release 发布时间：2026-06-21 03:39:08 UTC
- release 资产：`yeelight_pro.zip`
- release 资产 SHA-256：`5f2897771a83b6c52815ec540562841b2b48e1df56a80239ab3d01d9d27710c3`
- HACS 默认仓库 PR：<https://github.com/hacs/default/pull/8516>
- HACS PR 状态：open，未合并
- HACS PR 链接的验证 Action：<https://github.com/Yeelight/ha_yeelight_pro/actions/runs/27892410392>
- 验证 Action 状态：success

### 3.2 manifest 和 HACS 信息

`custom_components/yeelight_pro/manifest.json` 当前关键字段：

```json
{
  "domain": "yeelight_pro",
  "name": "Yeelight Pro",
  "codeowners": ["@yeelight"],
  "config_flow": true,
  "documentation": "https://github.com/yeelight/ha_yeelight_pro",
  "integration_type": "hub",
  "iot_class": "cloud_polling",
  "issue_tracker": "https://github.com/yeelight/ha_yeelight_pro/issues",
  "requirements": [],
  "version": "1.0.4"
}
```

`hacs.json` 当前关键字段：

```json
{
  "name": "Yeelight Pro",
  "homeassistant": "2024.1.0",
  "render_readme": true,
  "zip_release": true,
  "filename": "yeelight_pro.zip",
  "country": ["CN", "SG", "US", "DE"],
  "content_in_root": false,
  "hacs": "2.0.0"
}
```

### 3.3 当前能力范围

当前 README 和代码体现的主要能力：

- 统一配置流支持云端、私有部署、局域网网关三类模式。
- 云端支持多区域和 Yeelight APP 扫码登录，手动 token 作为高级兜底。
- 支持 token 失效重认证。
- 支持 11 个 Home Assistant 平台：`binary_sensor`、`button`、`climate`、`cover`、`event`、`fan`、`light`、`number`、`select`、`sensor`、`switch`。
- 支持易来 IoT 品类投影：灯、门磁/人体/光照传感器、窗帘、温控、继电器、情景面板、网关、旋钮开关等。
- 云端情景通过 `button` 执行。
- 支持 Home Assistant device registry 拓扑，覆盖网关和子设备关系。
- 支持 diagnostics，且当前设计强调脱敏输出。
- 支持 Repairs，用于设备拓扑变化提示。
- 支持只读刷新服务和 registry cleanup dry-run + audit_id 确认机制。
- 支持英语和简体中文翻译。
- 支持本地 HA verifier、HACS preflight、生产探针入口。

### 3.4 当前验证材料

仓库已有以下验证入口和报告：

- `docs/TEST_REPORT.md`
- `docs/RELEASE_STATUS.md`
- `docs/FINAL_RELEASE_REPORT.md`
- `docs/PROJECT_SUMMARY.md`
- `python3 hacs_publish.py --check`
- `python3 validate_hacs.py`
- `python3 scripts/check_release_zip.py`
- `python3 scripts/verify_local_ha.py`
- `python3 scripts/verify_local_ha_soak.py`
- `python3 scripts/verify_local_ha_recovery.py`
- `python3 scripts/verify_push_websocket.py`
- `python3 scripts/verify_scan_login.py`
- `python3 scripts/verify_cloud_devices.py`
- `python3 scripts/verify_lan_gateway.py`

注意：`docs/TEST_REPORT.md` 明确要求测试数量和通过率以最新命令输出为准，PM 对外提交材料时不应引用历史固定数字。

## 4. 与 WWHA 的当前匹配度

| WWHA/质量要求 | 当前状态 | 判断 |
| --- | --- | --- |
| 明确认证设备或 Hub | 仓库是集成项目，未在文档内形成认证 SKU 清单 | 需 PM 补齐 |
| 公众可购买 | 需产品侧提供销售状态和区域信息 | 需 PM 补齐 |
| 本地可用，不依赖云 | 集成有 LAN gateway 模式，但 manifest 当前 `iot_class` 为 `cloud_polling`，README 仍以云端流程为主要入口之一 | 存在认证风险 |
| 云能力只能 opt-in | 需要确认云端、WebSocket、扫码登录和 live update 默认值是否符合 opt-in 表达 | 需研发复核 |
| 固件更新或提醒 | 当前未看到 `update` 平台或固件更新提醒闭环 | 高优先级缺口 |
| 本地网络/Bluetooth 集成 Gold+ | 当前为 HACS 自定义集成，未见 `quality_scale.yaml`；不是 Home Assistant Core 官方集成 | 高优先级缺口 |
| FCC/CE 或等效认证 | 仓库不包含硬件合规证书 | 需产品/法务补齐 |
| diagnostics | 已实现 diagnostics 并有脱敏规则和测试 | 基本匹配 |
| Repairs | 已有拓扑变化 Repairs 和测试边界 | 基本匹配 |
| 翻译 | 已有英文和简体中文 | 基本匹配 |
| 自动发现 | 当前有 LAN 发现/探针能力，但 manifest 未声明 `zeroconf`/`dhcp`/`ssdp` 等发现 matcher | 需评估补齐 |
| 文档完整度 | README 较完整，但 WWHA/Gold 需要面向终端用户的支持设备、限制、用例、故障排查、数据更新、自动化示例 | 需补强 |

## 5. PM 对外申请应准备的材料

### 5.1 产品和认证范围

PM 需要先确定：

- 申请认证的设备 SKU 或 Hub 型号。
- 每个 SKU 的连接方式：LAN、Bluetooth、Matter、Zigbee、Z-Wave、云端辅助。
- 每个 SKU 的关键功能清单：开关、亮度、色温、窗帘开合、温控、传感器状态、情景触发等。
- 哪些功能是 Home Assistant 中必须可用的 key functionality。
- 哪些功能属于 secondary functionality。
- 每个 SKU 的上市区域、销售链接、量产状态。
- FCC/CE 或等效认证编号和证书文件。
- 固件升级方式，以及 Home Assistant 内是否能触达或提醒。

### 5.2 技术材料包

建议准备：

- GitHub 仓库地址。
- `v1.0.4` release 链接和 `yeelight_pro.zip` 资产链接。
- HACS PR #8516 链接和最新状态。
- 成功的 GitHub Actions 链接。
- `README.md`、`README_zh.md`、`CHANGELOG.md`、`CONTRIBUTING.md`。
- `docs/TEST_REPORT.md` 和最新本地命令输出摘要。
- 脱敏的 diagnostics 样例。
- 脱敏的 Home Assistant 日志样例，证明无 token、house id、device id、MAC、私有域名和原始 payload 泄露。
- 本地控制演示说明：断开外网或不配置云账号时，认证设备的核心功能仍可在 Home Assistant 使用。
- 固件更新或固件更新提醒演示说明。

### 5.3 申请沟通问题清单

首次联系 Open Home Foundation / Home Assistant Partnerships 时，建议直接确认：

1. Yeelight 希望以哪些设备或 Hub 申请 WWHA，而不是仅申请 `ha_yeelight_pro` 集成。
2. 当前 `ha_yeelight_pro` 通过 HACS 发布，是否可作为 WWHA 测试阶段的集成载体。
3. 如果 HACS 不足以满足 Gold 质量等级要求，是否需要先将集成贡献到 Home Assistant Core。
4. 对局域网网关类设备，官方是否接受“Hub 本地接入 + 子设备本地控制”的认证路径。
5. 固件更新如果暂不能在 Home Assistant 内直接执行，提供 Repairs/diagnostic/notification 提醒是否可接受。
6. 测试样机数量、区域、账号、固件版本和远程支持方式。
7. 认证通过前，Yeelight 能否在内部材料中使用“申请中”或“兼容 Home Assistant”的表述，以及外部宣传边界。

## 6. 主要风险

### 6.1 不应把 HACS 通过等同于 WWHA 通过

HACS 是社区分发渠道，WWHA 是 Home Assistant 官方合作认证计划。即使 HACS 默认仓库 PR 合并，也不代表设备获得 WWHA 标识。

### 6.1.1 HACS 与 Core 并行但需要迁移策略

同一集成可以先通过 HACS 收集反馈，再准备 Home Assistant Core 上游。两者不冲突。若未来 Core 接收 `yeelight_pro`，仍安装 HACS/custom 版本的用户会加载 custom integration，从而覆盖 Core 内置版本。Core 接收后需要在 README、release notes 和 issue 模板中提示普通用户删除 custom integration 并重启。

### 6.2 当前 manifest 倾向云端分类

`manifest.json` 当前 `iot_class` 是 `cloud_polling`。WWHA 官方强调本地可用且不依赖云，云只能作为 opt-in。若认证设备必须通过云端才可完成核心功能，认证风险很高。

### 6.3 Gold 质量等级可能要求官方 Core 路径

Home Assistant 的 Integration Quality Scale 主要服务于官方集成。当前 `ha_yeelight_pro` 是 HACS 自定义集成，未见 `quality_scale.yaml`。PM 需要尽早向官方确认：认证是否接受 HACS 集成，还是必须进入 Home Assistant Core 并满足 Gold 质量等级。

### 6.4 固件更新能力未闭环

WWHA 要求设备能在 Home Assistant 中访问 OTA 固件更新；如果不能，需要提供提醒方式。当前集成未看到 `update` 平台或固件提醒闭环，这是认证材料中的高优先级缺口。

### 6.5 设备范围过大可能拖慢认证

Yeelight Pro 品类覆盖较广。WWHA 现在更偏设备级认证，建议首批选择本地链路稳定、关键功能完整、证书齐全、测试样机可控的 SKU，不建议一次性覆盖全部生态。

## 7. 推荐首批认证策略

建议按“低风险、强本地、可演示”的原则选择首批设备：

1. 优先选择通过 LAN gateway 可完成核心控制的 Hub/灯控/面板类设备。
2. 首批设备数量控制在 3-5 个典型 SKU，覆盖灯、开关/面板、窗帘或传感器中的核心代表。
3. 避免首批选择必须依赖云端或移动 App 才能完成核心功能的设备。
4. 每个 SKU 准备一份 Home Assistant 能力矩阵：实体、服务、自动化触发、诊断、固件更新/提醒、已知限制。
5. 每个 SKU 准备断网或不登录云端场景下的本地控制证明。

## 8. 参考资料

- Works with Home Assistant 官方页面：<https://works-with.home-assistant.io/>
- Integration Quality Scale：<https://developers.home-assistant.io/docs/core/integration-quality-scale/>
- Integration Quality Scale Rules：<https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/>
- Integration manifest：<https://developers.home-assistant.io/docs/creating_integration_manifest>
- HACS 发布说明：<https://www.hacs.xyz/docs/publish/start/>
- `ha_yeelight_pro` GitHub 仓库：<https://github.com/Yeelight/ha_yeelight_pro>
- `ha_yeelight_pro` v1.0.4 release：<https://github.com/Yeelight/ha_yeelight_pro/releases/tag/v1.0.4>
- HACS default PR #8516：<https://github.com/hacs/default/pull/8516>
