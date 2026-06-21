# 实际功能测试指南

## 测试环境要求

- Home Assistant 2024.1.0 或更高版本
- Python 3.11 或更高版本
- Yeelight Pro 设备（云端或私有部署）

## 测试步骤

### 1. 安装集成

#### 方法 A: 本地开发安装

```bash
# 1. 克隆仓库
git clone https://github.com/Yeelight/ha_yeelight_pro.git
cd ha_yeelight_pro

# 2. 同步运行时文件到 HA 配置目录
python3 scripts/sync_local_ha_runtime.py --config-dir /path/to/homeassistant/config

# 3. 重启 Home Assistant
```

#### 方法 B: HACS 安装

1. 打开 HACS
2. 在 HACS 默认仓库 PR 合并前，将 `https://github.com/Yeelight/ha_yeelight_pro` 添加为 custom repository，类别选择 Integration
3. 搜索 "Yeelight Pro"
4. 点击安装
5. 重启 Home Assistant

### 2. 配置集成

1. 打开 Home Assistant
2. 进入 设置 → 设备与服务 → 添加集成
3. 搜索 "Yeelight Pro"
4. 选择连接模式：
   - **云端模式**: 选择 "Yeelight Pro 云端"
   - **私有部署**: 选择 "私有部署（Lucore）"
   - **局域网控制**: 选择 "局域网控制"

#### 云端模式配置

1. 选择账号区域
2. 使用易来 APP 扫描 Home Assistant 展示的二维码
3. 等待 Home Assistant 轮询到授权 token
4. 选择家庭
5. 选择需要导入的真实设备
6. 完成配置

#### 私有部署配置

1. 输入私有部署服务根 URL。
2. 如 WebSocket 推送服务使用不同域名，可输入私有部署 WebSocket 推送 URL。
3. 选择认证方式，完成扫码登录或 Access Token 认证。
4. 选择家庭。
5. 选择需要导入的真实设备。
6. 完成配置。

#### 局域网控制配置

1. 选择自动发现到的 Yeelight Pro 网关，或进入手动输入。
2. 手动模式输入网关 IP、端口和网关类型。
3. 确认网关已在易来 APP 中开启局域网控制模式。
4. 完成配置。

### 3. 功能测试清单

#### 3.1 设备发现

- [ ] 自动发现所有设备
- [ ] 设备信息正确显示
- [ ] 设备状态按轮询刷新；云端/私有部署可选开启 `live_updates` 验证 WebSocket runtime。

#### 3.2 灯光控制

- [ ] 开关灯
- [ ] 调节亮度
- [ ] 调节色温
- [ ] RGB 颜色控制（如果支持）

#### 3.3 风扇控制

- [ ] 开关风扇
- [ ] 调节速度
- [ ] 切换方向
- [ ] 预设模式

#### 3.4 开关控制

- [ ] 开关操作
- [ ] 状态显示

#### 3.5 传感器

- [ ] 温度传感器
- [ ] 湿度传感器
- [ ] 照度传感器
- [ ] 状态更新

#### 3.6 窗帘控制

- [ ] 开关窗帘
- [ ] 设置位置
- [ ] 状态显示

#### 3.7 空调控制

- [ ] 开关空调
- [ ] 设置温度
- [ ] 设置模式
- [ ] 状态显示

#### 3.8 场景执行

- [ ] 执行场景
- [ ] 场景列表显示

#### 3.9 灯组控制

- [ ] 控制灯组
- [ ] 调节灯组亮度
- [ ] 调节灯组色温

#### 3.10 诊断导出

- [ ] 导出的 diagnostics JSON 包含 `spec_correction`、`spec_runtime_inventory`、`entity_candidates`、`device_import_filter_preview` 和 `entity_import_filter_preview` 聚合。
- [ ] `device_import_filter_preview` 只包含规则维度计数、忽略规则计数和候选维度去重数量，不包含原始规则值。
- [ ] filter preview 不会实际隐藏、删除或禁用实体。
- [ ] diagnostics JSON 不包含 token、house ID、device ID、MAC、私有域名、product model id、component/property/event/action 明细、原始设备 payload 或原始 filter rule。

#### 3.11 服务

- [ ] `assign_areas` 和 `auto_assign_areas` 只允许管理员调用。
- [ ] `debug_emit_event`、`debug_dump_push_health` 和 `debug_emit_push_payload` 在 `debug_mode` 关闭时拒绝执行。
- [ ] `refresh` 可刷新全部 entry 或指定 `entry_id`，可选刷新产品物模型。
- [ ] `cleanup_registry` 先 dry-run 返回 `audit_id`，confirm 时必须提供同一个 `entry_id` 和 `audit_id`，且只禁用 stale entities。

### 4. 错误处理测试

- [ ] 网络断开时的行为
- [ ] Token 过期时的处理
- [ ] 设备离线时的处理
- [ ] API 调用失败时的处理

### 5. 性能测试

- [ ] 首次加载时间
- [ ] 状态更新延迟
- [ ] 控制响应时间
- [ ] 内存使用情况

## 测试记录

### 测试环境

- Home Assistant 版本: ____________
- Python 版本: ____________
- 测试日期: ____________
- 测试人员: ____________

### 测试结果

| 测试项 | 结果 | 备注 |
|--------|------|------|
| 设备发现 | ⬜ | |
| 灯光控制 | ⬜ | |
| 风扇控制 | ⬜ | |
| 开关控制 | ⬜ | |
| 传感器 | ⬜ | |
| 窗帘控制 | ⬜ | |
| 空调控制 | ⬜ | |
| 场景执行 | ⬜ | |
| 灯组控制 | ⬜ | |
| 诊断导出 | ⬜ | |
| 错误处理 | ⬜ | |
| 性能测试 | ⬜ | |

### 发现的问题

1. ____________
2. ____________
3. ____________

### 建议改进

1. ____________
2. ____________
3. ____________

## 测试结论

- [ ] 所有测试通过
- [ ] 发现问题已修复
- [ ] 可以进入发布审查

测试完成日期: ____________
测试签名: ____________
