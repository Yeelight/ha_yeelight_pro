# Yeelight Pro 测试报告

> 测试数量和通过率必须以当前命令输出为准。本文件不固定宣传历史测试数量。

## 当前测试入口

```bash
# Run from the repository root.
python3 -m compileall -q custom_components/yeelight_pro
pytest -q
python3 validate_hacs.py
python3 scripts/verify_local_ha.py
python3 scripts/verify_local_ha.py --repeat 2 --repeat-delay 0
python3 scripts/verify_local_ha.py --soak-seconds 2 --soak-interval 1
python3 scripts/verify_local_ha_soak.py
python3 scripts/verify_local_ha_recovery.py
python3 scripts/check_release_zip.py
python3 scripts/verify_push_websocket.py
python3 scripts/verify_scan_login.py
python3 scripts/verify_cloud_devices.py
python3 scripts/verify_lan_gateway.py
```

当前已验证结果必须以本地最新命令输出为准。本轮已在本地 Home Assistant 验证环境完成启动、实体注册表、手动刷新服务和 cleanup 服务合同实测；受控生产探针默认都必须 fail-closed，并通过显式确认 flag 与环境变量接收授权上下文。

当前覆盖率验证结果：

```bash
pytest --cov --cov-report=term --cov-report=json:coverage.json -q
```

覆盖率结果必须以最新命令输出为准。覆盖重点集中在 registry、projector、coordinator、adapter/converter、持久 product schema cache、diagnostics、Repairs 提示、手动刷新服务、平台实体运行时和回归测试。

## 覆盖重点

