# Home Assistant Core and HACS Migration Strategy

更新时间：2026-06-22

## 目标

本文说明 `ha_yeelight_pro` 在继续维护 HACS 发布路径的同时，如何准备 Home Assistant Core 上游和 Works with Home Assistant 认证材料。

## 结论

HACS 和 Home Assistant Core 可以并行推进，不存在天然冲突：

- HACS 适合作为社区安装、公开试用、快速发版和反馈收集渠道。
- Home Assistant Core 适合作为官方内置集成、Integration Quality Scale、官方文档、品牌和 WWHA 合作流程的长期路径。
- 已经提交或进入 HACS 审核，不会阻止同一集成后续贡献到 Home Assistant Core。

## 关键兼容风险

如果未来 Home Assistant Core 接收同一个 `domain=yeelight_pro`，而用户本地仍安装 `custom_components/yeelight_pro`，Home Assistant 会优先加载 custom integration。结果是 HACS/custom 版本会覆盖 Core 内置版本。

这种覆盖机制可用于开发和测试，但不适合长期让普通用户保留。长期覆盖会让用户错过 Core 集成更新，也会让问题排查难以判断实际加载的是 HACS 版本还是 Core 版本。

## 推荐路线

### 1. 当前 HACS 阶段

- 保持 `domain=yeelight_pro` 不变。
- 继续使用 `hacs.json` 和 GitHub release zip。
- custom integration 的 `manifest.json` 保留 `version` 字段。
- README 明确 HACS 默认仓库 PR 仍在审核中，不宣称已经合并或认证。
- 将 WWHA、Gold 和 Core 相关内容放入 docs，避免 README 过度宣传。

### 2. Core 上游准备期

- 维护 Core delta 清单：
  - Core manifest 不应包含 custom integration 的 `version` 字段。
  - Core 需要官方文档、brands、质量等级文件和更严格的测试材料。
  - Core 代码需要尽量使用 `ConfigEntry.runtime_data`，减少平台直接读取 `hass.data`。
  - 每个平台需要明确 `PARALLEL_UPDATES`。
  - 需要 `async_step_reconfigure` 或官方接受的 reconfigure 体验。
- 不建议为了规避覆盖风险改成 `yeelight_pro_hacs` 之类的新 domain。改 domain 会制造 config entry、device registry、entity unique id 和用户自动化迁移成本。

### 3. Core 接收后

如果 Core PR 被接收，建议采用迁移公告期：

1. HACS README 和 release notes 明确提示：普通用户应删除 `custom_components/yeelight_pro`，重启 Home Assistant，改由 Core 内置集成加载。
2. HACS 仓库进入维护/迁移状态，只发布安全、兼容或迁移辅助更新。
3. 若仍需要实验功能，放入明确标注的 beta/experimental 分支，不让默认用户长期覆盖 Core。
4. issue 模板要求用户说明实际加载路径：Core 内置还是 `custom_components`。
5. 文档继续说明同 domain custom integration 会覆盖 Core。

## 当前差异清单

| 项目 | HACS 当前状态 | Core 预期 | 当前处理 |
| --- | --- | --- | --- |
| `manifest.json` `version` | 必需 | 不应保留 | HACS 保留，Core 分支移除 |
| `hacs.json` | 必需 | 不适用 | HACS 保留，Core 不提交 |
| `domain` | `yeelight_pro` | `yeelight_pro` | 保持一致，降低迁移成本 |
| quality scale | 可用 gap analysis 跟踪 | Core 使用质量等级文件 | 先维护 gap analysis |
| 分发 | GitHub release zip / HACS | HA Core release | 双轨准备 |
| 用户迁移 | custom integration | Core built-in | Core 接收后提示删除 custom |

## PM 对外口径

可以说：

- Yeelight 正在用 HACS 社区发布渠道收集反馈，并评估 Home Assistant Core 上游路径。
- HACS 和 Home Assistant Core 不是互斥路径。
- 若官方认证或 Gold 要求 Core，研发侧会准备 Core 上游差异。

不要说：

- HACS 审核通过等同于 Home Assistant Core 接收。
- HACS 审核结果等同于 WWHA 官方审批结果。
- `ha_yeelight_pro` 当前已经完成官方质量等级目标。
- Core 接收后用户可以永久保留 HACS 版本且没有影响。

## 研发待办

- 将 runtime data 迁移到 `ConfigEntry.runtime_data` 主路径，并保留 `hass.data` 兼容镜像。
- 为所有平台补齐 `PARALLEL_UPDATES`。
- 实现 reconfigure flow。
- 为 WWHA 候选设备补齐本地模式主路径和发现说明。
- 根据官方反馈判断是否需要 Core PR 作为 WWHA 前置条件。
