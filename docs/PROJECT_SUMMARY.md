# Yeelight Pro 项目摘要

> 本文件是当前事实摘要。早期项目总结中过度宣称的平台数量、发布状态和完成度已经废弃。

## 当前状态

- 当前目标：提供可审查、可测试、可发布前验证的 Yeelight Pro Home Assistant 自定义集成。
- 发布状态：发布审查阶段，仓库包含 HACS 元数据和发布包校验入口。
- 验证状态：以当前 `pytest -q`、`validate_hacs.py` 和 `scripts/check_release_zip.py` 输出为准。

## 已收口能力

- 云端模式和私有部署模式配置入口。
- 标准 Home Assistant 重认证错误传播。
- 设备注册表拓扑同步。
- 易来 IoT 品类到 Home Assistant 平台的投影矩阵。
- 可配置轮询间隔、调试模式、实时更新、本地网关控制和未知能力隐藏策略。
- APP 扫码登录、多区域 API 域名、显式 opt-in WebSocket runtime、本地网关 TCP runtime、setup/options 真实设备 picker 和非破坏性 registry cleanup。
- 保守 spec correction、canonical spec runtime inventory、entity candidate 聚合、非破坏性导入过滤预览和运行时新增 gate；这些能力用于稳定投影、diagnostics 和提交新设备来源实体前的导入范围控制。
- 英文和简体中文配置流文案。

## 当前平台边界

易来 IoT 品类按物模型属性和事件投影到 Home Assistant 平台；云端情景通过 `button` 执行易来情景接口。发布 zip 只包含当前运行时平台文件。

## 运行时模型

- 多区域云端入口映射 CN/SG/US/DE API 域名。
- 多账号以 config entry 隔离：一个云端账号、区域和家庭组合对应一个配置条目。
- 云端登录主路径是易来 APP 扫码登录，手动 Access Token 是高级兜底路径。
- 事件通知使用显式 `live_updates` WebSocket runtime；默认全量刷新路径仍为轮询。
- 本地网关控制使用显式 `local_gateway_control` 选项；host 为空时执行一次局域网 UDP discovery fallback 后建立 TCP 会话。
- setup 和 options 都提供真实设备 picker，选择结果保存为后续设备来源实体的导入过滤规则。
- registry cleanup 通过 dry-run + audit_id confirm 禁用 stale entities。
