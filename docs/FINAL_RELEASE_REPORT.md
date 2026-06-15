# Yeelight Pro 发布报告状态

> 本文件记录当前发布审查事实。发布判断以本文件、README、CHANGELOG、manifest、release zip 和本地 HA 验证输出一致为准。

## 当前结论

- 当前阶段：发布审查。
- HACS 状态：仓库包含 HACS 元数据和本地 preflight。
- 官方社区状态：按正式发布流程提交。
- 更新模型：默认拓扑刷新和全量状态兜底使用轮询；`live_updates` 显式启用后，云端事件通知按 WebSocket runtime 实现。
- Registry cleanup：提供 dry-run + audit-id 二次确认服务；确认后只禁用 stale entities。
- 设备 picker：云端配置流选择家庭后会只读加载真实设备列表，并把勾选结果保存为导入过滤规则；云端 entry 的 options 可再次打开真实设备 picker 调整设备选择。设备列表加载失败时，setup 仍可继续创建 entry，options 不覆盖现有过滤规则。
- 多账号：当前支持“一个云端账号/家庭一个 config entry”的隔离模型；手动 token fallback 使用脱敏 token 指纹避免同区域同家庭冲突。
- 当前平台：12 个 Home Assistant 平台。

## 发布前必须通过的门禁

```bash
# Run from the repository root.
python3 -m compileall -q custom_components/yeelight_pro scripts hacs_publish.py
ruff check custom_components/yeelight_pro scripts hacs_publish.py
mypy --ignore-missing-imports --explicit-package-bases --exclude custom_components/yeelight_pro/tests custom_components/yeelight_pro scripts hacs_publish.py
pytest -q
python3 validate_hacs.py
python3 scripts/sync_local_ha_runtime.py
python3 scripts/verify_local_ha.py
python3 scripts/check_release_zip.py
```

`python3 hacs_publish.py --check` 会运行除本地 HA verifier 之外的完整本地发布门禁。受控生产探针通过显式确认 flag 和环境变量接收授权上下文，输出仅包含脱敏聚合结果；当前云端登录主路径已确定为易来 APP 扫码登录。

## 当前事实来源

- `README.md`
- `README_zh.md`
- `CHANGELOG.md`
- `RELEASE_GUIDE.md`
- `scripts/check_release_zip.py`
