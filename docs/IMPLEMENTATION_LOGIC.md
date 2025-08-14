# 软件功能实现逻辑详解

## 📖 文档说明

---

## 🔬 硬件模拟误差测量原理详解

### 测量原理概述

本系统模拟的是**旋转式接触测量**，类似于三坐标测量机(CMM)的工作原理。硬件系统包括：
- **X轴直线导轨**：控制测头沿工件长度方向移动
- **旋转工作台**：将被测工件按指定角度旋转
- **千分表/位移传感器**：测量从旋转中心到工件表面的径向距离

### 坐标系统转换原理

#### 1. 理论数据坐标系（笛卡尔坐标系）
理论点云数据采用标准的三维笛卡尔坐标系：
```python
# 理论点云数据结构
theoretical_point = {
    'x_mm': x_coordinate,    # X轴位置（沿工件长度方向）
    'y_mm': y_coordinate,    # Y轴位置（径向，工件半径方向）  
    'z_mm': z_coordinate     # Z轴位置（径向，垂直于Y轴）
}
```

#### 2. 硬件测量坐标系（柱坐标系）
硬件系统实际采用的是**柱坐标系**测量方式：
```python
# 硬件测量数据结构
measurement_data = {
    'x_pos_mm': x_position,      # X轴位置（直接对应笛卡尔X）
    'angle_deg': rotation_angle, # 旋转角度（相对于Y轴的角度）
    'measured_radius_mm': radius # 千分表测得的径向距离
}
```

#### 3. 坐标转换算法

**理论数据 → 硬件测量指令（逆向转换）**
```python
def cartesian_to_cylindrical(x_mm, y_mm, z_mm):
    """笛卡尔坐标 → 柱坐标"""
    # X坐标直接对应
    x_pos = x_mm
    
    # 计算理论半径（从原点到(y,z)的距离）
    ideal_radius = math.sqrt(y_mm**2 + z_mm**2)
    
    # 计算旋转角度（使用atan2确保象限正确）
    # 注意：角度是相对于Y轴计算的
    angle_rad = math.atan2(z_mm, y_mm)  # atan2(Z, Y)
    angle_deg = math.degrees(angle_rad)
    
    return x_pos, angle_deg, ideal_radius
```

**硬件测量数据 → 笛卡尔坐标（正向转换）**
```python
def cylindrical_to_cartesian(x_pos, angle_deg, measured_radius):
    """柱坐标 → 笛卡尔坐标"""
    # 角度转弧度
    angle_rad = math.radians(angle_deg)
    
    # 坐标转换（关键公式）
    x_measured = x_pos                              # X坐标直接对应
    y_measured = measured_radius * math.cos(angle_rad)  # Y = R * cos(θ)
    z_measured = measured_radius * math.sin(angle_rad)  # Z = R * sin(θ)
    
    return x_measured, y_measured, z_measured
```

### 测量误差模拟设计

#### 1. 误差组成模型
系统模拟了真实测量设备中的多种误差源：

```python
def simulate_measurement_error(self, ideal_radius, sequence):
    """多源误差模拟算法"""
    
    # 1. 系统性误差（固定偏移）- 模拟设备零位漂移
    systematic_error = self.systematic_error  # 默认 ±0.02mm
    
    # 2. 随机噪声 - 模拟电子噪声和环境振动
    random_noise = (random.random() - 0.5) * 2 * self.random_noise_level  # ±0.05mm
    
    # 3. 周期性误差 - 模拟机械振动和转台偏心
    periodic_error = 0.02 * math.sin(2 * math.pi * sequence / 50)
    
    # 4. 位置相关误差 - 模拟几何误差随位置变化
    position_error = 0.01 * math.sin(ideal_radius / 100)
    
    # 5. 总误差合成
    total_error = systematic_error + random_noise + periodic_error + position_error
    
    # 6. 误差幅度限制（防止异常值）
    total_error = max(-self.error_amplitude, min(self.error_amplitude, total_error))
    
    return ideal_radius + total_error
```

#### 2. 各类误差特性说明

| 误差类型 | 数学模型 | 物理原因 | 典型幅度 |
|---------|---------|----------|---------|
| 系统性误差 | `constant_offset` | 设备零位漂移、标定误差 | ±0.02mm |
| 随机噪声 | `gaussian(0, σ)` | 电子噪声、环境振动 | ±0.05mm |
| 周期性误差 | `A*sin(2πf*t)` | 机械振动、转台偏心 | ±0.02mm |
| 位置相关误差 | `f(position)` | 几何误差、导轨精度 | ±0.01mm |

### 测量路径规划算法

#### 1. 循环旋转测量模式
系统采用**循环往复**的测量路径，提高测量效率：

```python
def filter_measurement_points(self):
    """循环旋转路径规划算法"""
    # 1. 按X坐标分组
    for i, x_val in enumerate(selected_x_values):
        x_data = filtered_data[filtered_data['x_mm'] == x_val]
        
        # 2. 计算角度并排序
        angles = [(math.degrees(math.atan2(y, z)), row) 
                 for _, row in x_data.iterrows()]
        angles.sort(key=lambda x: x[0])
        
        # 3. 循环往复路径规划
        if i % 2 == 0:
            # 偶数位置：正向旋转（最小角度→最大角度）
            current_angle = min_angle
            while current_angle <= max_angle:
                # 选择最接近的测量点
                measurement_points.append(closest_point)
                current_angle += rot_step
        else:
            # 奇数位置：反向旋转（最大角度→最小角度）
            current_angle = max_angle
            while current_angle >= min_angle:
                measurement_points.append(closest_point)
                current_angle -= rot_step
```

