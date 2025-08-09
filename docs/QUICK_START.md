# 快速上手指南

## 🎯 15分钟快速上手

本指南帮助您在15分钟内快速了解项目结构并开始开发。

## ⚡ 第一步：环境准备 (2分钟)

### 检查环境
```bash
# 检查conda环境
conda env list | grep pyside-env

# 如果不存在，创建环境
conda create -n pyside-env python=3.9
conda activate pyside-env
pip install PySide6
```

### 运行项目
```bash
cd /path/to/mold-surface-inspector
conda activate pyside-env
python app.py
```

**✅ 验证**: 看到主窗口正常显示

## 🔍 第二步：理解项目结构 (3分钟)

### 核心文件（必须了解）
```
📁 mold-surface-inspector/
├── 🚪 app.py              ← 程序入口（10行代码）
├── 🏠 main_window.py      ← 核心文件（600行代码）
├── ⚙️ config.py           ← 配置管理（100行代码）
└── 🎨 styles.py           ← 样式管理（400行代码）
```

### 快速导航
- **修改界面布局** → `main_window.py`
- **修改配置参数** → `config.py`
- **修改界面样式** → `styles.py`
- **添加新功能** → `main_window.py` + 信号槽

## 🎨 第三步：界面结构一览 (3分钟)

### 布局层级
```
MainWindow
├── MenuBar          # 菜单：文件|视图|工具|帮助
├── ToolBar          # 工具栏：5个按钮
└── CentralWidget    # 主体：三栏布局
    ├── LeftPanel    # 左侧：参数设置 (320px)
    ├── CenterPanel  # 中心：表格+可视化
    └── RightPanel   # 右侧：统计图例 (320px)
```

### 关键组件引用
```python
# 在 MainWindow 类中可直接访问
self.start_measure_btn    # 开始测量按钮
self.data_table          # 数据表格
self.x_min_input         # X轴最小值输入框
self.current_x_label     # 当前X位置标签
```

## 🔧 第四步：核心交互逻辑 (4分钟)

### 信号槽机制
```python
# 在 setup_connections() 方法中
self.start_measure_btn.clicked.connect(self.start_measurement)
#     ↑ 信号源                         ↑ 处理函数

# 处理函数的典型结构
def start_measurement(self):
    print("=== 功能执行 ===")        # 1. 调试输出
    self.read_parameters()          # 2. 读取参数  
    self.update_ui_state()         # 3. 更新界面
    self.start_timer()             # 4. 启动逻辑
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
conda activate pyside-env
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
