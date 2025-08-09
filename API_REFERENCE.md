# API 参考文档

## 📖 概述

本文档详细描述了模具曲面精度分析系统中所有类、方法和函数的API接口。

## 📁 模块结构

### main_window.py

#### MainWindow 类

**继承**: `QMainWindow`

**描述**: 应用程序的主窗口类，负责整个界面的构建和交互逻辑。

##### 构造方法

```python
def __init__(self)
```
**功能**: 初始化主窗口实例
- 设置状态变量
- 初始化定时器
- 调用UI构建方法
- 设置样式和信号连接

**状态变量**:
- `is_measuring: bool` - 测量状态标记
- `simulation_timer: QTimer` - 模拟数据定时器
- `current_sequence: int` - 当前测量序号
- `measurement_count: int` - 已测量点数
- `total_measurement_count: int` - 预计总测量点数
- `current_x: float` - 当前X坐标
- `current_angle: float` - 当前旋转角度
- `errors_list: List[float]` - 误差数据列表

##### UI构建方法

```python
def init_ui(self) -> None
```
**功能**: 初始化用户界面
- 设置窗口属性（标题、尺寸）
- 创建菜单栏、工具栏、中央部件

```python
def create_menu_bar(self) -> None
```
**功能**: 创建应用程序菜单栏
**菜单项**: 文件(F), 视图(V), 工具(T), 帮助(H)

```python
def create_toolbar(self) -> None
```
**功能**: 创建工具栏
**按钮组件**:
- `load_model_btn: QPushButton` - 加载模型按钮
- `reset_view_btn: QPushButton` - 重置视图按钮
- `start_measure_btn: QPushButton` - 开始测量按钮
- `pause_btn: QPushButton` - 暂停按钮
- `stop_btn: QPushButton` - 停止按钮

```python
def create_central_widget(self) -> None
```
**功能**: 创建中央窗口部件
**布局**: 三栏水平布局（左侧面板 | 中心区域 | 右侧面板）

```python
def create_left_panel(self) -> QFrame
```
**功能**: 创建左侧面板
**返回**: QFrame 对象
**包含组件**:
- 理论模型信息组
- 测量参数设置组  
- 实时状态监控组

```python
def create_center_panel(self) -> QFrame  
```
**功能**: 创建中心面板
**返回**: QFrame 对象
**包含组件**:
- 3D可视化占位符
- 实时数据表格

```python
def create_right_panel(self) -> QFrame
```
**功能**: 创建右侧面板  
**返回**: QFrame 对象
**包含组件**:
- 颜色图例组
- 总体误差统计组
- 误差分布图表组

##### 子组件创建方法

```python
def create_model_info_group(self) -> QWidget
```
**功能**: 创建理论模型信息组件
**组件引用**:
- `model_name_label: QLabel` - 模型名称标签
- `rotation_range_label: QLabel` - 旋转范围标签
- `load_cad_btn: QPushButton` - CAD加载按钮

```python
def create_measurement_params_group(self) -> QWidget  
```
**功能**: 创建测量参数设置组件
**输入组件**:
- `x_min_input: QLineEdit` - X轴最小值输入框
- `x_max_input: QLineEdit` - X轴最大值输入框  
- `x_step_input: QLineEdit` - X轴步长输入框
- `rot_step_input: QLineEdit` - 旋转步长输入框

```python
def create_status_monitor_group(self) -> QWidget
```
**功能**: 创建实时状态监控组件
**显示组件**:
- `current_x_label: QLabel` - 当前X位置标签
- `current_angle_label: QLabel` - 当前角度标签
- `valid_angle_label: QLabel` - 有效角度标签
- `status_indicator: QLabel` - 状态指示器
- `status_text: QLabel` - 状态文本

```python
def create_data_table(self, parent_layout: QVBoxLayout) -> None
```
**功能**: 创建实时数据表格
**参数**: 
- `parent_layout: QVBoxLayout` - 父级布局
**表格组件**:
- `data_table: QTableWidget` - 数据表格
- `table_status_label: QLabel` - 表格状态标签