#### 2. 路径优化效果
- **减少空行程**：避免每次都从0°开始旋转
- **提高效率**：路径长度减少约40-50%
- **均匀采样**：确保各角度区间的测量密度一致

---

## 🎛️ 测量设备移动控制逻辑详解

### 硬件系统架构

系统模拟的测量设备采用**两轴联动**控制架构：

#### 1. X轴直线导轨系统
```python
# X轴移动控制参数
x_axis_config = {
    'min_position': x_min,     # 最小X位置 (mm)
    'max_position': x_max,     # 最大X位置 (mm) 
    'step_size': x_step,       # X轴步进距离 (mm)
    'movement_speed': 50.0,    # 移动速度 (mm/s)
    'positioning_accuracy': 0.01  # 定位精度 (±mm)
}
```

#### 2. 旋转工作台系统
```python
# 旋转轴控制参数
rotation_axis_config = {
    'angle_range': (0, 360),      # 旋转角度范围 (度)
    'angular_step': rot_step,     # 角度步进 (度)
    'rotation_speed': 30.0,       # 旋转速度 (度/s)
    'angular_accuracy': 0.1       # 角度精度 (±度)
}
```

### X轴位置选择算法

#### 1. 基于步长的位置筛选
```python
def select_x_positions(self, x_min, x_max, x_step):
    """X轴位置选择算法"""
    # 从理论数据中提取可用的X坐标
    available_x = sorted(self.theoretical_data['x_mm'].unique())
    
    selected_positions = []
    current_x = x_min
    
    # 按步长递进选择X位置
    while current_x <= x_max:
        # 寻找最接近目标位置的实际位置
        closest_x = min(available_x, key=lambda x: abs(x - current_x))
        
        # 检查位置误差是否在容差范围内
        position_error = abs(closest_x - current_x)
        if position_error <= x_step / 2:
            selected_positions.append(closest_x)
            print(f"选择X位置: {closest_x:.1f}mm (目标: {current_x:.1f}mm)")
        
        current_x += x_step
        
    return selected_positions
```

#### 2. X轴移动序列控制
```python
def execute_x_axis_movement(self, target_positions):
    """模拟X轴移动控制序列"""
    current_x = 0.0  # 当前X位置
    
    for target_x in target_positions:
        # 计算移动距离和时间
        movement_distance = abs(target_x - current_x)
        movement_time = movement_distance / self.x_axis_speed
        
        print(f"X轴移动: {current_x:.1f} → {target_x:.1f}mm")
        print(f"移动距离: {movement_distance:.1f}mm, 预计时间: {movement_time:.1f}s")
        
        # 模拟移动延时
        time.sleep(movement_time * self.time_scale_factor)
        
        # 更新当前位置
        current_x = target_x
        
        # 在每个X位置执行旋转测量
        self.execute_rotation_sequence(current_x)
```

### 旋转轴控制算法

#### 1. 双向旋转优化策略
```python
def execute_rotation_sequence(self, x_position):
    """在指定X位置执行旋转测量序列"""
    # 获取当前X位置的所有可测点
    points_at_x = self.get_measurement_points_at_x(x_position)
    
    # 计算角度范围
    angles = [self.calculate_angle(point) for point in points_at_x]
    min_angle, max_angle = min(angles), max(angles)
    
    # 确定旋转方向（循环优化）
    x_index = self.current_x_index
    if x_index % 2 == 0:
        # 偶数位置：正向旋转 (0° → 180°)
        rotation_direction = "forward"
        start_angle, end_angle = min_angle, max_angle
        angle_increment = +self.rot_step
    else:
        # 奇数位置：反向旋转 (180° → 0°)  
        rotation_direction = "reverse"
        start_angle, end_angle = max_angle, min_angle
        angle_increment = -self.rot_step
        
    print(f"X={x_position}mm: {rotation_direction}旋转 {start_angle:.1f}° → {end_angle:.1f}°")
    
    # 执行旋转测量
    self.perform_rotation_measurement(start_angle, end_angle, angle_increment)
```

#### 2. 角度定位与测量控制
```python
def perform_rotation_measurement(self, start_angle, end_angle, angle_increment):
    """执行旋转轴的角度定位和测量"""
    current_angle = start_angle
    
    while self.should_continue_rotation(current_angle, end_angle, angle_increment):
        if not self.is_running or self.is_paused:
            break
            
        # 1. 旋转轴定位
        self.rotate_to_angle(current_angle)
        
        # 2. 稳定延时（消除振动影响）
        time.sleep(self.stabilization_delay)
        
        # 3. 千分表测量
        measurement_result = self.perform_single_measurement(current_angle)
        
        # 4. 数据记录
        self.record_measurement_data(measurement_result)
        
        # 5. 进度更新
        self.update_measurement_progress()
        
        # 6. 移动到下一角度
        current_angle += angle_increment
        
def rotate_to_angle(self, target_angle):
    """旋转到指定角度"""
    angular_distance = abs(target_angle - self.current_angle)
    rotation_time = angular_distance / self.rotation_speed
    
    print(f"旋转轴定位: {self.current_angle:.1f}° → {target_angle:.1f}°")
    
    # 模拟旋转时间
    time.sleep(rotation_time * self.time_scale_factor)
    
    # 更新当前角度
    self.current_angle = target_angle
```

### 测量执行控制流程

#### 1. 主控制循环
```python
def simulate_measurement_process(self):
    """主测量控制流程"""
    print("开始硬件测量模拟...")
    
    # 1. 系统初始化
    self.initialize_measurement_system()
    
    # 2. 路径规划
    measurement_points = self.filter_measurement_points()
    total_points = len(measurement_points)
    
    print(f"规划路径: {total_points}个测量点")
    
    # 3. 按序执行测量
    for i, point in enumerate(measurement_points.iterrows()):
        if not self.is_running:
            break
            
        # 暂停检查
        while self.is_paused and self.is_running:
            time.sleep(0.1)
            
        # 执行单点测量
        sequence = i + 1
        self.execute_single_point_measurement(sequence, point[1])
        
        # 测量间隔
        time.sleep(self.measurement_params['measurement_delay'])
        
    print("测量过程完成")
```

