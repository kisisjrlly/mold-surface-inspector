# Bug修复日志

## 2026-01-22 修复记录

### 问题1: 点动按钮无响应 ❌ → ✅

**症状**: 
- 前端点击点动按钮，设备不移动
- 日志显示写入成功，但位置没有变化

**根本原因**:
1. `electron_ws_server.py` 使用了错误的参数名 `slave=1`，应该是 `device_id=1`
2. `modbus_sim_server.py` 的模拟器**没有实现点动逻辑**，只处理了动作信号

**修复内容**:

#### 修复1: electron_ws_server.py
```python
# 修复前
self.plc_driver.client.write_coil(address, value, slave=1)
self.plc_driver.client.write_registers(address, [high, low], slave=1)

# 修复后
self.plc_driver.client.write_coil(address, value, device_id=1)
self.plc_driver.client.write_registers(address, [low, high], device_id=1)
```

#### 修复2: modbus_sim_server.py - 添加点动处理逻辑
```python
def _update_axis(self, axis_id):
    # 新增点动信号检查
    is_jog_fwd = store.getValues(1, addr['jog_fwd'], count=1)[0]
    is_jog_bwd = store.getValues(1, addr['jog_bwd'], count=1)[0]
    
    if is_jog_fwd or is_jog_bwd:
        # 读取点动速度
        jog_speed = ...  # 从寄存器读取
        
        # 点动运动
        step = jog_speed if is_jog_fwd else -jog_speed
        new_val = current + step
        
        # 限位保护
        new_val = max(addr['min'], min(addr['max'], new_val))
        
        self._set_position(axis_id, new_val)
        store.setValues(1, addr['moving'], [True])
        return
```

**测试方法**:
1. 启动系统
2. 点击点动前进/后退按钮
3. 观察3D模型中探头是否移动
4. 检查位置显示是否更新

---

### 问题2: 整机初始化不完整 ❌ → ✅

**症状**:
- 点击整机初始化按钮没有反应
- 初始化状态标志不更新

**根本原因**:
- `modbus_sim_server.py` 没有处理整机初始化信号（地址104）
- 没有更新初始化中/完成状态标志

**修复内容**:

#### 添加整机初始化处理
```python
def _check_system_init(self):
    """检查整机初始化信号"""
    store = self.context[self.slave_id]
    is_system_init = store.getValues(1, 104, count=1)[0]
    
    if is_system_init:
        # 触发所有轴的初始化
        store.setValues(1, 1002, [True])  # 1#X轴初始化
        store.setValues(1, 1102, [True])  # 2#X轴初始化
        store.setValues(1, 1202, [True])  # 旋转轴初始化
        
        # 设置初始化中标志
        store.setValues(1, 700, [True])   # 系统初始化中
        
        # 复位整机初始化信号
        store.setValues(1, 104, [False])
```

#### 完善单轴初始化状态更新
```python
# 初始化完成后更新状态标志
store.setValues(1, init_status_map[axis_id]['ing'], [False])  # 清除"初始化中"
store.setValues(1, init_status_map[axis_id]['done'], [True])  # 置位"初始化完成"

# 检查所有轴是否都完成
all_done = all(store.getValues(1, init_status_map[i]['done'], count=1)[0] for i in [1, 2, 3])
if all_done:
    store.setValues(1, 700, [False])  # 清除"系统初始化中"
    store.setValues(1, 701, [True])   # 置位"系统初始化完成"
```

**测试方法**:
1. 点击"整机初始化"按钮
2. 观察所有轴是否移动到原点
3. 检查初始化状态指示灯

---

### 问题3: 字节序错误 ❌ → ✅

**症状**:
- 写入寄存器值不正确

**根本原因**:
- `electron_ws_server.py` 使用 Big Endian `[high, low]`
- `hardware_driver.py` 使用 Little Endian `[low, high]`
- 不一致导致数据错误

**修复内容**:
```python
# 统一使用 Little Endian
low = value & 0xFFFF
high = (value >> 16) & 0xFFFF
success = self.plc_driver.client.write_registers(address, [low, high], device_id=1)
```

