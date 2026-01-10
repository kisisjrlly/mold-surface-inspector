# 快速上手指南 - 硬件测量模拟系统

## 🎯 15分钟快速了解系统

本指南帮助您快速理解项目的硬件模拟和误差分析功能。

## ⚡ 第一步：运行系统 (2分钟)

### 环境检查
```bash
# 检查conda环境
conda env list | grep inspector

# 如果环境不存在
conda create -n inspector python=3.9
conda activate inspector
pip install -r requirements.txt
```

### 启动应用
```bash
cd /path/to/mold-surface-inspector
conda activate inspector

# 方式1: 使用启动脚本
./launch.sh

# 方式2: 直接运行
python app.py
```

**✅ 验证**: 主窗口显示，包含左中右三栏布局

## 🏗️ 第二步：理解系统架构 (4分钟)

### 核心文件结构
```
📁 mold-surface-inspector/
├── 🚪 app.py                    ← 程序入口
├── 🏠 main_window.py           ← UI控制层 (1400+行)
├── 🔧 hardware_simulator.py    ← 硬件模拟器线程 (320行)
├── 📊 analysis_worker.py       ← 误差分析线程 (412行)
├── ⚙️ config.py               ← 配置管理
├── 🎨 styles.py               ← QSS样式
├── 📁 data/                   ← 理论数据目录
│   └── semicylinder_pointcloud.csv
├── 📁 measurement_data/       ← 测量输出目录
└── 📁 test_output/           ← 测试数据目录
```

### 多线程工作流程
```
用户操作 → MainWindow → 创建线程 → 数据处理 → 界面更新
                    ↓
            HardwareSimulator    AnalysisWorker
                    │                    │
                生成测量数据            实时误差计算
                    │                    │
                 CSV文件 ←→ 文件监控 ←→ 统计分析
                    │                    │
                    └→ 信号通信 ←→ UI更新 ←┘
```

## 🚀 第三步：体验核心功能 (5分钟)

### 加载理论数据
1. 点击 "📁 加载模型" 按钮
2. 选择 `data/semicylinder_pointcloud.csv` 文件
3. 观察左侧面板显示数据信息

### 开始测量模拟
1. **设置测量参数**:
   - X轴范围: 0-50mm
   - X轴步长: 10mm  
   - 旋转步长: 30°
2. **启动测量**: 点击 "▶ 开始测量" 按钮
3. **观察过程**:
   - 实时状态更新 (绿色"测量中...")
   - 数据表格逐行填充
   - 3D视图显示测量点
   - 右侧统计数据更新

### 查看分析结果
- **误差统计**: 右上角显示最大/最小/平均误差
- **分布图表**: 右下角直方图显示误差分布
- **3D可视化**: 中心区域显示理论点云(蓝色)和测量点(绿色)

## 🔧 第四步：理解技术实现 (4分钟)

### 硬件模拟器 (hardware_simulator.py)
```python
class HardwareSimulator(QThread):
    """模拟测量设备的数据采集过程"""
    
    # 核心信号
    measurement_point = Signal(int, float, float, float)  # 序号,X,角度,半径
    measurement_finished = Signal()                       # 完成信号
    progress_updated = Signal(int, int)                   # 进度更新
    
    def run(self):
        # 1. 筛选测量点（循环旋转模式）
        measurement_points = self.filter_measurement_points()
        
        # 2. 逐点模拟测量
        for point in measurement_points:
            measured_radius = self.simulate_measurement_error(ideal_radius)
            self.measurement_point.emit(sequence, x, angle, measured_radius)
            time.sleep(self.measurement_delay)
```

### 误差分析器 (analysis_worker.py)  
```python
class AnalysisWorker(QThread):
    """实时误差计算和统计分析"""
    
    # 核心信号
    analysis_result = Signal(dict)      # 分析结果
    statistics_updated = Signal(dict)   # 统计更新
    
    def run(self):
        # 1. 创建理论数据查找索引
        self.create_theoretical_lookup()
        
        # 2. 监控测量文件变化
        while self.is_running:
            if file_size_changed:
                new_lines = read_new_lines()
                for line in new_lines:
                    result = self.process_measurement_line(line)
                    self.analysis_result.emit(result)
```