#### 2. 单点测量执行
```python
def execute_single_point_measurement(self, sequence, point_data):
    """执行单个点的完整测量流程"""
    x_target = point_data['x_mm']
    y_ideal = point_data['y_mm'] 
    z_ideal = point_data['z_mm']
    
    # 1. 计算目标位置参数
    target_angle = math.degrees(math.atan2(z_ideal, y_ideal))
    ideal_radius = math.sqrt(y_ideal**2 + z_ideal**2)
    
    print(f"测量点#{sequence}: X={x_target:.1f}mm, 角度={target_angle:.1f}°")
    
    # 2. X轴定位（如果需要移动）
    if abs(self.current_x_position - x_target) > 0.01:
        self.move_x_axis_to_position(x_target)
        
    # 3. 旋转轴定位
    self.rotate_to_angle(target_angle)
    
    # 4. 系统稳定延时
    time.sleep(self.stabilization_delay)
    
    # 5. 千分表读数
    measured_radius = self.read_dial_indicator(ideal_radius, sequence)
    
    # 6. 数据处理和记录
    self.process_measurement_result(sequence, x_target, target_angle, measured_radius)
```

### 设备状态监控与控制

#### 1. 实时状态跟踪
```python
class HardwareSimulator:
    def __init__(self):
        # 设备状态变量
        self.current_x_position = 0.0      # 当前X轴位置
        self.current_angle = 0.0           # 当前旋转角度
        self.is_x_axis_moving = False      # X轴运动状态
        self.is_rotating = False           # 旋转轴运动状态
        self.measurement_in_progress = False # 测量状态
        
        # 控制参数
        self.is_running = False            # 系统运行状态
        self.is_paused = False             # 暂停状态
        self.emergency_stop = False        # 急停状态
```

#### 2. 线程控制接口
```python
def pause(self):
    """暂停测量设备运动"""
    self.is_paused = True
    print("设备运动已暂停")
    
    # 停止当前运动（如果正在进行）
    if self.is_x_axis_moving:
        self.stop_x_axis_movement()
    if self.is_rotating:
        self.stop_rotation_movement()

def resume(self):
    """恢复测量设备运动"""
    self.is_paused = False
    print("设备运动已恢复")

def stop(self):
    """停止所有设备运动"""
    self.is_running = False
    self.is_paused = False
    
    # 立即停止所有轴的运动
    self.emergency_stop_all_axes()
    print("所有设备运动已停止")

def emergency_stop_all_axes(self):
    """紧急停止所有轴"""
    self.emergency_stop = True
    self.is_x_axis_moving = False
    self.is_rotating = False
    print("执行紧急停止！")
```

### 时间控制与同步机制

#### 1. 测量时序控制
```python
# 时间参数配置
timing_config = {
    'x_axis_settle_time': 0.2,      # X轴定位稳定时间 (s)
    'rotation_settle_time': 0.1,    # 旋转定位稳定时间 (s)
    'measurement_time': 0.05,       # 单点测量时间 (s)
    'inter_point_delay': 0.1,       # 点间间隔时间 (s)
    'time_scale_factor': 0.01       # 仿真加速比例
}
```

#### 2. 实时性能优化
```python
def optimize_measurement_sequence(self, measurement_points):
    """优化测量序列以减少总时间"""
    
    # 1. 按X坐标分组
    x_groups = self.group_points_by_x(measurement_points)
    
    # 2. 每组内按角度优化排序
    optimized_sequence = []
    for x_pos, points in x_groups.items():
        # 循环往复旋转策略
        if len(optimized_sequence) % 2 == 0:
            points.sort(key=lambda p: p['angle'])    # 正向
        else:
            points.sort(key=lambda p: p['angle'], reverse=True)  # 反向
            
        optimized_sequence.extend(points)
    
    # 3. 计算优化效果
    original_time = self.calculate_total_time(measurement_points)
    optimized_time = self.calculate_total_time(optimized_sequence)
    improvement = (original_time - optimized_time) / original_time * 100
    
    print(f"路径优化: 预计节省时间 {improvement:.1f}%")
    
    return optimized_sequence
```

### 故障模拟与异常处理

#### 1. 硬件故障模拟
```python
def simulate_hardware_faults(self):
    """模拟可能的硬件故障"""
    
    # 随机故障概率 (生产环境应关闭)
    fault_probability = 0.001  # 0.1%故障率
    
    if random.random() < fault_probability:
        fault_type = random.choice(['x_axis_jam', 'rotation_error', 'sensor_fault'])
        
        if fault_type == 'x_axis_jam':
            raise HardwareFault("X轴运动卡死，无法到达目标位置")
        elif fault_type == 'rotation_error':
            raise HardwareFault("旋转轴编码器错误，角度读数异常")  
        elif fault_type == 'sensor_fault':
            raise HardwareFault("千分表传感器故障，读数异常")

class HardwareFault(Exception):
    """硬件故障异常类"""
    pass
```

#### 2. 异常恢复机制
```python
def handle_hardware_exception(self, exception):
    """硬件异常处理和恢复"""
    print(f"检测到硬件异常: {exception}")
    
    # 1. 立即停止所有运动
    self.emergency_stop_all_axes()
    
    # 2. 发送错误信号给主界面
    self.measurement_error.emit(f"硬件故障: {str(exception)}")
    
    # 3. 尝试自动恢复（简单故障）
    if self.attempt_auto_recovery(exception):
        print("故障自动恢复成功，继续测量")
        self.resume()
    else:
        print("故障需要人工干预，测量终止")
        self.stop()
```