---

### 问题4: 探头有效标志已废弃 ❌ → ✅

**症状**:
- 代码中仍然读取730/731地址
- 新协议中已移除这些地址

**修复内容**:
- `hardware_driver.py`: 移除 `probe1_valid`, `probe2_valid` 字段
- `electron_ws_server.py`: 移除数据有效性检查
- `modbus_sim_server.py`: 移除730/731的初始化设置

---

## 完整修复文件列表

| 文件 | 修复内容 | 状态 |
|------|---------|------|
| electron_ws_server.py | 修正参数名、字节序 | ✅ |
| modbus_sim_server.py | 添加点动/初始化逻辑 | ✅ |
| hardware_driver.py | 移除废弃字段 | ✅ |
| test_system.py | 更新测试输出 | ✅ |
| docs/PLC_PROTOCOL.md | 更新协议说明 | ✅ |

---

## 测试清单

### 基础连接测试
- [ ] 启动 Modbus 模拟器
- [ ] 启动 Electron 应用
- [ ] 成功连接 PLC（127.0.0.1:502）
- [ ] WebSocket 连接成功
- [ ] 状态指示灯变绿

### 手动操作测试

#### 点动控制
- [ ] 1#X轴前进按钮按住时移动，松开后停止
- [ ] 1#X轴后退按钮按住时移动，松开后停止
- [ ] 2#X轴前进按钮按住时移动，松开后停止
- [ ] 2#X轴后退按钮按住时移动，松开后停止
- [ ] 旋转轴正转按钮按住时移动，松开后停止
- [ ] 旋转轴反转按钮按住时移动，松开后停止
- [ ] 点动速度调整生效
- [ ] 3D模型同步更新
- [ ] 位置显示实时更新
- [ ] 限位保护生效（不能超出行程范围）

#### 定位动作
- [ ] 1#X轴输入目标位置后点击"定位"，自动移动到目标位置
- [ ] 2#X轴输入目标位置后点击"定位"，自动移动到目标位置
- [ ] 旋转轴输入目标角度后点击"定位"，自动旋转到目标角度
- [ ] 到达目标位置后自动停止
- [ ] 动作速度生效

#### 回原点
- [ ] 1#X轴回原点 → -700mm
- [ ] 2#X轴回原点 → +700mm
- [ ] 旋转轴回原点 → 0°
- [ ] 初始化完成标志置位

#### 整机初始化
- [ ] 点击"整机初始化"按钮
- [ ] 所有轴同时移动到原点
- [ ] "系统初始化中"标志置位
- [ ] 所有轴到达原点后，"系统初始化完成"标志置位
- [ ] "系统初始化中"标志清除

### 自动扫描测试
- [ ] 设置扫描参数（X步进、最大角度、角度步进）
- [ ] 点击"启动"按钮
- [ ] 扫描流程正常（APPROACH → SCAN → STEP）
- [ ] 点云数据正常采集
- [ ] 3D点云实时显示
- [ ] 误差统计更新
- [ ] 数据表格显示测量数据

### 理论点云测试
- [ ] 加载理论点云文件
- [ ] 理论点云显示（浅蓝色）
- [ ] 误差计算正确
- [ ] 颜色映射正确（绿色≤0.05mm，橙色0.05-0.10mm，红色>0.10mm）

---

## 已知限制

1. **点动速度单位**: 前端显示为 mm/s，但实际是每100ms的移动量
2. **3D模型更新频率**: 受限于WebSocket广播频率（目前100ms一次）
3. **仿真精度**: 模拟器使用0.01mm精度，可能与真实PLC有差异

---

## 下一步优化建议

1. **性能优化**: 减少不必要的Modbus写入操作
2. **错误处理**: 添加更详细的错误提示
3. **日志优化**: 使用结构化日志，方便调试
4. **UI优化**: 添加加载动画，提升用户体验
5. **数据导出**: 支持导出测量数据为CSV/Excel