```python
def create_color_legend_group(self) -> QWidget
```
**功能**: 创建颜色图例组件
**数据来源**: `AppConfig.get_color_legend_items()`

```python  
def create_error_stats_group(self) -> QWidget
```
**功能**: 创建误差统计组件
**统计标签**:
- `max_error_label: QLabel` - 最大误差
- `min_error_label: QLabel` - 最小误差
- `avg_error_label: QLabel` - 平均误差
- `std_error_label: QLabel` - 标准差

```python
def create_error_chart_group(self) -> QWidget
```
**功能**: 创建误差图表组件（占位符）

##### 系统设置方法

```python
def setup_style(self) -> None
```
**功能**: 应用界面样式
**样式来源**: `StyleManager.get_main_stylesheet()`

```python
def setup_connections(self) -> None  
```
**功能**: 设置信号槽连接
**连接关系**:
```python
# 工具栏按钮
self.load_model_btn.clicked -> self.load_model
self.start_measure_btn.clicked -> self.start_measurement  
self.pause_btn.clicked -> self.pause_measurement
self.stop_btn.clicked -> self.stop_measurement

# 面板按钮
self.load_cad_btn.clicked -> self.load_model

# 定时器
self.simulation_timer.timeout -> self.simulation_step
```

##### 交互功能方法

```python
def load_model(self) -> None
```
**功能**: 加载CAD模型文件
**流程**:
1. 打开文件选择对话框
2. 验证文件格式
3. 更新模型信息显示
4. 控制台输出文件路径
5. 显示成功消息

**支持格式**: .step, .stp, .iges, .igs, .stl

```python  
def reset_view(self) -> None
```
**功能**: 重置视图到默认状态
**操作**: 显示重置确认消息

```python
def start_measurement(self) -> None
```
**功能**: 开始测量过程
**流程**:
1. 调用 `read_measurement_parameters()` 读取参数
2. 更新按钮状态（禁用开始，启用暂停/停止）
3. 设置 `is_measuring = True`
4. 更新状态指示器
5. 启动模拟定时器 (1秒间隔)

```python
def pause_measurement(self) -> None  
```
**功能**: 暂停测量过程
**条件**: `is_measuring == True`
**流程**:
1. 停止定时器
2. 设置 `is_measuring = False`  
3. 更新状态指示器为警告状态
4. 更新按钮状态

```python
def stop_measurement(self) -> None
```
**功能**: 停止测量过程
**流程**:
1. 停止定时器
2. 重置状态变量
3. 重置按钮状态
4. 更新状态指示器为错误状态

```python
def simulation_step(self) -> None
```
**功能**: 执行一次模拟测量步骤
**频率**: 每秒执行一次（由定时器触发）
**流程**:
1. 生成随机测量数据
2. 计算误差和状态
3. 调用 `add_table_row()` 添加到表格
4. 调用 `update_statistics()` 更新统计
5. 调用 `update_real_time_status()` 更新状态
6. 递增计数和位置
7. 检查是否达到总数限制

##### 数据处理方法

```python
def read_measurement_parameters(self) -> None
```
**功能**: 读取用户输入的测量参数
**读取数据**:
- X轴范围 (min, max)
- X轴步长
- 旋转轴步长
**异常处理**: `ValueError` - 显示参数错误警告
**计算**: 根据参数估算总测量点数

```python
def add_table_row(
    self, 
    sequence: int, 
    x_coord: float, 
    angle: float, 
    measured: float, 
    theoretical: float, 
    error: float, 
    status: str
) -> None
```
**功能**: 向数据表格添加新行
**参数说明**:
- `sequence`: 测量序号
- `x_coord`: X坐标值
- `angle`: 旋转角度
- `measured`: 测量值
- `theoretical`: 理论值
- `error`: 误差值
- `status`: 状态("合格"/"注意"/"超差!")

