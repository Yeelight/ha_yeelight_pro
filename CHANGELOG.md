# Changelog

All notable changes to the Yeelight Pro integration will be documented in this file.

## [1.0.0] - 2026-06-03

### 🎉 Initial Release

首个正式版本发布，从 lucore_gateway 完整迁移到 ha_yeelight_pro。

### ✨ New Features

#### 核心架构

- **统一客户端**: 支持 Yeelight Pro 云端和私有部署两种模式
- **协调器模式**: 使用 DataUpdateCoordinator 管理设备状态
- **投影模式**: canonical → adapters → converter → projector → entity 分层架构
- **DRY 原则**: 统一的工具函数库 (utils.py)

#### 支持的平台 (15 个)

- **light** - 灯光控制（亮度/色温/RGB）
- **fan** - 风扇控制（速度/方向/预设模式）
- **switch** - 开关控制
- **sensor** - 传感器（温度/湿度/照度）
- **binary_sensor** - 二值传感器（移动/门窗）
- **cover** - 窗帘控制（位置/开关）
- **climate** - 空调控制（温度/HVAC 模式）
- **lock** - 门锁控制
- **event** - 事件和设备触发器
- **scene** - 场景执行
- **button** - 按钮（自动化触发/场景执行）
- **select** - 选择器（房间/灯组/场景）
- **number** - 数值控制（灯组亮度/色温）
- **vacuum** - 扫地机器人
- **text** - 文本显示（设备名称/标签）

#### API 接口

- **设备管理**: get_devices, get_gateways, get_product_schemas
- **家庭管理**: get_houses, get_rooms, get_areas
- **灯组管理**: get_groups, control_group
- **场景管理**: get_scenes, execute_scene
- **自动化管理**: get_automations, enable/disable/trigger_automation
- **设备控制**: control_device, toggle_device

#### 配置流程

- **多步配置**: 云端/私有部署模式选择
- **云端认证**: Access Token 验证
- **家庭选择**: 自动获取家庭列表
- **私有部署**: 域名和 Token 配置

#### 服务

- **assign_areas**: 批量分配区域
- **auto_assign_areas**: 自动分配区域（基于设备名称）
- **debug_emit_event**: 调试事件发射

### 🏗️ Architecture

#### 分层设计

```text
canonical/          - 规范模型层 (14 个 dataclass)
adapters/           - 适配器层 (2 个适配器)
converter/          - 转换层 (RUNTIME_PROPERTY_TEMPLATES)
projector/          - 投影层 (9 个投影模块)
core/               - 核心层 (client, coordinator)
platform entities   - 平台实体层 (15 个平台)
```

#### 核心资产

- **RUNTIME_PROPERTY_TEMPLATES**: 8 种设备类型的属性模板
- **投影函数**: 灯光颜色转换、风扇速度计算、设备状态映射
- **适配器**: ProductSchemaDtoV2 和 LAN 设备拓扑适配

### 📊 Statistics

- **总文件数**: 50 个 Python 文件
- **总代码行数**: 9,753 行
- **核心 dataclass**: 27 个
- **投影函数**: 9 个
- **平台实体**: 15 个
- **测试用例**: 69 个 (100% 通过)
- **代码覆盖率**: 30%

### 🧪 Testing

- **单元测试**: 69 个测试用例全部通过
- **测试覆盖**: canonical, utils, config_flow, projector
- **测试框架**: pytest + pytest-asyncio + pytest-cov

### 📝 Documentation

- **README.md**: 英文文档（完整）
- **README_zh.md**: 中文文档（完整）
- **API 文档**: 客户端方法文档
- **架构文档**: 分层设计说明

### 🔧 Dependencies

- **Home Assistant**: >= 2024.1.0
- **Python**: >= 3.11
- **无额外依赖**: 使用 HA 内置库

### 🎯 Key Improvements (相比 lucore_gateway)

1. **架构优化**
   - ✅ 文件大小合理 (<400行)
   - ✅ DRY 原则执行到位
   - ✅ 命名规范化 (Yeelight Pro)

2. **功能增强**
   - ✅ 新增 6 个平台 (scene, button, select, number, vacuum, text)
   - ✅ 新增房间/灯组/自动化管理
   - ✅ 统一的 API 客户端

3. **代码质量**
   - ✅ 完整的类型提示
   - ✅ 中文文档字符串
   - ✅ 统一的错误处理

4. **测试覆盖**
   - ✅ 核心模块测试
   - ✅ 配置流程测试
   - ✅ 投影层测试

### 🚀 Future Plans

- [ ] 提高测试覆盖率到 80%
- [ ] 添加更多设备类型支持
- [ ] 优化 SSE 实时更新
- [ ] 添加设备诊断功能
- [ ] 支持更多自动化触发器

---

## [0.1.0] - 2026-06-03 (Development)

### Added

- 初始项目结构
- 从 lucore_gateway 迁移核心代码
- 基础测试框架

### Changed

- 域名从 lucore_gateway 改为 yeelight_pro
- 架构从单体改为分层设计

### Fixed

- 无

---

For more details, see the [README](README.md) and [documentation](docs/).