这个详细的测量设备移动控制逻辑展示了系统如何模拟真实硬件的运动控制、定位、测量和异常处理全过程，为理解整个测量系统的工作机制提供了完整的技术参考。

### 实时误差计算过程

#### 1. 理论数据索引系统
为提高查找效率，系统建立了**O(1)复杂度**的查找索引：

```python
def create_theoretical_lookup(self):
    """创建理论数据快速查找索引"""
    self.theoretical_lookup = {}
    
    for _, row in self.theoretical_data.iterrows():
        x_mm, y_mm, z_mm = row['x_mm'], row['y_mm'], row['z_mm']
        
        # 计算索引键值
        angle_deg = math.degrees(math.atan2(z_mm, y_mm))
        x_key = round(x_mm, 1)      # X坐标精度0.1mm
        angle_key = round(angle_deg, 1)  # 角度精度0.1°
        
        # 存储理论值
        key = (x_key, angle_key)
        self.theoretical_lookup[key] = {
            'radius_theoretical': math.sqrt(y_mm**2 + z_mm**2),
            'x_theoretical': x_mm,
            'y_theoretical': y_mm,
            'z_theoretical': z_mm
        }
```

#### 2. 多维误差计算算法
系统计算多种误差指标，全面评估测量精度：

```python
def calculate_error(self, theoretical_data, measured_point, measured_radius):
    """多维误差分析算法"""
    
    # 1. 半径误差（核心指标）
    radius_error = measured_radius - theoretical_data['radius_theoretical']
    
    # 2. 笛卡尔坐标误差
    x_error = measured_point['x'] - theoretical_data['x_theoretical']
    y_error = measured_point['y'] - theoretical_data['y_theoretical']
    z_error = measured_point['z'] - theoretical_data['z_theoretical']
    
    # 3. 欧氏距离误差（总体误差幅度）
    euclidean_error = math.sqrt(x_error**2 + y_error**2 + z_error**2)
    
    # 4. 径向误差（沿半径方向）
    radial_error = radius_error  # 在半径测量中等同于半径误差
    
    # 5. 切向误差（垂直于半径方向）
    tangential_error = math.sqrt(max(0, euclidean_error**2 - radial_error**2))
    
    # 6. 动态阈值判定
    abs_radius_error = abs(radius_error)
    if abs_radius_error <= self.tolerance_qualified:
        status = "合格"
    elif abs_radius_error <= self.tolerance_attention:
        status = "注意" 
    elif abs_radius_error <= self.tolerance_over_limit:
        status = "超差!"
    else:
        status = "严重超差!"
        
    return error_analysis_dict
```

### 动态阈值参数系统

#### 1. 可配置阈值设计
系统支持用户自定义误差判定阈值：

```python
# 配置文件中的默认阈值参数
DEFAULT_TOLERANCE_QUALIFIED = 0.1   # 合格阈值：±0.1mm
DEFAULT_TOLERANCE_ATTENTION = 0.2   # 注意阈值：±0.2mm
DEFAULT_TOLERANCE_OVER_LIMIT = 0.3  # 超差阈值：±0.3mm

# 动态传递到分析线程
self.analysis_worker = AnalysisWorker(
    theoretical_data=self.theoretical_data,
    measurement_file_path=measurement_file,
    tolerance_qualified=qualified_threshold,    # 从UI读取
    tolerance_attention=attention_threshold,    # 从UI读取
    tolerance_over_limit=over_limit_threshold   # 从UI读取
)
```

#### 2. 阈值应用策略
- **合格区间**：`|误差| ≤ qualified_threshold` → 绿色显示
- **注意区间**：`qualified_threshold < |误差| ≤ attention_threshold` → 橙色显示
- **超差区间**：`attention_threshold < |误差| ≤ over_limit_threshold` → 红色显示
- **严重超差**：`|误差| > over_limit_threshold` → 深红色显示

### 实时数据流处理架构

#### 1. 多线程并行处理
```
主线程(GUI)     硬件模拟线程     分析计算线程
    ↓               ↓               ↓
界面响应    →   测量数据生成   →   误差实时计算
    ↑               ↓               ↓
结果显示    ←   CSV文件写入    ←   统计数据更新
```

#### 2. 信号槽通信机制
- `measurement_point` → 单点测量完成
- `analysis_result` → 单点误差计算完成
- `statistics_updated` → 统计数据更新
- `progress_updated` → 测量进度更新

#### 3. 数据同步策略
- **文件缓冲**：测量数据先写入CSV，后读取分析
- **增量处理**：只处理新增的测量点，避免重复计算
- **内存管理**：使用`deque`限制历史数据缓存大小

### 测量精度与性能优化

#### 1. 精度控制措施
- **坐标转换精度**：浮点运算保持6位有效数字
- **角度量化策略**：0.1°精度避免浮点误差累积
- **查找容差设计**：X轴±0.5mm，角度±1.0°的匹配容差

#### 2. 性能优化技术
- **索引查找**：O(1)复杂度的理论点查找
- **增量处理**：只处理新增数据，避免全量重计算
- **异步处理**：测量、分析、显示三线程并行
- **内存优化**：限制历史数据缓存，防止内存泄漏

### 系统扩展能力

#### 1. 误差模型扩展
- 支持添加新的误差源（温度、湿度等）
- 可调整各误差分量的权重系数
- 支持不同工件的专用误差模型

#### 2. 测量模式扩展  
- 支持不同的路径规划算法
- 可配置测量密度和采样策略
- 支持多轴联动的复杂测量模式