**颜色编码**:
- 超差: 黄色背景 (#fef3c7)
- 注意: 橙色背景 (#fef0e6)
- 合格: 默认背景

```python
def update_statistics(self) -> None
```
**功能**: 更新统计信息显示
**计算项目**:
- 最大误差: `max(errors_list)`
- 最小误差: `min(errors_list)`  
- 平均误差: `sum(errors_list) / len(errors_list)`
- 标准差: `sqrt(variance)`

```python
def update_real_time_status(self) -> None
```
**功能**: 更新实时状态显示
**更新内容**:
- 当前X位置标签
- 当前角度标签  
- 表格状态标签（进度信息）

##### 辅助方法

```python
def populate_sample_data(self) -> None
```
**功能**: 填充示例数据到表格
**数据**: 3行预设的测量数据

```python  
def init_timer(self) -> None
```
**功能**: 初始化定时器（当前为空实现）

### config.py

#### AppConfig 类

**类型**: 配置类（静态属性）

**描述**: 集中管理应用程序的所有配置参数。

##### 应用信息配置

```python
APP_NAME: str = "模具曲面精度分析系统"
APP_VERSION: str = "2.1"  
APP_ORGANIZATION: str = "工业精度检测"
```

##### 窗口尺寸配置

```python
WINDOW_WIDTH: int = 1440        # 主窗口宽度
WINDOW_HEIGHT: int = 900        # 主窗口高度
WINDOW_MIN_WIDTH: int = 1200    # 最小宽度
WINDOW_MIN_HEIGHT: int = 700    # 最小高度
LEFT_PANEL_WIDTH: int = 320     # 左侧面板宽度
RIGHT_PANEL_WIDTH: int = 320    # 右侧面板宽度
```

##### 默认参数配置

```python
DEFAULT_X_MIN: float = -5.0     # X轴最小值
DEFAULT_X_MAX: float = 500.0    # X轴最大值
DEFAULT_X_STEP: float = 10.0    # X轴步长
DEFAULT_ROT_STEP: float = 1.5   # 旋转步长
```

##### 系统配置

```python
DATA_UPDATE_INTERVAL: int = 2000  # 数据更新间隔(毫秒)
```

##### 颜色配置

```python
COLORS: Dict[str, str] = {
    'error_positive_high': '#ef4444',   # 正向超差
    'error_positive_low': '#f97316',    # 正向误差  
    'error_normal': '#10b981',          # 合格范围
    'error_negative_low': '#3b82f6',    # 负向误差
    'error_negative_high': '#1e40af',   # 负向超差
    'status_active': '#10b981',         # 活动状态
    'status_warning': '#f59e0b',        # 警告状态
    'status_error': '#ef4444',          # 错误状态
}
```

##### 误差阈值配置

```python
ERROR_THRESHOLDS: Dict[str, float] = {
    'high_positive': 0.5,     # 高正向阈值
    'low_positive': 0.25,     # 低正向阈值
    'normal': 0.0,            # 正常值
    'low_negative': -0.25,    # 低负向阈值
    'high_negative': -0.5,    # 高负向阈值
}
```

##### 文件格式配置

```python
SUPPORTED_MODEL_FORMATS: List[str] = [
    '.step', '.stp', '.iges', '.igs', '.stl'
]
```

##### 类方法

```python
@classmethod
def get_color_legend_items(cls) -> List[Tuple[str, str]]
```
**功能**: 获取颜色图例项目列表
**返回**: [(颜色代码, 描述文本), ...]

```python
@classmethod  
def get_error_color(cls, error_value: float) -> str
```
**功能**: 根据误差值获取对应颜色
**参数**: `error_value` - 误差值
**返回**: 颜色代码字符串

### styles.py

#### StyleManager 类

**类型**: 样式管理类（静态方法）

**描述**: 管理应用程序的所有QSS样式表。

##### 样式方法

```python
@staticmethod
def get_main_stylesheet() -> str
```
**功能**: 获取主要样式表
**返回**: 完整的QSS样式字符串
**样式覆盖**:
- 主窗口和基础组件
- 菜单栏样式
- 工具栏样式  
- 按钮样式（多种类型）
- 面板和框架样式
- 标签和文本样式
- 输入框样式
- 表格样式
- 滚动条样式
- 占位符样式

```python
@staticmethod
def get_color_block_style(color: str) -> str
```
**功能**: 生成颜色块样式
**参数**: `color` - 颜色代码
**返回**: 颜色块的QSS样式字符串

### data_manager.py

#### MeasurementPoint 数据类

**类型**: `@dataclass`

**描述**: 测量点数据结构定义。

##### 属性

```python
sequence: int           # 测量序号
x_coord: float         # X坐标位置
angle: float           # 旋转角度
measured_value: float  # 实际测量值
theoretical_value: float # 理论计算值
error: float           # 误差值
status: str            # 测量状态
```

#### DataManager 类

**继承**: `QObject`

**描述**: 数据管理器，处理测量数据的存储和计算。

**注意**: 当前版本中未在主程序中使用，为扩展预留。

##### 信号定义

```python
data_updated = Signal()          # 数据更新信号
statistics_updated = Signal(dict) # 统计更新信号
```

##### 方法接口

```python
def __init__(self)
```
**功能**: 初始化数据管理器

```python
def add_measurement_point(
    self, 
    x_coord: float, 
    angle: float, 
    measured_value: float, 
    theoretical_value: float
) -> MeasurementPoint
```
**功能**: 添加测量点数据

```python
def get_all_data(self) -> List[MeasurementPoint]
```
**功能**: 获取所有测量数据

```python
def update_statistics(self) -> None  
```
**功能**: 更新统计信息

## 🔧 使用示例

### 基本用法

```python
from main_window import MainWindow
from PySide6.QtWidgets import QApplication
import sys

# 创建应用程序
app = QApplication(sys.argv)

# 创建主窗口
window = MainWindow()
window.show()

# 运行应用程序
sys.exit(app.exec())
```

### 扩展UI组件

```python
class MainWindow(QMainWindow):
    def create_custom_group(self):
        """创建自定义组件组"""
        group_widget = QWidget()
        layout = QVBoxLayout(group_widget)
        
        # 使用配置
        title = QLabel("自定义功能")
        title.setObjectName("groupTitle")
        
        # 使用样式
        button = QPushButton("自定义按钮")
        button.setObjectName("primaryButton")
        
        layout.addWidget(title)
        layout.addWidget(button)
        
        return group_widget
```

### 使用配置管理

```python
from config import AppConfig

# 读取配置
window_width = AppConfig.WINDOW_WIDTH
colors = AppConfig.COLORS
formats = AppConfig.SUPPORTED_MODEL_FORMATS

# 获取颜色
error_color = AppConfig.get_error_color(0.3)
legend_items = AppConfig.get_color_legend_items()
```

### 应用样式

```python
from styles import StyleManager

# 应用主样式
widget.setStyleSheet(StyleManager.get_main_stylesheet())

# 应用颜色块样式  
color_block.setStyleSheet(
    StyleManager.get_color_block_style("#ef4444")
)
```

## 📋 错误码参考

### 常见错误类型

| 错误类型 | 描述 | 处理方法 |
|---------|------|----------|
| `ValueError` | 参数格式错误 | 参数验证和用户提示 |
| `FileNotFoundError` | 文件路径无效 | 文件存在性检查 |
| `AttributeError` | 对象属性不存在 | 对象初始化检查 |
| `TypeError` | 类型不匹配 | 类型转换和验证 |

### 调试方法

```python
# 启用调试输出
def debug_component(self, component_name):
    print(f"=== 调试: {component_name} ===")
    
# 检查组件状态
def check_component_state(self):
    print(f"按钮状态: {self.start_measure_btn.isEnabled()}")
    print(f"测量状态: {self.is_measuring}")
    print(f"表格行数: {self.data_table.rowCount()}")
```

---

*本API文档最后更新：2025年8月9日*
