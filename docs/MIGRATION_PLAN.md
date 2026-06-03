# 代码迁移计划：lucore_gateway → ha_yeelight_pro

## 迁移概述

**源项目**: `/Users/yeelight/Desktop/workspace/ai/lucore/services/homeassistant/custom_components/lucore_gateway`
**目标项目**: `/Users/yeelight/Desktop/workspace/ai/lucore/services/homeassistant/extensions/ha_yeelight_pro/custom_components/yeelight_pro`

## 迁移原则

1. **保持架构分层**: canonical → adapters → converter → projector → platform entities
2. **单一职责**: 每个模块职责明确，避免功能混杂
3. **DRY 消除**: 抽取重复工具函数到 utils.py
4. **适度重构**: 大文件（coordinator.py, gateway_client.py）拆分为多个子模块
5. **渐进式迁移**: 分阶段执行，每阶段验证

---

## 第一阶段：基础模型层（P0）

### 1.1 canonical/models.py (439行)

**迁移内容**:
- 14 个 dataclass: HAProductModel, ProductModel, ComponentModel, ComponentInstanceModel, HADeviceInstanceModel, DeviceInfoModel, PropertyModel, ValueRangeModel, ValueItemModel, EventModel, ActionModel, ActionParamModel, BridgeModel, InstanceCapabilitiesModel
- 工具函数: _list(), _dict()
- 所有 from_dict() 工厂方法

**修改要求**:
- [ ] 更新模块文档字符串（去除 "Lucore Gateway"）
- [ ] 保持所有 dataclass 结构不变
- [ ] 确保 slots=True 和 from_dict() 方法完整保留

**验证标准**:
- [ ] 所有 14 个 dataclass 完整迁移
- [ ] from_dict() 方法功能正确
- [ ] 无外部依赖（仅 dataclasses）

### 1.2 canonical/__init__.py (36行)

**迁移内容**:
- 所有 dataclass 的导出声明

**修改要求**:
- [ ] 更新文档字符串
- [ ] 保持所有导出不变

### 1.3 adapters/models.py (188行)

**迁移内容**:
- 14 个 Source*Input dataclass

**修改要求**:
- [ ] 更新文档字符串
- [ ] 保持所有 dataclass 结构不变

---

## 第二层：工具和常量（P0）

### 2.1 utils.py (新建)

**新建内容**:
- 抽取重复工具函数: _bool(), _int(), _float(), _string(), _category(), _matches_any()
- 来源: 从 15+ 个文件中提取

**设计要求**:
- [ ] 函数签名保持兼容
- [ ] 类型提示完整
- [ ] 文档字符串清晰

### 2.2 const.py (已存在，需验证)

**验证内容**:
- [ ] DOMAIN = "yeelight_pro" 正确
- [ ] 所有常量定义完整
- [ ] 无 lucore 引用

### 2.3 event_support.py (64行)

**迁移内容**:
- 事件归一化逻辑

**修改要求**:
- [ ] 更新文档字符串
- [ ] 去除 lucore 前缀引用

---

## 第三层：适配器层（P1）

### 3.1 adapters/product.py (386行)

**迁移内容**:
- YeelightProductSchemaAdapter 类
- ProductSchemaDtoV2 适配逻辑

**修改要求**:
- [ ] 更新文档字符串
- [ ] 调整 import 路径
- [ ] 保持适配逻辑完整

### 3.2 adapters/device.py (344行)

**迁移内容**:
- YeelightLanDeviceAdapter 类
- LAN 设备拓扑适配逻辑

**修改要求**:
- [ ] 更新文档字符串
- [ ] 调整 import 路径
- [ ] 保持适配逻辑完整

### 3.3 adapters/__init__.py (38行)

**迁移内容**:
- 适配器导出声明

---

## 第四层：转换层（P0）

### 4.1 converter/product.py (503行) ⭐ 核心资产

**迁移内容**:
- CanonicalProductBuilder 类
- RuntimeInferredProductModelBuilder 类
- RUNTIME_PROPERTY_TEMPLATES 字典（9 种设备类型属性模板）

**修改要求**:
- [ ] 更新文档字符串
- [ ] 调整 import 路径
- [ ] **完整保留 RUNTIME_PROPERTY_TEMPLATES**
- [ ] 保持 RuntimeInferredProductModelBuilder 完整