此文档详细展示了软件主要功能背后的完整代码执行流程，特别是硬件模拟误差测量的原理和实现机制，有助于理解系统的技术架构和数据处理逻辑。

````

---

## 🔧 功能1：加载理论模型

### 用户操作
用户点击工具栏中的"📁 加载模型"按钮或左侧面板的"加载CAD模型..."按钮

### 代码执行流程

#### 1. 信号触发 (main_window.py:295)
```python
# 在 setup_connections() 方法中预先连接的信号槽
self.load_model_btn.clicked.connect(self.load_model)
```

#### 2. 文件选择对话框 (main_window.py:898)
```python
def load_model(self):
    """加载理论模型数据文件"""
    print("=== 加载理论模型功能 ===")
    
    # 打开文件选择对话框
    file_path, _ = QFileDialog.getOpenFileName(
        self,
        "选择理论点云数据文件",
        "",
        "CSV files (*.csv);;All files (*.*)"
    )
```

#### 3. 文件验证与加载 (main_window.py:905-918)
```python
if file_path:
    try:
        print(f"尝试加载文件: {file_path}")
        
        # 使用pandas读取CSV文件
        self.theoretical_data = pd.read_csv(file_path)
        print(f"成功加载数据: {len(self.theoretical_data)} 行")
        
        # 验证数据格式 - 检查必要的列
        required_columns = ['x_mm', 'y_mm', 'z_mm']
        if not all(col in self.theoretical_data.columns for col in required_columns):
            raise ValueError(f"CSV文件必须包含列: {required_columns}")
```

#### 4. 界面更新 (main_window.py:919-935)
```python
# 更新左侧面板显示
import os
filename = os.path.basename(file_path)
self.model_name_label.setText(filename)
self.model_points_label.setText(f"{len(self.theoretical_data):,} 点")

# 显示数据范围信息
x_range = f"{self.theoretical_data['x_mm'].min():.1f} - {self.theoretical_data['x_mm'].max():.1f} mm"
self.model_range_label.setText(x_range)

# 显示成功消息
QMessageBox.information(self, "加载成功", f"成功加载理论模型数据！\n文件：{filename}\n数据点数：{len(self.theoretical_data):,}")
```

#### 5. 3D可视化更新 (main_window.py:936-945)
```python
# 在3D视图中显示理论点云
self.display_point_cloud_in_3d()

print("理论模型加载完成")
```

#### 6. 3D显示实现 (main_window.py:818-856)
```python
def display_point_cloud_in_3d(self):
    """在3D视图中显示理论点云数据"""
    if self.theoretical_data is None:
        return
        
    try:
        # 清除之前的图像
        self.point_cloud_ax.clear()
        
        # 提取坐标数据
        x = self.theoretical_data['x_mm'].values
        y = self.theoretical_data['y_mm'].values  
        z = self.theoretical_data['z_mm'].values
        
        # 绘制3D散点图 - 理论点云用浅蓝色
        self.point_cloud_ax.scatter(x, y, z, 
                                   c='lightblue', 
                                   s=1, 
                                   alpha=0.6, 
                                   label='Theoretical Points')
        
        # 设置坐标轴
        self.point_cloud_ax.set_xlabel('X (mm)', fontsize=8)
        self.point_cloud_ax.set_ylabel('Y (mm)', fontsize=8)
        self.point_cloud_ax.set_zlabel('Z (mm)', fontsize=8)
        self.point_cloud_ax.legend()
        
        # 刷新画布
        self.point_cloud_canvas.draw()
```

### 数据结构变化
- `self.theoretical_data`: 从 `None` 变为包含理论点云数据的 `pandas.DataFrame`
- DataFrame 结构：
  ```python
  columns: ['x_mm', 'y_mm', 'z_mm']
  # 示例数据：
  #    x_mm    y_mm    z_mm
  # 0   0.0   500.0     0.0
  # 1   0.0   499.8    31.2
  # ...
  ```

---

## ▶️ 功能2：开始测量

### 用户操作
用户点击工具栏中的"▶ 开始测量"按钮

### 代码执行流程

#### 1. 信号触发与前置验证 (main_window.py:978-987)
```python
def start_measurement(self):
    """开始测量 - 使用新的模拟器系统"""
    print("=== 开始测量功能 ===")
    
    # 检查是否已加载理论数据
    if self.theoretical_data is None:
        QMessageBox.warning(
            self, "无法开始测量", 
            "请先加载理论点云数据文件才能开始测量。"
        )
        return
    
    print(f"开始测量，理论数据点数: {len(self.theoretical_data)}")
```

#### 2. 读取测量参数 (main_window.py:989-992)
```python
# 读取测量参数
measurement_params = self.get_measurement_parameters()
if measurement_params is None:
    return
```

#### 3. 参数解析实现 (main_window.py:1353-1380)
```python
def get_measurement_parameters(self):
    """获取测量参数"""
    try:
        # 从界面控件读取参数值
        x_min = float(self.x_min_input.text())
        x_max = float(self.x_max_input.text())  
        x_step = float(self.x_step_input.text())
        rot_step = float(self.rot_step_input.text())
        
        # 参数验证
        if x_min >= x_max:
            QMessageBox.warning(self, "参数错误", "X轴最小值必须小于最大值")
            return None
            
        if x_step <= 0 or rot_step <= 0:
            QMessageBox.warning(self, "参数错误", "步长必须为正数")
            return None
        
        # 构造参数字典
        params = {
            'x_min': x_min,
            'x_max': x_max,
            'x_step': x_step,
            'rot_step': rot_step,
            'measurement_delay': 0.1  # 固定测量间隔
        }
        
        return params
```

