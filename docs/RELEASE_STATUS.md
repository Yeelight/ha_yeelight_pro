# Yeelight Pro 发布状态

## 状态

当前状态为 `v1.0.5` GitHub release 已发布，HACS 默认仓库 PR
[#8516](https://github.com/hacs/default/pull/8516) 审查中。

## 已具备的发布前材料

- `hacs.json`
- `custom_components/yeelight_pro/manifest.json`
- `README.md`
- `README_zh.md`
- `CHANGELOG.md`
- `CONTRIBUTING.md`
- `RELEASE_GUIDE.md`
- `.github/workflows/test.yaml`
- `.github/workflows/validate.yaml`
- `.github/workflows/release.yaml`
- `.github/ISSUE_TEMPLATE/bug_report.yml`
- `.github/ISSUE_TEMPLATE/feature_request.yml`
- `.github/ISSUE_TEMPLATE/support.yml`
- `scripts/check_release_zip.py`

## 当前门禁

```bash
# Run from the repository root.
python3 -m compileall -q custom_components/yeelight_pro scripts hacs_publish.py
ruff check custom_components/yeelight_pro scripts hacs_publish.py
mypy --ignore-missing-imports --explicit-package-bases --exclude custom_components/yeelight_pro/tests custom_components/yeelight_pro scripts hacs_publish.py
pytest -q
python3 validate_hacs.py
python3 scripts/check_release_zip.py
python3 scripts/sync_local_ha_runtime.py
python3 scripts/verify_local_ha.py
python3 scripts/verify_local_ha_soak.py
python3 scripts/verify_local_ha_recovery.py
```

`python3 hacs_publish.py --check` 会按同一顺序运行本地发布门禁。GitHub Actions 还应通过 hassfest、HACS action 和 release workflow 中的完整本地发布门禁。

当前公开候选版本必须满足：

- `custom_components/yeelight_pro/manifest.json` version、Git tag 和
  `CHANGELOG.md` release section 一致。
- GitHub release 包含名为 `yeelight_pro.zip` 的 zip asset。
- HACS PR links 指向当前 release 和最新成功的 HACS/hassfest action run。

## 发布阻断条件

- 本地 Home Assistant 验证或完整发布门禁在当前候选版本上失败。
- README、CHANGELOG、manifest version 和 release zip 不一致。
- 真实 token、家庭 ID、设备 ID、MAC 地址、endpoint URL 或设备原始数据进入仓库、issue 或支持材料。
- 文档与当前代码能力不一致。
- GitHub issue 模板缺失，或 bug/support 工单没有要求脱敏 diagnostics/logs。
- feature request 没有 Yeelight 文档或脱敏样本证据，却被当作实现任务。

## 发布审查动作

1. 复跑完整本地发布门禁和本地 Home Assistant 验证。
2. 修复验证发现的问题。
3. 审查 GitHub issue templates、support workflow、CHANGELOG 和 manifest version。
4. 确认 HACS PR links 指向当前 release 和最新成功的 action run；若 PR 已存在，更新原 PR，不重复提交。