- 控制接口必须携带明确 `house_id`。
- 认证失败必须映射到 Home Assistant 重新认证流程。
- 配置流、选项流和翻译 JSON 必须可加载。
- 多区域/多账号 config flow 必须防止同区域同家庭的不同云端账号冲突；扫码登录优先使用账号 ID，手动 token 兜底必须使用脱敏指纹，不能把 token 原文写入 unique_id。
- 易来 IoT 品类投影必须和 Home Assistant 实体平台分离。
- 运行时平台集合必须与 `PLATFORMS` 和发布包内容一致。
- 产品 schema 缓存必须避免同一 PID 每轮重复请求，并在 schema 端点临时失败或 Home Assistant 重启后复用 `.storage` 中已缓存 schema 保持 canonical payload。
- Home Assistant diagnostics 只能导出配置脱敏数据和运行时聚合指标，不能泄露 token、house ID、设备 ID、MAC、私有域名或原始设备 payload。
- diagnostics 必须只输出白名单配置、IoT registry 健康、spec correction 计数、canonical spec runtime inventory、entity candidate 计数、option/runtime 对齐状态、filter preview 聚合和运行时健康状态。filter preview 和 option status 只能输出布尔值与计数，不能输出原始过滤规则、unique_id、device_id、house_id、scene/group id、product model id、component/property/event/action 明细或设备 payload。
- HACS preflight 必须阻断 diagnostics capability flags 漂移：scan-login、push/LAN adapter、live WebSocket opt-in runtime 和 LAN local gateway opt-in runtime 可显式开启。当前云端登录主路径是易来 APP 扫码登录。
- HACS preflight 必须保留设备导入过滤的非破坏性 runtime gate 覆盖：用户选择的导入范围只作用于新的设备来源实体提交路径，并保留用户禁用实体与 scene/group/house 等非设备辅助实体。
- HACS preflight 和本地 HA verifier 必须保留 `device_trigger.py` 与 `tests/test_device_trigger.py`，确保事件型设备、场景面板和带事件的开关组件持续暴露 Home Assistant device trigger 自动化入口。
- 本地 HA verifier 必须同时校验 `services.yaml`、安装态 Python 运行时服务注册、服务字段 required 状态和文档 selector，阻断服务定义、文档字段和 handler schema 漂移。
- 本地 HA verifier 必须校验安装态 `strings.json`、`translations/en.json`、`translations/zh-Hans.json`：三份文件叶子 key 路径完全一致，关键 config/options/services/Repairs 翻译路径存在，服务翻译与 `services.yaml` 服务集合一致，已翻译的服务字段集合跨语言一致且不得超出 `services.yaml` 字段；Repairs issue 翻译文本中的 `{placeholder}` 必须与安装态 `repair_issues.py` 实际传入的 `translation_placeholders` 完全一致。
- 本地 HA verifier 必须校验安装态 diagnostics capability flags：当前已验证的 scan-login、push/LAN adapter、live WebSocket opt-in runtime 和 LAN local gateway opt-in runtime。
- 本地 HA verifier 支持 `--repeat` / `--repeat-delay` 短时重复验证，用于在不调用云端真实 API、不重启 HA 的情况下重复确认安装态、实体数量、服务注册、diagnostics 能力边界、日志和 URL 健康。
- 本地 HA verifier 支持 `--soak-seconds` / `--soak-interval` 有界稳定性窗口，用于在指定时间窗口内追加多轮采样；窗口内任一轮失败都必须阻断验证。
- `scripts/verify_local_ha_soak.py` 是 dedicated 外部稳定性入口，默认使用有界窗口并复用同一套本地 HA verifier，不复制安装态、registry、服务、i18n、diagnostics、日志恢复、Docker 和 URL 检查逻辑。
- `scripts/verify_local_ha_recovery.py` 是 dedicated 容器内恢复/日志验证入口，默认执行重复验证并扩大日志 tail；该入口需要 Docker 日志访问，会拒绝 `--skip-docker`，避免绕过恢复与日志健康检查。
- 本地 HA verifier 的 repeat/soak 多轮模式必须比较关键聚合指标稳定性：config entry 数量和版本、设备数、实体总数、实体 domain 分布、服务注册列表、diagnostics capability 边界和可选配置键缺失计数。任一指标跨轮漂移都必须阻断验证。
- 本地 HA verifier 的日志恢复判断必须按日志行顺序处理；临时轮询错误只有在后续出现 HA 恢复标记时才可降级为已恢复事实，恢复标记之后再次出现的错误必须继续阻断验证。
- 本地 HA verifier 必须校验安装态 config entry 已迁移到当前版本且包含运行时必需键；手动 token 旧 entry 可缺少 `open_api_client_id`，但只能作为聚合事实记录，不能泄露 token、house 或域名值。
- 本地 HA verifier 必须校验安装态 config entry options 已包含 `scan_interval`、`debug_mode`、`hide_unknown_entities`、`topology_change_repairs`，并校验 `scan_interval` 范围和布尔选项类型；`device_import_filter` 只允许以缺失计数和启用计数形式输出，不能输出过滤规则内容。
- 本地 HA verifier 必须校验安装态实体 domain 与当前 `PLATFORMS` 对齐；任何未加载平台的旧 registry entry 若仍启用都必须阻断验证。
- 本地 HA verifier 必须校验安装态 config/options flow 源码契约：options flow 必须通过 `merge_options` 保留高级字段、通过 `normalize_entry_options` 比较确认页、通过 `options_require_reload` 区分 runtime/reload 变更，config flow 必须仍返回 `YeelightProOptionsFlow`。
- 拓扑变化 Repairs issue 只在 topology generation 变化且选项启用时创建，不能因普通状态轮询重复创建；该选项默认启用以保持现有行为。
- `yeelight_pro.refresh` 只能做只读刷新和 registry reconciliation，不能绕过现有控制 API 引入新的写路径。
- fan projector 纯值转换逻辑已拆分到 `projector/fan_value_helpers.py`，`projector/fan_helpers.py` 保留组件识别、控制键和投影支撑边界；旧 `projector.fan` import 路径保持兼容。
- coordinator 的已接收 runtime/push/LAN payload 处理已拆分到 `core/coordinator_runtime.py`，`core/coordinator.py` 保留轮询、控制和拓扑协调主流程；live WebSocket 与 LAN TCP runtime 由显式 options 启用，默认仍走轮询。
- WebSocket 事件通知只走 `live_updates` 显式 opt-in runtime；transport 只派发 `type=prop` / `type=event` 业务 payload。`subscribe` / `heartbeat` ACK 控制帧不进入 coordinator payload 计数，控制帧错误只记录 `PushControlFrameError` 这类脱敏异常类型并关闭当前 websocket 进入既有重连边界。
- `scripts/verify_push_websocket.py` 提供默认 no-network 的生产 WebSocket 验证入口；只有同时传入 `--confirm-production-websocket` 且通过 `YEELIGHT_PRO_PUSH_TOKEN` 环境变量提供 token 时才会连接生产 WebSocket。输出只包含帧数、业务/控制帧计数、字段形态和错误类型等聚合脱敏摘要，不输出 token、URL、原始 payload、设备 ID、MAC 或家庭信息。
- dedicated soak/recovery 脚本已有单元测试和 release preflight 覆盖；候选版本在容器上执行这些入口并复核脱敏输出。

## 生产探针矩阵

- WebSocket：`scripts/verify_push_websocket.py`，显式确认 flag 为 `--confirm-production-websocket`，授权上下文来自 `YEELIGHT_PRO_PUSH_TOKEN`。
- 扫码登录：`scripts/verify_scan_login.py`，显式确认 flag 为 `--confirm-production-scan-login`，授权上下文来自 `YEELIGHT_PRO_SCAN_LOGIN_DEVICE`。
- 真实设备列表：`scripts/verify_cloud_devices.py`，显式确认 flag 为 `--confirm-production-cloud-devices`，授权上下文来自 `YEELIGHT_PRO_CLOUD_ACCESS_TOKEN` 和 `YEELIGHT_PRO_CLOUD_HOUSE_ID`。
- LAN 网关：`scripts/verify_lan_gateway.py`，显式确认 flag 为 `--confirm-production-lan-gateway`，授权上下文来自 `YEELIGHT_PRO_LAN_GATEWAY_HOST`。
- 所有生产探针输出只包含脱敏聚合结果，不输出 token、URL、house id、client id、host、port、设备 id/name、房间、MAC 或原始 payload。

