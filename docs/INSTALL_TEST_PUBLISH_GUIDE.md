# Yeelight Pro 安装、测试和发布前指南

## 当前状态

当前集成已发布 `v1.0.4` GitHub release，release asset 为 `yeelight_pro.zip`。
HACS 默认仓库 PR [#8516](https://github.com/hacs/default/pull/8516) 仍在审查中。本地 Home Assistant single/repeat/soak/recovery 验证入口已具备；每个候选版本提交或更新 HACS PR 前都必须重新运行这些入口并复核脱敏输出。

## 手动安装

```bash
# Run from the repository root.
python3 scripts/sync_local_ha_runtime.py --config-dir /path/to/homeassistant/config
```

重启 Home Assistant 后，进入“设置 -> 设备与服务 -> 添加集成 -> Yeelight Pro”。

## HACS

当前仓库包含 HACS 元数据、zip release 校验脚本和 `v1.0.4` release
zip。PR 合并前，HACS 用户应把本仓库添加为 custom repository；PR 合并后可从 HACS 默认仓库搜索安装。

## 本地验证清单

- 配置流：云端模式、私有部署模式、局域网网关模式、家庭选择、错误提示。
- 选项流：轮询间隔、调试模式、实时更新、局域网网关控制、未知能力隐藏。
- 设备发现：网关、子设备、房间和设备注册表拓扑。
- 实体投影：灯、传感器、窗帘、温控、开关、场景面板等核心品类。
- 控制命令：开关、亮度、色温、窗帘位置、温控目标值等已实现控制。
- 事件：点击、长按、门磁、人感、功率告警等标准化事件。
- 诊断导出：确认存在 `spec_correction`、`spec_runtime_inventory`、`entity_candidates`、`device_import_filter_preview` 和 `entity_import_filter_preview` 聚合；确认 filter preview 只导出规则维度计数、忽略规则计数和候选维度去重数量；确认 token、house ID、device ID、MAC、私有域名、product model id、component/property/event/action 明细、raw payload 和 raw filter rule 不出现在 JSON 中。
- 设备 picker：云端配置流在选择家庭后只读加载真实设备列表，默认全选，取消勾选后保存为后续新增设备来源实体的导入过滤规则；云端 entry 的 options 也可重新打开真实设备 picker 调整选择。设备列表加载失败时，setup 可继续创建 entry 且过滤关闭，options 不覆盖现有过滤规则。
- Registry cleanup：`cleanup_registry` 默认 dry-run；confirm 必须指定 entry 和 dry-run 返回的 audit_id，执行后只禁用 stale entities。
- 异常：token 失效、网络错误、API 返回错误、设备离线。
- WebSocket runtime：云端/私有部署 entry 在 `live_updates` 显式启用后接入易来事件通知 WebSocket。
- 本地网关 runtime：局域网 entry 在 `local_gateway_control` 显式启用后接入 LAN TCP runtime，host 为空时按局域网协议执行一次 UDP discovery fallback。启用前确认 token、网关地址或发现范围，以及日志脱敏策略。

## 发布前命令

```bash
# Run from the repository root.
python3 -m compileall -q custom_components/yeelight_pro
pytest -q
python3 validate_hacs.py
python3 scripts/sync_local_ha_runtime.py
python3 scripts/verify_local_ha.py
python3 scripts/verify_local_ha.py --repeat 2 --repeat-delay 0
python3 scripts/verify_local_ha_soak.py
python3 scripts/verify_local_ha_recovery.py
python3 scripts/check_release_zip.py --write yeelight_pro.zip
```

发布包必须只包含 `custom_components/yeelight_pro/` 下的运行时文件，不包含测试、缓存、coverage 或 pyc 文件。

本地 HA 开发安装也必须使用 `scripts/sync_local_ha_runtime.py`，不要直接 `cp -R`
整个组件目录；源码树里的 `tests/` 不能进入 Home Assistant 安装态。

`scripts/verify_local_ha.py` 只读检查本地 Docker Home Assistant 安装目录、
`.storage` 聚合计数、服务定义、容器健康和日志，不打印 token、house ID、
device ID 或原始 payload。可通过脚本参数指定本地 Home Assistant 配置目录。

## 不发布条件

- 候选版本未重新通过本地 HA single/repeat/soak/recovery 验证，或脱敏输出显示 runtime drift、服务/i18n/diagnostics 漂移、日志错误或 URL 不可达。
- 存在未脱敏 token、账号密码、house ID 或原始设备数据。
- 文档与当前代码能力不一致。
- release zip 结构检查失败。
