# Troubleshooting

更新时间：2026-06-29

## 基本原则

- 先确认 Home Assistant 实际加载的是当前 custom integration 安装路径。
- 排障材料不得包含 token、refresh token、house id、device id/name、room、MAC、host、port、私有 endpoint 或原始 payload。
- 生产探针只能在授权环境和显式确认参数下运行。

## 常见问题

| 问题 | 可能原因 | 建议处理 |
| --- | --- | --- |
| 找不到 Yeelight Pro 集成 | HACS 未安装、自定义仓库未添加、HA 未重启 | 确认 `custom_components/yeelight_pro` 已安装并重启 HA |
| HACS 默认仓库搜索不到 | HACS PR 仍在审核中 | PR 合并前使用 custom repository 安装 |
| 扫码登录失败 | 区域选择错误、二维码过期、APP 版本过旧、网络失败 | 选择正确区域，使用 Yeelight APP 1.5.0 或更高版本重新扫码 |
| Token 失效 | 云端 token 过期或被撤销 | 走 Home Assistant reauth 流程 |
| 设备列表为空 | 家庭选择错误、账号无设备、云端接口暂时失败 | 重新确认账号和家庭；设备 picker 失败时可先跳过过滤 |
| 实体数量少于预期 | 未知能力隐藏、设备导入过滤、产品 schema 缺失 | 查看 diagnostics 的 aggregate preview，不要导出原始 payload |
| 实体不可用 | 设备离线、轮询失败、LAN gateway 连接失败 | 先确认设备在 Yeelight APP 和局域网内可达 |
| LAN gateway 连接失败 | host/port 错误、未启用 `local_gateway_control`、网关不在同一网络 | 在 LAN entry 选项中确认本地网关控制、host 和 port |
| 实时事件不更新 | `live_updates` 未启用或 WebSocket 不可达 | 确认该 entry 的选项；轮询仍是默认全量刷新路径 |
| 拓扑变化提示 | 设备新增、移除或元数据变化 | 查看 Repairs 聚合提示，必要时运行只读 refresh |
| stale entity 残留 | 设备曾经存在但后来移除 | 使用 `yeelight_pro.cleanup_registry` 先 dry-run，再用 audit_id 确认禁用 |

## 推荐排障顺序

1. 查看 Home Assistant 集成条目的连接模式和选项。
2. 检查 `scan_interval`、`live_updates`、`local_gateway_control`、device import filter。
3. 运行只读刷新服务 `yeelight_pro.refresh`。
4. 下载 Home Assistant diagnostics，并确认只包含脱敏聚合信息。
5. 本地开发环境运行：

```bash
python3 validate_hacs.py
python3 scripts/verify_local_ha.py
```

6. 授权环境才运行生产探针：

```bash
python3 scripts/verify_scan_login.py
python3 scripts/verify_cloud_devices.py
python3 scripts/verify_lan_gateway.py
python3 scripts/verify_push_websocket.py
```

## 安装路径排查

如果 Home Assistant 中看不到 Yeelight Pro，或日志显示加载的版本不是预期版本，优先确认实际安装路径。

排查时应确认：

- 是否存在 `custom_components/yeelight_pro`。
- 该目录是否由 HACS 或 `scripts/sync_local_ha_runtime.py` 安装。
- `custom_components/yeelight_pro/manifest.json` 中的 `version` 是否为预期版本。
- HACS 自定义仓库 URL 是否为 `https://github.com/Yeelight/ha_yeelight_pro`，类型是否为 `Integration`。
- 安装或更新后是否已经重启 Home Assistant。

## 提交 issue 前

请提供：

- Home Assistant 版本。
- `ha_yeelight_pro` 版本。
- 安装方式：HACS custom repository、HACS default 或手动安装。
- 连接模式：cloud、private、LAN。
- 只包含脱敏聚合信息的 diagnostics。
- 重现步骤和预期结果。

请不要提供：

- token、refresh token、authorization header。
- house id、device id、device name、room name。
- MAC、IP、host、port。
- 私有 endpoint 或完整 URL。
- 原始设备 payload。
