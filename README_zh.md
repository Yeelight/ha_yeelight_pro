# Yeelight Pro

[English](README.md) | [中文](README_zh.md)

Yeelight Pro Home Assistant 集成，支持通过同一个配置流程接入易来云端和私有部署。

## 当前状态

- 集成状态：发布前加固
- 已验证测试：见 [docs/TEST_REPORT.md](docs/TEST_REPORT.md)
- 默认启用平台：声明 14 个，默认启用 13 个
- 实验平台：`vacuum`
- 不作为发布平台：`text`
- 更新方式：云端轮询，轮询间隔可配置
- HACS/官方社区：当前工作区尚未发布

## 功能

- 云端和私有部署配置流程
- Token 失效时触发 Home Assistant 标准重新认证
- 通过多区域账号 API 接入易来 APP 扫码登录；二维码登录是当前云端登录主路径
- 已测试的易来 OAuth token endpoint 客户端辅助能力和手动授权码配置路径；完整 Home Assistant webhook/redirect OAuth 登录不是当前发布目标
- 可配置轮询间隔、调试模式、实验平台、未知能力隐藏策略、手动非破坏性设备导入过滤和拓扑 Repairs 提示
- canonical -> adapter -> converter -> projector -> entity 分层架构
- 轻量 Yeelight IoT 物模型注册表，集中表达品类、组件、属性、事件、协议和 `nodeType`
- 持久化 Home Assistant `.storage` 产品 schema 缓存，重启后仍保持稳定的 schema-aware 投影
- 网关和子设备拓扑同步到 Home Assistant 设备注册表
- Home Assistant 诊断导出，配置使用白名单输出，并包含 IoT registry 健康、spec correction 计数、canonical spec runtime inventory、实体候选计数和运行时健康聚合
- 非破坏性设备/实体导入过滤诊断预览，以及保守的运行时新增 gate：可阻止未来新增的设备来源实体，但不会删除、禁用、隐藏或迁移既有实体和设备注册表条目
- 设备拓扑在启动后变化时可选创建 Home Assistant Repairs 提示，包含脱敏的新增/移除/元数据变化计数
- `debug_mode` 控制的调试事件服务
- 只读手动刷新服务，可立即刷新已加载 coordinator 并同步 HA 设备/实体注册表
- 云端配置期和后续 options 真实设备 picker：选择家庭后可只读拉取该家庭设备列表，并把用户勾选的设备 ID 保存为后续设备来源实体的导入过滤规则；若设备列表加载失败，仍可继续创建 entry 或保持现有过滤规则不变
- 注册表清理服务：先 dry-run 返回 audit_id，二次确认后仅通过 Home Assistant registry 禁用 stale entities，不删除实体或设备注册表条目
- 英文和简体中文翻译

## 支持的易来 IoT 品类

下面是易来 IoT 品类，不是 Home Assistant 实体平台。

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

`event`、`scene`、`button`、`select`、`number`、`vacuum` 和 `text` 是 Home Assistant 实体平台或实验投影目标，不是易来 IoT 设备品类。`vacuum` 仅作为未来兼容的实验平台，默认不启用。

物模型注册表边界见 [docs/IOT_SPEC_REGISTRY.md](docs/IOT_SPEC_REGISTRY.md)；ha_xiaomi_home 架构对比、已借鉴思想和后续决策点见 [docs/HA_XIAOMI_HOME_GAP_REVIEW.md](docs/HA_XIAOMI_HOME_GAP_REVIEW.md)。

## 安装

### 手动安装

1. 运行 `python3 scripts/sync_local_ha_runtime.py --config-dir /path/to/homeassistant/config`，只把运行时文件同步到 Home Assistant 的 `custom_components` 目录，不复制测试或生成产物。
2. 重启 Home Assistant。
3. 进入 设置 -> 设备与服务 -> 添加集成 -> Yeelight Pro。

### HACS

当前仓库已包含 HACS 元数据和发布包校验入口，但应在本地 HA 实测和发布审查完成后再提交 HACS。

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
- 实验平台：启用 `vacuum` 等实验平台
- 隐藏未知能力实体：避免把不确定能力泛化成普通实体
- 设备导入过滤：可编辑保守的手动规则；云端 entry 可重新打开真实设备 picker，在配置后继续调整选中设备
- 拓扑变化 Repairs 提示：设备/实体拓扑在启动后变化时创建 Home Assistant Repairs issue，并包含聚合数量和脱敏 diff 计数，默认启用

## 服务

### `yeelight_pro.assign_areas`

批量为 Yeelight Pro 设备分配 Home Assistant 区域。

### `yeelight_pro.auto_assign_areas`

根据设备名称中的房间关键词自动分配区域。

### `yeelight_pro.debug_emit_event`

发射标准化 Yeelight Pro 运行时事件，用于开发和排障。该服务需要在集成选项中启用 `debug_mode`。

### `yeelight_pro.refresh`

立即刷新已加载的 Yeelight Pro 数据，并执行设备/实体注册表同步。可选 `entry_id` 用于限定单个配置条目。

## 开发

```bash
cd extensions/ha_yeelight_pro
pytest -q
python3 -m compileall -q custom_components/yeelight_pro scripts hacs_publish.py
ruff check custom_components/yeelight_pro scripts hacs_publish.py
mypy --ignore-missing-imports --explicit-package-bases custom_components/yeelight_pro scripts hacs_publish.py
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

## 已知缺口

- 完整 Home Assistant webhook/redirect OAuth 登录未实现，因为当前云端登录主路径是易来
  APP 扫码登录。若未来产品方向重新启用 OAuth，再需要易来分配凭据、redirect 策略、
  CSRF state 处理和 token 生命周期规则后进入实现。
- 多区域 API 域名已实现。多个云端账号可通过不同 config entry 共存，账号隔离优先使用扫码登录账号元数据、Open API clientId，手动 token 兜底使用脱敏 token 指纹；单个 config entry 内多账号 UX 仍是路线图能力。
- 本地网关 TCP 控制可通过显式 options 启用；当 `local_gateway_control` 已启用且 host 为空时，runtime 会先按局域网协议尝试一次 UDP 广播发现，再打开 TCP 连接。mDNS、持续网络扫描、云端/LAN 拓扑合并和实物验证仍是路线图能力。
- WebSocket 推送消息构造器、注入式 PushManager 和显式 opt-in live WebSocket runtime 已有测试覆盖。易来事件通知资料只给出 WebSocket，因此云端事件通知在显式启用 `live_updates` 后只按 WebSocket 实现；默认拓扑刷新和全量状态兜底仍使用轮询。
- 尚未实现完整规则/spec filter 引擎。
- 设备导入过滤当前支持 diagnostics 预览、逗号分隔的手动 options 规则、云端配置期和后续 options 真实设备 picker，以及保守的未来新增实体 gate。若云端设备列表加载失败，配置仍可继续，options 不会覆盖现有过滤规则。既有 registry 清理仅以显式 dry-run 加 audit_id 二次确认禁用 stale entity 的形式提供；删除、隐藏、迁移和设备注册表清理语义仍是路线图能力。

## 许可证

MIT License