**验证标准**:
- [ ] RUNTIME_PROPERTY_TEMPLATES 覆盖所有 9 种设备类型
- [ ] RuntimeInferredProductModelBuilder 功能正确

### 4.2 converter/device.py (110行)

**迁移内容**:
- CanonicalDeviceInstanceBuilder 类

**修改要求**:
- [ ] 更新文档字符串
- [ ] 调整 import 路径

### 4.3 converter/__init__.py (10行)

**迁移内容**:
- 转换器导出声明

---

## 第五层：投影层（P0）⭐ 最高价值

### 5.1 projector/device.py (82行)

**迁移内容**:
- device_info 投影逻辑

### 5.2 projector/light.py (545行) ⭐ 核心价值

**迁移内容**:
- project_light() 函数
- 亮度/色温/RGB 转换逻辑
- 颜色模式推断

**修改要求**:
- [ ] 更新文档字符串
- [ ] 调整 import 路径
- [ ] 提取重复工具函数到 utils.py
- [ ] **完整保留所有投影逻辑**

### 5.3 projector/fan.py (628行) ⭐ 核心价值

**迁移内容**:
- project_fans() 函数
- 速度百分比、预设模式、方向逻辑

**修改要求**:
- [ ] 更新文档字符串
- [ ] 调整 import 路径
- [ ] 提取重复工具函数到 utils.py
- [ ] **完整保留所有投影逻辑**

### 5.4 projector/switch.py (313行)

**迁移内容**:
- project_switches() 函数
- 索引开关、多通道逻辑

### 5.5 projector/sensor.py (156行)

**迁移内容**:
- project_sensors() 函数
- 温度/湿度/照度/光感投影

### 5.6 projector/binary_sensor.py (214行)

**迁移内容**:
- project_binary_sensors() 函数
- 移动/门窗/防拆投影

### 5.7 projector/cover.py (155行)

**迁移内容**:
- project_cover() 函数
- 位置/开关状态投影

### 5.8 projector/climate.py (126行)

**迁移内容**:
- project_climate() 函数
- 温度/HVAC 模式投影

### 5.9 projector/lock.py (126行)

**迁移内容**:
- project_lock() 函数
- 锁定状态/控制投影

### 5.10 projector/event.py (261行)

**迁移内容**:
- project_events() 函数
- 事件类型/设备触发器投影

### 5.11 projector/__init__.py (36行)

**迁移内容**:
- 投影函数导出声明

---

## 第六层：协调器和客户端（P1）⚠️ 需重构

### 6.1 coordinator.py (826行) → 拆分为 4 个文件

**拆分方案**:
- `coordinator/data_coordinator.py` - 数据刷新逻辑
- `coordinator/event_dispatcher.py` - SSE 事件分发
- `coordinator/product_model_cache.py` - 产品模型缓存
- `coordinator/state_manager.py` - 运行时状态管理

**迁移要求**:
- [ ] 按职责拆分
- [ ] 保持公共接口兼容
- [ ] 更新文档字符串
- [ ] 调整 import 路径

### 6.2 gateway_client.py (1605行) → 拆分为 5 个文件

**拆分方案**:
- `client/http_client.py` - HTTP 请求基础设施
- `client/proxy_backend.py` - proxy 后端
- `client/public_test_backend.py` - public_test 后端
- `client/sse_consumer.py` - SSE 流消费
- `client/device_type_mapper.py` - 设备类型推断逻辑

**迁移要求**:
- [ ] 按职责拆分
- [ ] 保持公共接口兼容
- [ ] 更新文档字符串
- [ ] 调整 import 路径

### 6.3 source_snapshot.py (535行)

**迁移内容**:
- HA northbound 快照适配逻辑

**修改要求**:
- [ ] 更新文档字符串
- [ ] 调整 import 路径

### 6.4 entity_lifecycle.py (106行)

**迁移内容**:
- 实体生命周期管理

---

## 第七层：HA 平台实体（P0）

### 7.1 __init__.py (439行)

**迁移内容**:
- 集成入口、服务注册、设备同步

**修改要求**:
- [ ] DOMAIN 改为 "yeelight_pro"
- [ ] 去除 lucore 前缀
- [ ] 服务 schema 调整

### 7.2 config_flow.py (140行)