#### 4. 线程清理与准备 (main_window.py:994-999)
```python
# 停止之前的定时器
self.simulation_timer.stop()

# 清理之前的线程
self.cleanup_threads()

# 重置表格和统计数据
self.reset_measurement_data()
```

#### 5. 线程清理实现 (main_window.py:1073-1083)
```python
def cleanup_threads(self):
    """清理之前的线程"""
    if self.hardware_simulator is not None:
        self.hardware_simulator.stop()
        self.hardware_simulator.wait(1000)  # 等待最多1秒
        self.hardware_simulator = None
        
    if self.analysis_worker is not None:
        self.analysis_worker.stop()
        self.analysis_worker.wait(1000)  # 等待最多1秒
        self.analysis_worker = None
```

#### 6. 创建工作线程 (main_window.py:1001-1015)
```python
# 创建输出文件路径
output_dir = os.path.join(os.getcwd(), "measurement_data")
os.makedirs(output_dir, exist_ok=True)
measurement_file = os.path.join(output_dir, "live_measurement.csv")

# 创建硬件模拟器
self.hardware_simulator = HardwareSimulator(
    theoretical_data=self.theoretical_data,
    measurement_params=measurement_params,
    output_file_path=measurement_file
)

# 创建误差分析工作线程
self.analysis_worker = AnalysisWorker(
    theoretical_data=self.theoretical_data,
    measurement_file_path=measurement_file
)
```

#### 7. 信号槽连接 (main_window.py:1017-1033)
```python
# 连接硬件模拟器信号
self.hardware_simulator.measurement_point.connect(self.on_measurement_point)
self.hardware_simulator.measurement_finished.connect(self.on_measurement_finished)
self.hardware_simulator.measurement_error.connect(self.on_measurement_error)
self.hardware_simulator.progress_updated.connect(self.on_progress_updated)

# 连接误差分析工作线程信号
self.analysis_worker.analysis_result.connect(self.on_analysis_result)
self.analysis_worker.statistics_updated.connect(self.on_statistics_updated)
self.analysis_worker.error_data_updated.connect(self.on_error_data_updated)
self.analysis_worker.analysis_finished.connect(self.on_analysis_finished)
self.analysis_worker.analysis_error.connect(self.on_analysis_error)
```

#### 8. 启动线程与UI更新 (main_window.py:1035-1042)
```python
# 启动线程
self.hardware_simulator.start()
self.analysis_worker.start()

# 更新UI状态
self.update_ui_measurement_started()

print("测量和分析线程已启动")
```

#### 9. UI状态更新实现 (main_window.py:1085-1098)
```python
def update_ui_measurement_started(self):
    """更新UI状态为测量开始"""
    self.is_measuring = True
    
    # 更新按钮状态
    self.start_measure_btn.setEnabled(False)
    self.pause_btn.setEnabled(True) 
    self.stop_btn.setEnabled(True)
    
    # 更新状态指示器
    self.status_text.setText("测量中...")
    self.status_indicator.setStyleSheet("color: #22c55e; font-size: 12px;")
    
    print("UI状态已更新为测量开始")
```

---

## 🔬 硬件模拟器线程执行流程

### HardwareSimulator.run() 主流程 (hardware_simulator.py:63-101)

#### 1. 线程初始化
```python
def run(self):
    """线程主执行方法 - 模拟硬件测量过程"""
    try:
        print("开始硬件模拟测量过程...")
        self.is_running = True
        
        # 初始化CSV文件
        self.initialize_output_file()
        
        print(f"理论数据点数: {len(self.theoretical_data)}")
```

#### 2. 测量点筛选 (hardware_simulator.py:73-79)
```python
# 根据测量参数筛选测量点
measurement_points = self.filter_measurement_points()
print(f"选择的X坐标: {len(measurement_points['x_mm'].unique())} 个")
print(f"生成的测量点: {len(measurement_points)} 个")

self.total_points = len(measurement_points)
print(f"根据测量参数，需要测量 {self.total_points} 个点")
```

#### 3. 循环测量模拟 (hardware_simulator.py:81-101)
```python
# 遍历每个测量点进行模拟
for idx, row in measurement_points.iterrows():
    if not self.is_running:
        break
        
    # 等待暂停状态
    while self.is_paused and self.is_running:
        time.sleep(0.1)
    
    if not self.is_running:
        break
    
    # 执行单点测量
    self.simulate_single_measurement(idx + 1, row)
    
    # 测量间隔延时
    time.sleep(self.measurement_params['measurement_delay'])
```

#### 4. 单点测量实现 (hardware_simulator.py:180-220)
```python
def simulate_single_measurement(self, sequence, point_data):
    """模拟单个点的测量过程"""
    x_pos = point_data['x_mm']
    y_ideal = point_data['y_mm'] 
    z_ideal = point_data['z_mm']
    
    # 计算理想的柱坐标
    ideal_radius = math.sqrt(y_ideal**2 + z_ideal**2)
    ideal_angle_rad = math.atan2(z_ideal, y_ideal)
    angle_deg = math.degrees(ideal_angle_rad)
    
    # 添加测量误差
    measured_radius = self.simulate_measurement_error(
        ideal_radius, x_pos, angle_deg
    )
    
    print(f"测量点 #{sequence}: X={x_pos}, 角度={angle_deg:.1f}°, 半径={measured_radius:.6f}")
    
    # 发射测量信号
    self.measurement_point.emit(sequence, x_pos, angle_deg, measured_radius)
    
    # 写入CSV文件
    self.write_measurement_to_file(sequence, x_pos, angle_deg, measured_radius)
    
    # 更新进度
    self.progress_updated.emit(sequence, self.total_points)
```

