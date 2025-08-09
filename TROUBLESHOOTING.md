# 🔧 故障排除指南

本文档提供常见问题的解决方案，帮助开发者快速解决遇到的问题。

## 📋 目录

- [环境问题](#环境问题)
- [运行问题](#运行问题)
- [界面问题](#界面问题)
- [功能问题](#功能问题)
- [性能问题](#性能问题)
- [开发问题](#开发问题)

## 🔧 环境问题

### 问题1: conda 环境创建失败

**症状**: 
```bash
CondaError: The following packages are not available from current channels
```

**解决方案**:
```bash
# 更新 conda
conda update conda

# 添加 conda-forge 频道
conda config --add channels conda-forge

# 重新创建环境
conda env remove -n pyside-env
conda create -n pyside-env python=3.11 -y
conda activate pyside-env
pip install -r requirements.txt
```

### 问题2: PySide6 安装失败

**症状**: 
```bash
ERROR: Failed building wheel for PySide6
```

**解决方案**:
```bash
# 更新 pip
pip install --upgrade pip

# 清除缓存
pip cache purge

# 使用预编译轮子
pip install PySide6 --only-binary=all

# 如果仍失败，尝试指定版本
pip install PySide6==6.5.0
```

### 问题3: macOS 权限问题

**症状**: 
```bash
Permission denied: '/Users/xxx/work/mold-surface-inspector/run.sh'
```

**解决方案**:
```bash
# 给予执行权限
chmod +x run.sh install.sh

# 如果仍有问题，检查系统安全设置
# 系统偏好设置 -> 安全性与隐私 -> 隐私 -> 完全磁盘访问权限
```

## 🚀 运行问题

### 问题4: 应用启动后立即崩溃

**症状**: 
```bash
QApplication: invalid style override passed
```

**解决方案**:
```python
# 在 app.py 中添加环境检查
import os
os.environ['QT_MAC_WANTS_LAYER'] = '1'  # macOS 特殊设置

# 或者修改启动参数
app = QApplication(sys.argv)
app.setAttribute(Qt.AA_DontShowIconsInMenus, False)
```

### 问题5: 中文字体显示异常

**症状**: 中文显示为方框或乱码

**解决方案**:
```python
# 在 main_window.py 中添加字体设置
from PySide6.QtGui import QFont

def setup_fonts(self):
    """设置中文字体"""
    font = QFont("Arial Unicode MS", 10)  # macOS
    # font = QFont("Microsoft YaHei", 10)  # Windows
    # font = QFont("DejaVu Sans", 10)     # Linux
    self.setFont(font)
```

### 问题6: 应用无响应

**症状**: 界面卡死，点击无反应

**解决方案**:
```python
# 检查是否有阻塞的同步操作
# 将耗时操作移到 QThread

# 临时解决：增加事件处理
from PySide6.QtCore import QCoreApplication

def long_operation(self):
    for i in range(1000):
        # 耗时操作
        QCoreApplication.processEvents()  # 处理事件
        time.sleep(0.001)
```

## 🖥️ 界面问题

### 问题7: 窗口布局错乱

**症状**: 组件重叠或位置不正确

**解决方案**:
```python
# 检查布局管理器的使用
# 确保每个 widget 都有正确的父容器

# 调试布局
def debug_layout(self, widget, level=0):
    """调试布局结构"""
    indent = "  " * level
    print(f"{indent}{widget.__class__.__name__}: {widget.geometry()}")
    for child in widget.children():
        if hasattr(child, 'geometry'):
            self.debug_layout(child, level + 1)
```

### 问题8: QSS 样式不生效

**症状**: 界面样式与预期不符

**解决方案**:
```python
# 1. 检查 QSS 语法
# 2. 验证选择器是否正确
# 3. 确保样式应用顺序

# 调试样式
def debug_style(self, widget):
    """调试样式应用"""
    print(f"Widget: {widget.__class__.__name__}")
    print(f"ObjectName: {widget.objectName()}")
    print(f"StyleSheet: {widget.styleSheet()}")
```

### 问题9: 表格数据显示异常

**症状**: 表格为空或数据格式错误

**解决方案**:
```python
# 检查数据模型
def debug_table_data(self):
    """调试表格数据"""
    model = self.measurement_table.model()
    if model:
        print(f"行数: {model.rowCount()}")
        print(f"列数: {model.columnCount()}")
        for row in range(min(5, model.rowCount())):
            for col in range(model.columnCount()):
                item = model.item(row, col)
                print(f"[{row},{col}]: {item.text() if item else 'None'}")
```

## ⚙️ 功能问题

### 问题10: 文件对话框打开失败

**症状**: 点击"加载模型"无反应

**解决方案**:
```python
def load_model(self):
    """加载3D模型文件"""
    try:
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setNameFilter("3D模型文件 (*.step *.stp *.iges *.igs *.stl)")
        
        if file_dialog.exec() == QFileDialog.Accepted:
            file_path = file_dialog.selectedFiles()[0]
            print(f"选择的文件: {file_path}")
            # 处理文件...
    except Exception as e:
        print(f"文件对话框错误: {e}")
        # 使用备用方案
        file_path = QFileDialog.getOpenFileName(
            self, "选择3D模型文件", "", 
            "3D模型文件 (*.step *.stp *.iges *.igs *.stl)"
        )[0]
```

### 问题11: 测量数据模拟异常

**症状**: 测量开始后无数据更新

**解决方案**:
```python
def debug_simulation(self):
    """调试测量模拟"""
    print(f"定时器状态: {self.simulation_timer.isActive()}")
    print(f"测量状态: {self.is_measuring}")
    print(f"表格行数: {self.measurement_table.rowCount()}")
    
    # 检查定时器连接
    self.simulation_timer.timeout.disconnect()
    self.simulation_timer.timeout.connect(self.simulation_step)
```

### 问题12: 参数读取错误

**症状**: 参数读取返回异常值

**解决方案**:
```python
def read_measurement_params_debug(self):
    """调试版参数读取"""
    try:
        params = {}
        
        # 逐个读取并验证
        x_start_text = self.x_start_input.text()
        print(f"X起始值文本: '{x_start_text}'")
        
        if not x_start_text.strip():
            print("警告: X起始值为空，使用默认值")
            x_start = -5.0
        else:
            x_start = float(x_start_text)
            
        params['x_start'] = x_start
        print(f"解析后的X起始值: {x_start}")
        
        return params
        
    except ValueError as e:
        print(f"参数解析错误: {e}")
        return None
```

## 🔧 性能问题

### 问题13: 内存占用过高

**症状**: 应用运行一段时间后内存持续增长

**解决方案**:
```python
import tracemalloc

def monitor_memory(self):
    """内存监控"""
    tracemalloc.start()
    
    # 执行操作...
    
    current, peak = tracemalloc.get_traced_memory()
    print(f"当前内存: {current / 1024 / 1024:.1f} MB")
    print(f"峰值内存: {peak / 1024 / 1024:.1f} MB")
    tracemalloc.stop()

# 检查常见内存泄漏点
# 1. 定时器未正确停止
# 2. 信号连接未断开
# 3. 大量数据未清理
```

### 问题14: 界面响应慢

**症状**: 点击按钮或更新界面有明显延迟

**解决方案**:
```python
import time
from functools import wraps

def timer_decorator(func):
    """性能计时装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"{func.__name__} 执行时间: {end - start:.3f}s")
        return result
    return wrapper

@timer_decorator
def update_statistics(self):
    """更新统计信息"""
    # 原有代码...
```

## 🔨 开发问题

### 问题15: 代码修改后不生效

**症状**: 修改代码后运行仍是旧版本

**解决方案**:
```bash
# 清除 Python 缓存
find . -name "__pycache__" -type d -exec rm -rf {} +
find . -name "*.pyc" -delete

# 重新启动应用
python app.py
```

### 问题16: Git 提交问题

**症状**: 无法提交代码或推送失败

**解决方案**:
```bash
# 检查状态
git status

# 添加忽略的文件
echo "__pycache__/" >> .gitignore
echo "*.pyc" >> .gitignore
echo ".DS_Store" >> .gitignore

# 重新提交
git add .
git commit -m "feat: 修复问题描述"
```

### 问题17: 代码格式化问题

**症状**: 代码风格不一致

**解决方案**:
```bash
# 安装格式化工具
pip install black isort flake8

# 格式化代码
black *.py
isort *.py

# 检查代码质量
flake8 *.py
```

## 📞 获取帮助

如果以上解决方案无法解决您的问题，请：

1. **查看日志**: 检查控制台输出的详细错误信息
2. **搜索问题**: 在 GitHub Issues 或 Stack Overflow 搜索类似问题
3. **创建最小复现**: 创建最简单的代码来重现问题
4. **提交Issue**: 在项目仓库创建详细的问题报告

### 问题报告模板

```markdown
## 问题描述
[简洁描述问题]

## 环境信息
- 操作系统: [macOS/Windows/Linux]
- Python版本: [例如 3.11.0]
- PySide6版本: [例如 6.5.0]

## 重现步骤
1. [步骤1]
2. [步骤2]
3. [步骤3]

## 预期行为
[描述预期发生什么]

## 实际行为
[描述实际发生了什么]

## 错误信息
```
[粘贴完整的错误堆栈]
```

## 尝试的解决方案
[描述已经尝试过的解决方案]
```

---

💡 **提示**: 保持冷静，仔细阅读错误信息，大多数问题都有标准的解决方案。记住，每个问题都是学习的机会！
