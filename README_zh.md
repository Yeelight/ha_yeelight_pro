# Yeelight Pro

[English](README.md) | [中文](README_zh.md)

Yeelight Pro Home Assistant 集成，支持通过同一个配置流程接入易来云端、私有部署和局域网网关模式。

## 当前状态

- 集成状态：`v1.0.4` 发布包已可用
- 已验证测试：见 [docs/TEST_REPORT.md](docs/TEST_REPORT.md)
- 启用的 Home Assistant 平台：11 个
- 运行时平台：`binary_sensor`、`button`、`climate`、`cover`、`event`、
  `fan`、`light`、`number`、`select`、`sensor`、`switch`
- 更新方式：轮询仍是默认全量状态刷新路径，轮询间隔可配置
- HACS/官方社区：HACS 默认仓库 PR
  [#8516](https://github.com/hacs/default/pull/8516) 审查中

## Works with Home Assistant 和 Core 准备状态

Yeelight 正在准备选择部分 Yeelight Pro 设备或 Hub 申请 Works with Home
Assistant。本文档不代表已经获得认证：HACS 审核、Home Assistant Core 上游、
Integration Quality Scale Gold 和 Works with Home Assistant 审批是相互独立的门槛。

规划和交底材料：

- [WWHA 交底文档](docs/WORKS_WITH_HOME_ASSISTANT_HANDOVER.md)
- [WWHA 申请指南](docs/WORKS_WITH_HOME_ASSISTANT_APPLICATION_GUIDE.md)
- [Core 和 HACS 迁移策略](docs/CORE_MIGRATION_STRATEGY.md)
- [Gold 质量等级差距分析](docs/QUALITY_SCALE_GOLD_GAP_ANALYSIS.md)
- [本地控制模型](docs/LOCAL_CONTROL.md)
- [支持设备模板](docs/SUPPORTED_DEVICES.md)
- [故障排查](docs/TROUBLESHOOTING.md)
- [自动化示例](docs/AUTOMATION_EXAMPLES.md)

## 功能

- 云端、私有部署和局域网网关配置流程
- Token 失效时触发 Home Assistant 标准重新认证
- 通过多区域账号 API 接入易来 APP 扫码登录；二维码登录是当前云端登录主路径
- 可配置轮询间隔、调试模式、未知能力隐藏策略、手动非破坏性设备导入过滤和拓扑 Repairs 提示
- 云端事件通知使用显式 `live_updates` WebSocket runtime；私有部署 entry 使用同一 runtime，并可配置私有推送 URL；轮询仍是默认全量状态刷新路径
- 局域网网关 runtime 位于局域网连接模式和 `local_gateway_control` 选项边界内
- canonical -> adapter -> converter -> projector -> entity 分层架构
- 轻量 Yeelight IoT 物模型注册表，集中表达品类、组件、属性、事件、协议和 `nodeType`
- 持久化 Home Assistant `.storage` 产品 schema 缓存，重启后仍保持稳定的 schema-aware 投影
- 网关和子设备拓扑同步到 Home Assistant 设备注册表
- 房屋级数据分析诊断传感器，暴露报警、能耗、用户操作和端点健康聚合；可选分析端点失败时降级为 unavailable 诊断值，不阻断集成加载
- Home Assistant 诊断导出，配置使用白名单输出，并包含 IoT registry 健康、spec correction 计数、canonical spec runtime inventory、实体候选计数和运行时健康聚合
- 非破坏性设备/实体导入过滤诊断预览，以及保守的运行时新增 gate：在提交新的设备来源实体前应用用户选择的导入范围
- 设备拓扑在启动后变化时可选创建 Home Assistant Repairs 提示，包含脱敏的新增/移除/元数据变化计数
- `debug_mode` 控制的调试事件服务
- 只读手动刷新服务，可立即刷新已加载 coordinator 并同步 HA 设备/实体注册表
- 云端配置期和后续 options 真实设备 picker：选择家庭后可只读拉取该家庭设备列表，并把用户勾选的设备 ID 保存为后续设备来源实体的导入过滤规则；若设备列表加载失败，仍可继续创建 entry 或保持现有过滤规则不变
- 注册表清理服务：先 dry-run 返回 audit_id，二次确认后通过 Home Assistant registry 禁用 stale entities
- 英文和简体中文翻译

## 支持的易来 IoT 品类

下表列出易来 IoT 品类和当前 Home Assistant 投影方式。

| 易来品类 | 默认 HA 投影 | 状态 |
| --- | --- | --- |
| `light` | `light` | 稳定 |
| `contact_sensor` | `binary_sensor` | 稳定 |
| `human_sensor` | `binary_sensor` | 稳定 |
| `light_sensor` | `sensor` | 稳定 |
| `curtain` | `cover` | 稳定 |
| `temp_control` | `climate` | 稳定 |
| `relay_switch` | `switch` | 稳定 |
| `scene_panel` | `event` + device trigger | 稳定 |
| `gateway` | 设备注册表拓扑 | 稳定 |
| `knob_switch` | `event` + device trigger | 稳定 |
| `other` | 仅明确属性降级为传感器 | 保守支持 |

云端情景通过 `button` 实体执行易来情景接口。

物模型注册表边界和发布映射合同见 [docs/IOT_SPEC_REGISTRY.md](docs/IOT_SPEC_REGISTRY.md)。

## 安装

### 手动安装

1. 运行 `python3 scripts/sync_local_ha_runtime.py --config-dir /path/to/homeassistant/config`，只把运行时文件同步到 Home Assistant 的 `custom_components` 目录，不复制测试或生成产物。
2. 重启 Home Assistant。
3. 进入 设置 -> 设备与服务 -> 添加集成 -> Yeelight Pro。

### HACS

GitHub `v1.0.4` release 已包含 HACS zip 资产 `yeelight_pro.zip`。HACS 默认仓库 PR
[#8516](https://github.com/hacs/default/pull/8516) 仍在审查中；该 PR 合并前，请在
HACS 中把本仓库作为自定义集成仓库安装。

## 配置

### 云端模式

1. 选择 Yeelight Pro 云端模式。
2. 选择易来账号所在区域。
3. 使用易来 APP 1.5.0 或以上版本扫描 Home Assistant 展示的二维码。Home Assistant 会持续轮询，直到 APP 授权返回 token 或 5 分钟二维码过期。
4. 选择 API 返回的家庭。

手动 Access Token 配置仍作为高级兜底路径保留。

### 私有部署模式

1. 选择私有部署模式。
2. 输入私有服务器地址。
3. 输入 Access Token 和家庭 ID。

## 选项

在集成选项中可配置：

- 轮询间隔：10-300 秒，默认 30 秒
- 调试模式：启用 `yeelight_pro.debug_emit_event`
- 隐藏未知能力实体：避免把不确定能力泛化成普通实体
- 设备导入过滤：可编辑保守的手动规则；云端 entry 可重新打开真实设备 picker，在配置后继续调整选中设备
- 实时更新：云端/私有部署 entry 可启用 WebSocket runtime
- 私有推送 URL：私有部署 entry 可覆盖 WebSocket 推送端点
- 本地网关控制：局域网 entry 可配置网关 host 和端口
- 拓扑变化 Repairs 提示：设备/实体拓扑在启动后变化时创建 Home Assistant Repairs issue，并包含聚合数量和脱敏 diff 计数，默认启用

## 服务

### `yeelight_pro.assign_areas`

批量为 Yeelight Pro 设备分配 Home Assistant 区域。

### `yeelight_pro.auto_assign_areas`

根据设备名称中的房间关键词自动分配区域。

### `yeelight_pro.debug_emit_event`

发射标准化 Yeelight Pro 运行时事件，用于开发和排障。该服务需要在集成选项中启用 `debug_mode`。

### `yeelight_pro.debug_dump_push_health`

向 Home Assistant 日志写入聚合后的 WebSocket 推送健康信息，用于开发和排障。该服务需要启用 `debug_mode`。

### `yeelight_pro.debug_emit_push_payload`

向 runtime bridge 注入一条合成属性推送。该服务需要启用 `debug_mode`，不会控制真实设备。

### `yeelight_pro.refresh`

立即刷新已加载的 Yeelight Pro 数据，并执行设备/实体注册表同步。可选 `entry_id` 用于限定单个配置条目；可选 `refresh_product_schemas` 会刷新产品物模型，失败时回退已缓存 schema。

### `yeelight_pro.cleanup_registry`

执行 stale entity registry cleanup dry-run 预览。确认执行时必须提供同一个 `entry_id` 和 dry-run 返回的 `audit_id`；确认后通过 Home Assistant entity registry 禁用 stale entities。

## 开发

```bash
cd extensions/ha_yeelight_pro
pytest -q
python3 -m compileall -q custom_components/yeelight_pro scripts hacs_publish.py
ruff check custom_components/yeelight_pro scripts hacs_publish.py
mypy --ignore-missing-imports --explicit-package-bases --exclude custom_components/yeelight_pro/tests custom_components/yeelight_pro scripts hacs_publish.py
python3 validate_hacs.py
python3 scripts/check_release_zip.py
python3 scripts/sync_local_ha_runtime.py
python3 scripts/verify_local_ha.py
python3 scripts/verify_local_ha_soak.py
python3 scripts/verify_local_ha_recovery.py
```

以下受控生产探针用于授权后的外部验证；没有显式确认 flag 时必须保持 fail-closed：

```bash
python3 scripts/verify_push_websocket.py
python3 scripts/verify_scan_login.py
python3 scripts/verify_cloud_devices.py
python3 scripts/verify_lan_gateway.py
```

CI/release 入口保留在 `.github/workflows/test.yaml`、`.github/workflows/validate.yaml` 和 `.github/workflows/release.yaml`。

不要提交 token、Home Assistant 账号密码、真实家庭 ID 或原始设备数据。测试样本必须脱敏。

## 运行时模型

- 区域和账号隔离基于 config entry：每个云端账号、区域和家庭组合对应一个 Home Assistant 配置条目。
- 云端事件通知使用显式 `live_updates` WebSocket runtime；私有部署 entry 使用同一 runtime，并可配置私有推送 URL；轮询仍作为默认全量状态刷新路径。
- 本地网关控制通过局域网模式 entry 暴露；启用 `local_gateway_control` 且未配置 host 时，runtime 会按局域网协议执行一次 UDP 发现，再建立 TCP 网关会话。
- 设备导入过滤结合 diagnostics 预览、手动 options 规则、setup/options 真实设备 picker 选择，以及提交新设备来源实体前的保守 gate。
- 既有 registry 清理通过显式 dry-run 加 audit_id 二次确认服务执行，并通过 Home Assistant registry 禁用 stale entities。

## 许可证

MIT License