### 主窗口控制 (main_window.py)
```python
def start_measurement(self):
    """启动完整的测量和分析流程"""
    
    # 1. 创建工作线程
    self.hardware_simulator = HardwareSimulator(...)
    self.analysis_worker = AnalysisWorker(...)
    
    # 2. 连接信号槽
    self.hardware_simulator.measurement_point.connect(self.on_measurement_point)
    self.analysis_worker.analysis_result.connect(self.on_analysis_result)
    
    # 3. 启动线程
    self.hardware_simulator.start()
    self.analysis_worker.start()
```

## 📊 第五步：数据流理解 (2分钟)

### 数据处理流水线
```
理论点云数据 (CSV)
        ↓
过滤筛选 (按测量参数)
        ↓
添加模拟误差 (多层误差模型)  
        ↓
实时写入文件 (live_measurement.csv)
        ↓
文件监控分析 (增量处理)
        ↓
坐标转换计算 (柱坐标↔笛卡尔)
        ↓
误差统计分析 (实时更新)
        ↓
界面数据显示 (表格+图表+3D)
```

### 关键数据格式
```python
# 理论数据格式 (输入)
theoretical_data = {
    'x_mm': [0.0, 0.0, ...],
    'y_mm': [500.0, 499.8, ...], 
    'z_mm': [0.0, 31.2, ...]
}

# 测量数据格式 (中间)
"sequence,x_mm,angle_deg,measured_radius"
"1,0.0,0.0,500.023"

# 分析结果格式 (输出)
analysis_result = {
    'sequence': 1,
    'error_analysis': {'radius_error': 0.023},
    'measured_point': (0.0, 500.023, 0.0)
}
```

## 🎯 下一步学习建议

### 🔰 初学者
- 阅读 [📖 API参考文档](API_REFERENCE.md) 了解详细接口
- 运行 `test_simulation.py` 理解测试流程
- 修改误差参数观察结果变化

### 🔧 开发者  
- 阅读 [🏗️ 架构文档](ARCHITECTURE.md) 了解设计决策
- 查看 [🔧 开发指南](DEV_GUIDE.md) 学习扩展方法
- 研究坐标转换算法优化

### ⚠️ 问题排查
- 查看 [🛠️ 故障排除](TROUBLESHOOTING.md) 常见问题
- 检查终端输出的调试信息
- 确认conda环境和依赖安装

## 💡 快速技巧

### 调试模式
```bash  
# 查看详细日志输出
python app.py 2>&1 | tee debug.log

# 独立测试硬件模拟器
python test_simulation.py
```

### 参数调优
```python
# 在 hardware_simulator.py 中调整误差模型
self.error_amplitude = 0.1      # 基础误差幅度
self.systematic_error = 0.02    # 系统性误差  
self.random_noise_level = 0.05  # 随机噪声级别
```

**🎉 恭喜！您已掌握系统核心功能，可以开始深入学习和开发了！**
```

### 状态管理
```python
# 重要的状态变量
self.is_measuring         # bool: 是否正在测量
self.simulation_timer     # QTimer: 模拟定时器
self.current_sequence     # int: 当前序号
self.errors_list         # List[float]: 误差数据
```

### 数据流转
```
用户点击 → 信号槽 → 处理函数 → 更新状态 → 界面刷新
   ↓         ↓        ↓         ↓        ↓
 [按钮]   [clicked] [函数]    [变量]   [标签/表格]
```

## 🚀 第五步：动手实践 (3分钟)

### 任务1: 添加一个新按钮
**目标**: 在工具栏添加"测试按钮"

1. **找到按钮创建位置**
```python
# 在 main_window.py 的 create_toolbar() 方法中
def create_toolbar(self):
    # ...existing buttons...
    
    # 添加你的按钮
    self.test_btn = QPushButton("🧪 测试按钮")
    self.test_btn.setObjectName("primaryButton")
    toolbar.addWidget(self.test_btn)