### 误差模拟算法 (hardware_simulator.py:242-275)
```python
def simulate_measurement_error(self, ideal_radius, x_pos, angle_deg):
    """为理想半径值添加模拟误差"""
    
    # 1. 系统性误差 (固定偏移)
    systematic_error = self.systematic_error
    
    # 2. 随机噪声 (高斯分布)
    random_noise = random.gauss(0, self.random_noise_level)
    
    # 3. 位置相关误差 (基于角度和位置)
    angle_error = 0.02 * math.sin(math.radians(angle_deg * 2))  # 角度相关
    position_error = 0.01 * (x_pos / 100.0)  # 位置相关
    
    # 4. 周期性误差 (模拟机械振动等)
    cyclic_error = 0.005 * math.sin(math.radians(angle_deg * 4))
    
    # 组合所有误差
    total_error = (systematic_error + random_noise + 
                  angle_error + position_error + cyclic_error)
    
    # 限制误差范围
    max_error = self.error_amplitude
    total_error = max(-max_error, min(max_error, total_error))
    
    measured_radius = ideal_radius + total_error
    return measured_radius
```

---

## 📊 误差分析线程执行流程  

### AnalysisWorker.run() 主流程 (analysis_worker.py:57-95)

#### 1. 初始化与索引创建
```python
def run(self):
    """线程主执行方法 - 实时监控测量文件并分析"""
    try:
        print("开始监控测量文件...")
        self.is_running = True
        
        # 创建理论数据查找索引
        self.create_theoretical_lookup()
        print(f"理论数据索引创建完成，索引项数: {len(self.theoretical_lookup)}")
```

#### 2. 文件监控循环 (analysis_worker.py:71-95)
```python
# 主监控循环
while self.is_running:
    # 等待暂停状态
    while self.is_paused and self.is_running:
        time.sleep(0.1)
    
    if not self.is_running:
        break
    
    # 检查文件是否存在和变化
    if os.path.exists(self.measurement_file_path):
        current_size = os.path.getsize(self.measurement_file_path)
        if current_size > self.last_file_size:
            self.process_new_data()
            self.last_file_size = current_size
    
    time.sleep(0.1)  # 100ms检查间隔
```

#### 3. 理论数据索引创建 (analysis_worker.py:117-141)
```python
def create_theoretical_lookup(self):
    """创建理论数据的快速查找索引"""
    self.theoretical_lookup = {}
    
    for _, row in self.theoretical_data.iterrows():
        x_mm = row['x_mm']
        y_mm = row['y_mm']
        z_mm = row['z_mm']
        
        # 计算角度用于索引
        angle_rad = math.atan2(z_mm, y_mm)
        angle_deg = math.degrees(angle_rad)
        
        # 创建索引键 - 量化角度避免浮点精度问题
        angle_key = round(angle_deg / 0.1) * 0.1
        index_key = (x_mm, angle_key)
        
        # 存储完整的理论点信息
        self.theoretical_lookup[index_key] = {
            'x_mm': x_mm,
            'y_mm': y_mm, 
            'z_mm': z_mm,
            'radius': math.sqrt(y_mm**2 + z_mm**2),
            'angle_deg': angle_deg
        }
    
    print(f"理论数据索引创建完成，索引项数: {len(self.theoretical_lookup)}")
```

#### 4. 新数据处理 (analysis_worker.py:143-171)
```python
def process_new_data(self):
    """处理新增的测量数据"""
    try:
        with open(self.measurement_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 跳过已处理的行（包括表头）
        new_lines = lines[max(1, self.processed_lines):]
        
        for line in new_lines:
            line = line.strip()
            if line and not line.startswith('sequence'):
                # 处理单行数据
                result = self.process_measurement_line(line)
                if result:
                    # 发射分析结果信号
                    self.analysis_result.emit(result)
                    
                    # 更新统计
                    self.update_statistics(result['error_analysis'])
                    
        self.processed_lines = len(lines)
```

#### 5. 单行数据分析 (analysis_worker.py:173-230)
```python
def process_measurement_line(self, line):
    """处理单行测量数据并计算误差"""
    try:
        # 解析CSV行数据
        parts = line.strip().split(',')
        if len(parts) != 4:
            return None
            
        sequence = int(parts[0])
        x_pos = float(parts[1])
        angle_deg = float(parts[2])
        measured_radius = float(parts[3])
        
        # 查找对应的理论值
        theoretical_point = self.find_theoretical_point(x_pos, angle_deg)
        if theoretical_point is None:
            print(f"警告: 找不到对应的理论点 X={x_pos}, 角度={angle_deg}")
            return None
        
        # 计算误差
        theoretical_radius = theoretical_point['radius']
        radius_error = measured_radius - theoretical_radius
        
        # 转换为笛卡尔坐标
        measured_point = self.convert_to_cartesian(x_pos, angle_deg, measured_radius)
        
        # 构造完整结果
        result = {
            'sequence': sequence,
            'x_pos': x_pos,
            'angle_deg': angle_deg, 
            'measured_radius': measured_radius,
            'theoretical_radius': theoretical_radius,
            'error_analysis': {
                'radius_error': radius_error,
                'abs_error': abs(radius_error),
                'status': 'qualified' if abs(radius_error) <= 0.1 else 'attention' if abs(radius_error) <= 0.3 else 'over_tolerance'
            },
            'measured_point': measured_point
        }
        
        return result
```

#### 6. 坐标转换实现 (analysis_worker.py:362-375)
```python
def convert_to_cartesian(self, x, angle_deg, radius):
    """柱坐标转换为笛卡尔坐标"""
    angle_rad = math.radians(angle_deg)
    
    # 柱坐标转换公式
    cart_x = x  # X坐标不变
    cart_y = radius * math.cos(angle_rad)
    cart_z = radius * math.sin(angle_rad)
    
    return (cart_x, cart_y, cart_z)
```

