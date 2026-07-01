# Yeelight Pro

[English](README.md) | [中文](README_zh.md)

Yeelight Pro 是面向 Home Assistant 的易来 Pro 自定义集成，用于接入易来
Pro 家庭、设备、网关、情景和运行时诊断。它通过同一个配置流程支持易来云端、
私有部署和局域网网关三种连接模式。

## 当前状态

- 当前版本：`v1.0.5`，已提供 HACS zip 资产 `yeelight_pro.zip`
- HACS 默认仓库 PR：
  [#8516](https://github.com/hacs/default/pull/8516)，审查中
- 提前体验方式：在 HACS 中把本仓库添加为自定义集成仓库
- HACS 元数据目标：HACS `2.0.0`，Home Assistant `2024.1.0`
- 已验证测试和发布门禁：见 [docs/TEST_REPORT.md](docs/TEST_REPORT.md)
- 启用的 Home Assistant 平台：11 个
- 运行时平台：`binary_sensor`、`button`、`climate`、`cover`、`event`、
  `fan`、`light`、`number`、`select`、`sensor`、`switch`
- 更新方式：轮询仍作为默认全量状态刷新路径，轮询间隔可配置。云端和私有部署事件通知使用显式 `live_updates` WebSocket runtime。

## 功能

- 云端、私有部署和局域网网关三种配置流程
- 通过多区域账号 API 接入易来 APP 扫码登录；二维码登录是当前云端登录主路径
- 为既有易来 Pro 部署保留高级手动 Access Token 配置
- Token 失效时触发 Home Assistant 标准重新认证
- 可配置轮询间隔、调试模式、未知能力隐藏策略、非破坏性设备导入过滤、实时更新、本地网关控制和拓扑 Repairs 提示
- 同时读取 v1 和 v2 产品 schema，并用保守合并策略最大化能力覆盖
- 持久化 Home Assistant `.storage` 产品 schema 缓存，重启后仍保持稳定的 schema-aware 投影
- canonical -> adapter -> converter -> projector -> entity 分层架构
- 轻量 Yeelight IoT 物模型注册表，集中表达品类、组件、属性、事件、协议和 `nodeType`
- 网关、子设备、情景、分组、房间、区域和家庭级辅助实体同步到 Home Assistant 设备注册表
- 房屋级数据分析诊断传感器，暴露报警、能耗、用户操作和端点健康聚合；可选分析端点失败时降级为 unavailable 诊断值，不阻断集成加载
- Home Assistant 诊断导出，配置使用白名单输出，并包含 IoT registry 健康、spec correction 计数、canonical spec runtime inventory、实体候选计数、设备导入预览和运行时健康聚合
- 非破坏性设备/实体导入过滤：用户选择的设备或手动规则只限制新的设备来源实体提交，不会删除、隐藏、迁移或禁用既有 registry 条目
- 云端配置期和后续 options 真实设备 picker：若设备列表加载失败，setup 可继续创建 entry 且不启用过滤，options 会保留既有过滤规则
- 注册表清理服务：先 dry-run 返回 audit_id，二次确认后通过 Home Assistant entity registry 禁用 stale entities
- `debug_mode` 控制的调试服务
- 只读手动刷新服务，可立即刷新已加载 coordinator 并同步 Home Assistant 设备/实体注册表
- 英文和简体中文翻译

## 安装

### HACS 安装

[![打开 Home Assistant 并把本仓库添加到 HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Yeelight&repository=ha_yeelight_pro&category=integration)

HACS 默认仓库 PR
[#8516](https://github.com/hacs/default/pull/8516) 仍在审查中。在 PR 合并前，极客用户可以通过 HACS 自定义仓库提前体验。该流程遵循 HACS 的自定义仓库模型：添加仓库 URL、选择正确仓库类型，再从 HACS 下载集成。

要求：

- Home Assistant `2024.1.0` 或以上
- HACS `2.0.0` 或以上
- 安装任何自定义集成前，先备份 Home Assistant

快捷方式：

1. 点击上方 **打开 Home Assistant 并把本仓库添加到 HACS** 按钮。
2. 在 Home Assistant 中确认添加仓库。
3. 确认分类为 **Integration**。
4. 在 HACS 中安装 **Yeelight Pro**。
5. 重启 Home Assistant。
6. 进入 **设置 -> 设备与服务 -> 添加集成**。
7. 搜索 **Yeelight Pro** 并开始配置。

手动添加自定义仓库：

1. 打开 Home Assistant。
2. 进入 **HACS**。
3. 点击右上角三个点菜单。
4. 选择 **Custom repositories**。
5. 在 **Repository** 中填写：

   ```text
   https://github.com/Yeelight/ha_yeelight_pro
   ```

6. 在 **Type** 中选择 **Integration**。
7. 点击 **Add**。
8. 在 HACS 中搜索 **Yeelight Pro**。
9. 打开仓库页面并点击 **Download**。如果 HACS 要求选择版本，选择最新 release。
10. 重启 Home Assistant。
11. 进入 **设置 -> 设备与服务 -> 添加集成**。
12. 搜索 **Yeelight Pro** 并开始配置。

如果重启后仍找不到集成，刷新浏览器缓存，并确认 HACS 已把它安装到 Home
Assistant 配置目录下的 `custom_components/yeelight_pro/`。

参考：

- HACS 自定义仓库：
  <https://www.hacs.xyz/docs/faq/custom_repositories/>
- HACS 集成仓库类型：
  <https://www.hacs.xyz/docs/use/repositories/type/integration/>

### 手动开发安装

该路径用于本地开发或 QA，不建议普通 HACS 用户使用。

```bash
python3 scripts/sync_local_ha_runtime.py --config-dir /path/to/homeassistant/config
```

然后重启 Home Assistant，进入
**设置 -> 设备与服务 -> 添加集成 -> Yeelight Pro**。

不要把整个源码目录复制进 Home Assistant。同步脚本只复制运行时文件，并排除测试、缓存和生成产物。

## 配置

### 云端模式

1. 选择 Yeelight Pro 云端模式。
2. 选择易来账号所在区域：CN、SG、US 或 DE。
3. 使用易来 APP 1.5.0 或以上版本扫描 Home Assistant 展示的二维码。Home Assistant 会持续轮询，直到 APP 授权返回 token 或 5 分钟二维码过期。
4. 选择 API 返回的家庭。
5. 可选：在完成配置前调整设备 picker。

手动 Access Token 配置仍作为高级兜底路径保留。

### 私有部署模式

1. 选择私有部署模式。
2. 输入私有服务器地址。
3. 输入 Access Token 和家庭 ID。
4. 可选：在 options 中配置私有 WebSocket 推送 URL。

### 局域网网关模式

1. 选择局域网网关模式。
2. 已知网关地址时，输入 host、port 和 product id。
3. 后续启用 `local_gateway_control` 且未配置 host 时，runtime 会按局域网协议执行一次 UDP discovery，再建立 TCP 网关会话。

## 支持的易来 IoT 品类

下表列出易来 IoT 品类和当前 Home Assistant 投影方式。某个品类存在投影策略，不代表每个 SKU 都会在 Home Assistant 中暴露厂商 App 的全部功能。

| 易来品类 | 默认 HA 投影 | 状态 |
| --- | --- | --- |
| `light` | `light` | 稳定 |
| `contact_sensor` | `binary_sensor`，schema 声明事件时增加 event/device trigger | 稳定 |
| `human_sensor` | `binary_sensor`，schema 声明事件时增加 event/device trigger | 稳定 |
| `light_sensor` | `sensor` | 稳定 |
| `curtain` | `cover` | 稳定 |
| `temp_control` | `climate` | 稳定 |
| `relay_switch` | `switch` | 稳定 |
| `scene_panel` | `event` + device trigger | 稳定 |
| `gateway` | 设备注册表拓扑和诊断 | 稳定 |
| `knob_switch` | `event` + device trigger | 稳定 |
| `other` | 仅明确只读属性降级为传感器 | 保守支持 |

云端情景通过 `button` 实体执行易来情景接口。

物模型注册表边界和发布映射合同见 [docs/IOT_SPEC_REGISTRY.md](docs/IOT_SPEC_REGISTRY.md)。

## 选项

在集成选项中可配置：

- 轮询间隔：10-300 秒，默认 30 秒
- 调试模式：启用受保护的调试服务
- 隐藏未知能力实体：避免把不确定能力泛化成普通实体
- 设备导入过滤：可编辑保守的手动规则；云端 entry 可重新打开真实设备 picker，在配置后继续调整选中设备
- 实时更新：云端/私有部署 entry 使用显式 `live_updates` WebSocket runtime。轮询仍作为默认全量状态刷新路径
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

向 Home Assistant debug 日志写入聚合后的 WebSocket 推送健康信息，用于开发和排障。该服务需要启用 `debug_mode`。

### `yeelight_pro.debug_emit_push_payload`

向 runtime bridge 注入一条合成属性推送。该服务需要启用 `debug_mode`，不会控制真实设备。

### `yeelight_pro.refresh`

立即刷新已加载的 Yeelight Pro 数据，并执行设备/实体注册表同步。可选 `entry_id` 用于限定单个配置条目；可选 `refresh_product_schemas` 会刷新产品物模型，失败时回退已缓存 schema。

### `yeelight_pro.cleanup_registry`

执行 stale entity registry cleanup dry-run 预览。确认执行时必须提供同一个 `entry_id` 和 dry-run 返回的 `audit_id`；确认后通过 Home Assistant entity registry 禁用 stale entities。

## 运行时模型

- 区域和账号隔离基于 config entry：每个云端账号、区域和家庭组合对应一个 Home Assistant 配置条目。
- 产品 schema 完整性优先：可用时同时读取并合并 v1 和 v2 schema 响应。
- 云端事件通知使用显式 `live_updates` WebSocket runtime；私有部署 entry 使用同一 runtime，并可配置私有推送 URL。轮询仍作为默认全量状态刷新路径。
- 本地网关控制通过局域网模式 entry 暴露，并由 `local_gateway_control` 选项控制。
- 设备导入过滤结合 diagnostics 预览、手动 options 规则、setup/options 真实设备 picker 选择，以及提交新设备来源实体前的保守 gate。
- Registry 清理通过显式 dry-run 加 audit_id 二次确认服务执行，并通过 Home Assistant registry 禁用 stale entities。

## 已知边界

- 该集成不会把未支持或未知的可写能力泛化为普通 switch、select、number、text 或 button。
- 未知标量属性只有在相关选项允许时，才可能成为保守的只读 sensor。
- 设备导入过滤只作用于新的设备来源实体提交路径。
- 调试服务只有在启用 `debug_mode` 后才可用。
- 受控生产探针需要显式确认 flag；没有确认 flag 时必须保持 fail-closed。

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

## 许可证

MIT License