**迁移内容**:
- UI 配置流程

**修改要求**:
- [ ] DOMAIN 改为 "yeelight_pro"
- [ ] 配置字段调整

### 7.3 platform entities (10 个文件)

**迁移内容**:
- light.py (244行)
- fan.py (313行)
- switch.py (142行)
- sensor.py (140行)
- binary_sensor.py (135行)
- cover.py (153行)
- climate.py (150行)
- lock.py (117行)
- event.py (163行)
- device_trigger.py (145行)

**修改要求**:
- [ ] 更新所有 import 路径
- [ ] DOMAIN 改为 "yeelight_pro"
- [ ] 保持投影委托模式

---

## 第八层：配置和资源（P0）

### 8.1 manifest.json

**修改要求**:
- [ ] domain: "yeelight_pro"
- [ ] name: "Yeelight Pro"

### 8.2 strings.json

**修改要求**:
- [ ] 全面更新，去除 lucore 引用

### 8.3 translations/*.json

**修改要求**:
- [ ] 全面更新，去除 lucore 引用

### 8.4 services.yaml

**修改要求**:
- [ ] domain 引用更新为 yeelight_pro

---

## 第九层：测试（P1）

### 9.1 测试文件迁移

**迁移内容**:
- test_fan_projection.py
- test_projection_baselines.py
- test_proxy_snapshot_mode.py
- test_cloud_projection_snapshot.py
- test_event_automation.py
- test_debug_event_service.py

**修改要求**:
- [ ] 更新所有 import 路径
- [ ] 更新 fixtures 中的 lucore_gateway 引用

---

## 迁移检查清单

### 每个文件迁移后必须验证：

- [ ] 文档字符串更新（去除 "Lucore Gateway"）
- [ ] import 路径正确
- [ ] 无残留 lucore 引用
- [ ] 类型提示完整
- [ ] 函数/类签名保持兼容

### 每个模块迁移后必须验证：

- [ ] 单元测试通过
- [ ] 无循环依赖
- [ ] 符合单一职责原则
- [ ] 文件行数合理（<400行）

### 整体迁移完成后必须验证：

- [ ] hassfest 验证通过
- [ ] HACS 结构正确
- [ ] 所有测试通过（目标 >80% 覆盖率）
- [ ] 文档完整

---

## 风险和注意事项

### 高风险点：

1. **RUNTIME_PROPERTY_TEMPLATES** (converter/product.py)
   - 这是核心业务知识，必须完整保留
   - 包含 9 种设备类型的属性模板

2. **投影层** (projector/*.py)
   - 最有价值的业务逻辑
   - 必须完整保留所有投影函数

3. **大文件拆分** (coordinator.py, gateway_client.py)
   - 需要仔细设计接口
   - 保持向后兼容

### 注意事项：

1. **不要过度重构**: 迁移时只做必要的调整，不要改变业务逻辑
2. **保持渐进式**: 每完成一个模块就验证，不要一次性迁移所有代码
3. **记录问题**: 遇到问题及时记录，不要强行迁移
4. **测试优先**: 迁移后立即编写/更新测试

---

## 工作流使用

### 使用 trellis-implement 执行迁移：

```
/trellis-implement 迁移 canonical/models.py 到 ha_yeelight_pro
```

### 使用 trellis-check 验证质量：

```
/trellis-check 检查迁移后的代码质量
```

### 使用 trellis-research 查找依赖：

```
/trellis-research 查找 canonical/models.py 的所有依赖
```

---

## 迁移时间估算

| 阶段 | 内容 | 预计时间 |
|------|------|---------|
| 第一阶段 | canonical + adapters + converter + projector | 2-3 天 |
| 第二阶段 | coordinator + client 拆分重构 | 3-4 天 |
| 第三阶段 | platform entities + config_flow | 1 天 |
| 第四层 | 配置、资源、测试 | 1 天 |
| **总计** | | **7-9 天** |

---

## 里程碑

- [ ] **M1**: canonical + projector 迁移完成
- [ ] **M2**: adapters + converter 迁移完成
- [ ] **M3**: coordinator + client 拆分完成
- [ ] **M4**: platform entities 迁移完成
- [ ] **M5**: 测试覆盖 >80%
- [ ] **M6**: hassfest 验证通过
- [ ] **M7**: HACS 发布就绪