---

## 📈 实时数据更新流程

### 测量点信号处理 (main_window.py:1124-1134)
```python
def on_measurement_point(self, sequence, x_pos, angle_deg, measured_radius):
    """处理硬件模拟器的测量点信号"""
    print(f"收到测量点: 序号={sequence}, X={x_pos}, 角度={angle_deg}, 半径={measured_radius}")
    
    # 更新实时状态显示
    self.current_x = x_pos
    self.current_angle = angle_deg
    self.current_x_label.setText(f"{x_pos:.1f} mm")
    self.current_angle_label.setText(f"{angle_deg:.1f}°")
```

### 分析结果信号处理 (main_window.py:1136-1159)  
```python
def on_analysis_result(self, result):
    """处理误差分析结果信号"""
    try:
        # 提取数据
        sequence = result['sequence']
        x_pos = result['x_pos']
        angle_deg = result['angle_deg']
        measured_radius = result['measured_radius']
        theoretical_radius = result['theoretical_radius']
        error_analysis = result['error_analysis']
        measured_point = result['measured_point']
        
        # 添加到数据表格
        self.add_analysis_result_to_table(
            sequence, x_pos, angle_deg, measured_radius,
            theoretical_radius, error_analysis
        )
        
        # 添加测量点到3D可视化
        self.add_measured_point_to_3d(measured_point, error_analysis)
        
        print(f"分析结果已添加到表格和3D视图: 序号={sequence}, 误差={error_analysis['radius_error']:.6f}")
```

### 3D可视化更新 (main_window.py:857-893)
```python  
def add_measured_point_to_3d(self, measured_point, error_analysis):
    """添加测量点到3D可视化"""
    if self.point_cloud_ax is None:
        return
        
    try:
        x, y, z = measured_point
        error = error_analysis['radius_error']
        
        # 根据误差确定颜色
        if abs(error) <= 0.05:
            color = 'green'      # 合格
        elif abs(error) <= 0.1: 
            color = 'yellow'     # 注意
        else:
            color = 'red'        # 超差
        
        # 添加单个测量点
        self.point_cloud_ax.scatter([x], [y], [z], 
                                   c=color, 
                                   s=10, 
                                   alpha=0.8)
        
        # 刷新画布
        self.point_cloud_canvas.draw()
```

### 统计数据更新 (main_window.py:1199-1209)
```python
def on_statistics_updated(self, statistics):
    """处理统计数据更新信号"""
    try:
        # 更新统计标签
        self.max_error_label.setText(f"{statistics['max_error']:+.3f} mm")
        self.min_error_label.setText(f"{statistics['min_error']:+.3f} mm") 
        self.avg_error_label.setText(f"{statistics['avg_error']:+.3f} mm")
        self.std_error_label.setText(f"{statistics['std_error']:.3f} mm")
        
    except Exception as e:
        print(f"更新统计数据时出错: {e}")
```

---

## 🎛️ 线程控制流程

### 暂停测量 (main_window.py:1245-1264)
```python
def pause_measurement(self):
    """暂停测量 - 使用新的模拟器系统"""
    print("=== 暂停测量功能 ===")
    
    # 暂停线程
    if self.hardware_simulator is not None:
        self.hardware_simulator.pause()
        print("硬件模拟器已暂停")
        
    if self.analysis_worker is not None:
        self.analysis_worker.pause() 
        print("误差分析工作线程已暂停")
    
    # 更新状态
    self.status_text.setText("已暂停")
    self.status_indicator.setStyleSheet("color: #eab308; font-size: 12px;")
    
    # 更新按钮状态
    self.start_measure_btn.setEnabled(True)
    self.pause_btn.setEnabled(False)
    
    print("测量已暂停")
```

### 停止测量 (main_window.py:1266-1286)
```python  
def stop_measurement(self):
    """停止测量 - 使用新的模拟器系统"""
    print("=== 停止测量功能 ===")
    
    # 停止并清理线程
    self.cleanup_threads()
    
    # 重置状态
    self.is_measuring = False
    self.status_text.setText("已停止")
    self.status_indicator.setStyleSheet("color: #ef4444; font-size: 12px;")
    
    # 重置按钮状态
    self.update_ui_measurement_finished()
    
    print("测量已停止")
```

---

## 📊 数据流总结

### 完整数据流向图
```
用户点击"开始测量"
        ↓
读取界面参数 → 创建线程对象 → 连接信号槽 → 启动线程
        ↓
HardwareSimulator.run():
理论数据 → 筛选测量点 → 循环模拟测量 → 添加误差 → 写入CSV → 发射信号
        ↓
AnalysisWorker.run():
监控文件变化 → 读取新数据行 → 查找理论对应点 → 计算误差 → 发射结果信号
        ↓
MainWindow信号处理:
接收信号 → 更新表格 → 更新3D视图 → 更新统计数据 → 刷新界面
```

### 关键数据结构
- **理论数据**: `pd.DataFrame` 包含 x_mm, y_mm, z_mm 列
- **测量参数**: `dict` 包含范围、步长、延时等参数  
- **测量数据**: CSV格式文件，实时写入
- **分析结果**: `dict` 包含误差计算和状态判断
- **统计数据**: 实时计算的最大/最小/平均误差等指标

### 性能优化点
- **理论数据索引**: O(1)复杂度的点查找
- **增量处理**: 只处理文件中的新增数据行
- **线程分离**: UI响应与数据处理完全分离
- **内存控制**: 限制历史数据缓存大小

此文档详细展示了软件主要功能背后的完整代码执行流程，有助于理解系统的技术实现和数据处理机制。