```

2. **添加信号连接**
```python
# 在 setup_connections() 方法中
def setup_connections(self):
    # ...existing connections...
    self.test_btn.clicked.connect(self.test_function)
```

3. **实现处理函数**
```python
# 在 MainWindow 类中添加
def test_function(self):
    """测试功能"""
    print("=== 测试按钮被点击 ===")
    QMessageBox.information(self, "测试", "测试功能正常工作！")
```

**✅ 验证**: 运行程序，点击按钮看到弹窗

### 任务2: 修改配置参数
**目标**: 修改窗口默认尺寸

```python
# 在 config.py 中修改
class AppConfig:
    WINDOW_WIDTH = 1600    # 改为1600
    WINDOW_HEIGHT = 1000   # 改为1000
```

**✅ 验证**: 重启程序，窗口变大

### 任务3: 修改界面样式
**目标**: 修改主按钮颜色

```python
# 在 styles.py 中修改
QPushButton#primaryButton {
    background-color: #7c3aed;  /* 改为紫色 */
    color: white;
}
```

**✅ 验证**: 重启程序，按钮变成紫色

## 📚 常用开发模式

### 模式1: 添加新的UI组
```python
def create_my_group(self):
    """创建自定义组"""
    group = QWidget()
    layout = QVBoxLayout(group)
    
    # 标题
    title = QLabel("我的功能")
    title.setObjectName("groupTitle")
    layout.addWidget(title)
    
    # 内容
    content = QPushButton("我的按钮")
    layout.addWidget(content)
    
    return group

# 在合适的面板创建方法中调用
layout.addWidget(self.create_my_group())
```

### 模式2: 添加配置项
```python
# 1. 在 config.py 中添加
class AppConfig:
    MY_NEW_CONFIG = "默认值"

# 2. 在代码中使用
value = AppConfig.MY_NEW_CONFIG
```

### 模式3: 处理用户输入
```python
def handle_user_input(self):
    """处理用户输入"""
    try:
        # 读取输入
        value = float(self.input_field.text())
        
        # 验证范围
        if not (0 <= value <= 100):
            raise ValueError("值必须在0-100之间")
            
        # 处理逻辑
        result = self.process_value(value)
        
        # 更新界面
        self.result_label.setText(f"结果: {result}")
        
    except ValueError as e:
        QMessageBox.warning(self, "输入错误", str(e))
```

## 🐛 常见问题速查

### 问题1: 按钮点击无反应
**检查清单**:
- [ ] 按钮是否已创建？
- [ ] 信号是否已连接？
- [ ] 处理函数是否存在？
- [ ] 控制台有错误信息吗？

### 问题2: 界面显示异常
**检查清单**:
- [ ] QSS样式是否有语法错误？
- [ ] 组件是否正确添加到布局？
- [ ] 是否调用了 `show()` 方法？

### 问题3: 找不到模块
```bash
# 解决方案
conda activate inspector
pip install 缺失的模块名
```

## 🎯 下一步学习

### 深入学习建议
1. **阅读完整文档** → `DEV_GUIDE.md`
2. **查看API参考** → `API_REFERENCE.md`
3. **研究功能实现** → `FUNCTIONS.md`
4. **练习代码修改** → 按上述任务实践

### 进阶开发方向
- 添加真实的3D可视化
- 实现数据文件导入导出
- 添加更复杂的统计分析
- 集成实际的测量设备

---

## 🎉 恭喜！

您已经完成了快速上手指南。现在您应该能够：

✅ 运行和修改项目  
✅ 理解基本的代码结构  
✅ 添加简单的新功能  
✅ 解决常见问题  

**下一步**: 选择一个感兴趣的功能进行深入开发！

---

*需要帮助？查看其他文档或在控制台输出调试信息。*