## 本地 Home Assistant 实测

- 验证环境由本地 Home Assistant 配置目录和 Docker 运行环境决定。
- 最近一次安装态更新以最新 `scripts/sync_local_ha_runtime.py` 和
  `scripts/verify_local_ha.py` 输出为准。
- 本地安装态关键模块存在检查通过：`refresh_service`、`schema_cache`、`client`、`client_request`、`coordinator_runtime`、`diagnostics`、`diagnostic_options`、`device_trigger`、`repair_issues`、`debug_service`；真实运行时导入结果以 HA 日志无 `ImportError` / `ModuleNotFoundError` 和 setup completion 为准。
- 当前本地 HA 事实以 `python3 scripts/verify_local_ha.py` 的脱敏聚合输出为准。
- 本地 HA verifier 已确认服务定义、运行态注册和字段/schema 合同一致：`assign_areas`、`auto_assign_areas`、`debug_emit_event`、`debug_dump_push_health`、`debug_emit_push_payload`、`refresh`、`cleanup_registry`。
- 本地 HA 前端实测已确认 Yeelight Pro 可在“添加集成”中搜索到，配置流 `user` 步骤可打开，cloud 分支可进入“云端认证方式”和 Access Token 表单，private 分支可进入私有部署表单；验证过程中未提交真实 token。
- 本地 HA verifier 已确认安装态服务集合包含当前 7 个服务：`assign_areas`、`auto_assign_areas`、`debug_emit_event`、`debug_dump_push_health`、`debug_emit_push_payload`、`refresh`、`cleanup_registry`。
- 本地 HA verifier 已确认安装态 i18n 合同：`strings.json`、`translations/en.json`、`translations/zh-Hans.json` 叶子 key 对齐，关键 config/options/services/Repairs 路径存在，服务翻译和当前 `services.yaml` 服务集合一致，Repairs 翻译占位符与运行态 `translation_placeholders` 对齐。
- 本地 HA verifier 已确认 diagnostics capability flags 边界：扫码登录、多区域、push/LAN contract 和显式 opt-in runtime flags 均通过安装态校验。
- 本地 HA verifier 已确认 config entry options 边界：必需 option keys、`scan_interval` 范围、布尔类型和 device import filter 聚合状态均通过安装态校验。
- 本地 HA verifier 已确认平台/options 对齐：实际实体 domain 与当前 `PLATFORMS` 匹配，未加载平台不会出现在启用实体中。
- 本地 HA verifier 已确认 flow 契约：options flow 的 merge/reload 确认边界和 config flow 的 options factory 均存在。
- 本地 HA verifier 已通过单元测试覆盖日志恢复顺序：恢复前的临时轮询错误可记录为已恢复事实，恢复后再次出现且没有新恢复标记的错误会作为未恢复运行时错误阻断。
- 本地 HA verifier 已通过单元测试和 preflight 合同覆盖 repeat/soak 多轮稳定性指标：匹配时记录稳定事实，实体数量等关键指标漂移时整体失败。
- `python3 scripts/verify_local_ha.py --repeat 2 --repeat-delay 0` 已完成两轮本地 HA 短跑验证，运行时必需键和必需 options、实体数量、服务注册、diagnostics flags、日志和 URL 健康均通过；本地手动 token entry 缺少可选 `open_api_client_id` 和可选 `device_import_filter`，已按兼容事实记录。
- `python3 scripts/verify_local_ha.py --soak-seconds 2 --soak-interval 1` 已完成有界本地 HA 稳定性窗口验证，窗口内采样的 config entry、options、实体数量、服务注册、diagnostics flags、日志和 URL 健康均通过。
- HA 后端日志显示 Yeelight Pro 集成完成加载，未发现 `yeelight_pro` 相关 `ERROR`、`Traceback`、`ImportError` 或平台加载失败。
- HA entity registry 中 `yeelight_pro` 实体以最新 verifier 脱敏聚合输出为准；registry cleanup 通过 `cleanup_registry` 的 dry-run + audit_id confirm 禁用 stale entries。
- 已通过登录态 HA 前端上下文调用 `yeelight_pro.refresh`，服务返回 200；日志显示 `Manual Yeelight Pro refresh completed for 1 config entries`，registry reconciliation 聚合数量以最新 verifier 为准。
- 当前真实样本的 `.storage/yeelight_pro.product_schemas` 由 schema cache verifier 和启动路径共同覆盖；本地 HA 事实以最新 verifier 输出为准。
