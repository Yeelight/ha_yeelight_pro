# Goal Completion Audit

更新时间：2026-06-21

本文按用户目标记录 `ha_yeelight_pro` 当前实现和验证入口。当前公开候选版本为 `v1.0.4` GitHub release，HACS 默认仓库 PR
[#8516](https://github.com/hacs/default/pull/8516) 审查中；发布审查以当前命令输出和本地 HA 安装态为准。

## 审计结论

| 目标项 | 当前实现 | 当前证据 |
| --- | --- | --- |
| 易来能力边界 | 运行时能力对齐易来接口、WebSocket、局域网协议和 Home Assistant runtime 的可验证支撑范围 | `capabilities/`、`projector/`、`options_flow.py`、`diagnostics.py`、`scripts/` |
| APP 扫码登录 | 云端主路径为易来 APP 扫码登录；二维码内容为 `cli&{device}&{qrcodeId}`，二维码有效期 5 分钟，表单含倒计时和刷新入口 | `config_flow_scan_login.py`、`scan_login_contract.py`、`core/scan_login.py`、`tests/test_config_flow_scan_login.py`、`tests/test_scan_login_runtime.py` |
| 多区域 | CN/SG/US/DE 区域映射到对应 API 域名 | `const.py`、`scan_login_contract.py`、`config_flow_helpers.py`、`tests/test_scan_login_contract.py`、`tests/test_config_flow_cloud.py` |
| 多账号 | 一个账号/家庭一个 config entry；entry unique id 包含 region、account key 和 house；手动 token fallback 使用脱敏 token 指纹 | `config_flow_account.py`、`config_flow.py`、`config_flow_reauth.py`、`entry_title.py` |
| WebSocket 事件通知 | 事件通知使用显式 `live_updates` WebSocket runtime；`prop` / `event` payload 进入同一 runtime bridge | `live_runtime.py -> YeelightPushWebSocketTransport -> push_transport.py ws_connect -> subscribe/heartbeat -> prop/event -> coordinator_runtime.py async_handle_push_payload` |
| LAN 控制 | 显式 `local_gateway_control` LAN runtime 和 LAN-first 控制路由已落地；host 为空时只在启用后执行一次 hostless one-shot UDP fallback | `lan_contract.py`、`lan_discovery.py`、`lan_runtime.py`、`core/lan_control.py`、`tests/test_lan_runtime.py` |
| 真实设备 picker A | setup 和 options 均支持真实设备 picker；只持久化 selected device ids，列表加载失败时 setup 可继续、options 不覆盖现有 filter | `config_flow_device_picker.py`、`config_flow.py`、`options_flow.py`、`tests/test_config_flow_device_picker.py`、`tests/test_options_flow_device_picker.py` |
| cleanup B | `cleanup_registry` 是显式 admin service，采用 dry-run + audit_id confirm，只禁用 stale entities | `registry_cleanup_service.py`、`entity_lifecycle_cleanup.py`、`services.yaml`、`tests/test_registry_cleanup_service.py` |
| 数据分析诊断传感器 | 房屋级 analytics 诊断传感器暴露报警、能耗、用户操作和端点健康聚合；可选端点失败时降级为 unavailable 诊断值，不阻断 setup | `analytics_sensor.py`、`core/analytics_coordinator.py`、`core/client_data_analytics.py`、`tests/test_analytics_sensor.py`、`tests/test_analytics_coordinator.py` |
| 本地 HA 实测 | 安装态 verifier 校验运行时文件、服务、i18n、diagnostics、WebSocket runtime、日志、HA URL 和跨轮稳定性 | `scripts/verify_local_ha.py`、`scripts/local_ha_verification/`、`hacs_publish.py --check` |

## 当前验证命令

发布审查至少运行：

```bash
# Run from the repository root.
python3 hacs_publish.py --check
python3 scripts/sync_local_ha_runtime.py
python3 scripts/verify_local_ha.py
python3 scripts/verify_local_ha_soak.py
python3 scripts/verify_local_ha_recovery.py
```

受控生产探针默认保持 fail-closed，无确认参数时返回 `missing_confirm_flag` 且 `network_attempted=false`：

```bash
python3 scripts/verify_push_websocket.py
python3 scripts/verify_scan_login.py
python3 scripts/verify_cloud_devices.py
python3 scripts/verify_lan_gateway.py
```

授权运行时必须使用显式确认 flag 和环境变量传入上下文：

- `--confirm-production-websocket` + `YEELIGHT_PRO_PUSH_TOKEN`
- `--confirm-production-scan-login` + `YEELIGHT_PRO_SCAN_LOGIN_DEVICE`
- `--confirm-production-cloud-devices` + `YEELIGHT_PRO_CLOUD_ACCESS_TOKEN`、`YEELIGHT_PRO_CLOUD_HOUSE_ID`
- `--confirm-production-lan-gateway` + `YEELIGHT_PRO_LAN_GATEWAY_HOST`

探针输出仅包含脱敏聚合结果，例如帧数、字段形态、设备数量、category 聚合、method 聚合和异常类型；不输出 token、URL、house id、client id、host、port、设备 id/name、房间、MAC 或原始 payload。
