# 模具曲面精度分析系统

一个基于 Python 和 PySide6 开发的桌面应用程序，用于加载理论CAD模型信息和实时测量数据，通过对比分析两者差异来计算和可视化模具的表面精度误差。

## �️ 界面预览

![系统界面](./figures/UI_with_display_pointcloud.png)

*系统主界面：三栏布局设计，左侧为参数设置，中央为3D可视化，右侧为数据统计*

## �🚀 快速开始

### 环境要求

- Python 3.8+
- conda 环境管理器
- 已创建的 pyside-env 环境，包含 PySide6

### 安装和运行

1. **激活 conda 环境**
   ```bash
   conda activate pyside-env
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **运行应用程序**
   ```bash
   python app.py
   ```
   或使用启动脚本：
   ```bash
   ./launch.sh
   ```

## 🎯 使用流程

1. **加载理论数据**: 点击"📁 加载模型"，选择 `data/semicylinder_pointcloud.csv`
2. **设置测量参数**: 在左侧面板配置X轴范围、步长等参数  
3. **开始测量模拟**: 点击"▶ 开始测量"启动硬件模拟和误差分析
4. **实时查看结果**: 观察3D可视化、数据表格和统计图表的实时更新
5. **控制测量过程**: 使用暂停/停止按钮控制测量流程

## ✨ 核心功能

- **理论模型管理**: 支持加载CSV格式的理论点云数据文件
- **硬件模拟测量**: 通过 `HardwareSimulator` 类模拟测量设备的数据采集过程
- **实时误差分析**: 使用 `AnalysisWorker` 线程实时计算测量误差和统计数据  
- **3D数据可视化**: 实时显示理论点云和测量点的3D分布图
- **统计图表**: 提供误差分布直方图和实时统计数据更新
- **多线程架构**: 使用QThread实现非阻塞的数据处理和界面更新
- **现代化界面**: 采用PySide6和QSS样式，界面美观易用

## 📁 项目结构

```
mold-surface-inspector/
├── app.py                   # 应用程序启动入口
├── main_window.py          # 主窗口类实现 - 核心UI逻辑
├── hardware_simulator.py  # 硬件模拟器 - QThread测量设备模拟
├── analysis_worker.py      # 误差分析工作线程 - 实时数据处理
├── config.py               # 配置管理模块
├── styles.py               # QSS样式管理模块  
├── data_manager.py         # 数据管理模块
├── generate_semicylinder.py # 半圆柱点云数据生成工具
├── test_simulation.py      # 硬件模拟测试脚本
├── test_functions.py       # UI功能测试脚本
├── comprehensive_test.py   # 综合测试脚本
├── requirements.txt        # 项目依赖配置
├── install.sh              # 环境安装脚本
├── run.sh                  # 便捷运行脚本
├── launch.sh              # 应用启动脚本
├── data/                   # 理论数据存储目录
│   └── semicylinder_pointcloud.csv
├── measurement_data/       # 测量数据输出目录
├── test_output/           # 测试输出目录
├── figures/               # 界面截图和图表
└── docs/                  # 📚 完整文档目录
    ├── README.md          # 详细项目说明
    ├── QUICK_START.md     # 快速上手指南
    ├── DEV_GUIDE.md       # 开发指南
    ├── API_REFERENCE.md   # API参考手册
    ├── ARCHITECTURE.md    # 技术架构文档
    ├── FUNCTIONS.md       # 功能详细说明
    ├── TROUBLESHOOTING.md # 故障排除指南
    ├── DOC_INDEX.md       # 文档导航索引
    ├── CHANGELOG.md       # 更新日志
    └── USER_COMMANDS.md   # 用户命令记录
```

## 📚 文档导航

本项目提供了完整的开发文档体系，帮助不同需求的开发者快速上手：

### 🎯 新手必读
- **[⚡ 快速上手指南](docs/QUICK_START.md)** - 15分钟快速了解项目
- **[🏠 项目功能说明](docs/FUNCTIONS.md)** - 详细的功能特性介绍
- **[📚 完整项目说明](docs/README.md)** - 更详细的项目介绍

### 🔧 开发人员
- **[📚 完整开发文档](docs/DEV_GUIDE.md)** - 全面的开发指南和规范
- **[📖 API 参考手册](docs/API_REFERENCE.md)** - 详细的类和方法说明
- **[🏗️ 技术架构文档](docs/ARCHITECTURE.md)** - 系统架构和设计决策

### 🔧 维护支持
- **[🛠️ 故障排除指南](docs/TROUBLESHOOTING.md)** - 常见问题和解决方案
- **[📋 更新日志](docs/CHANGELOG.md)** - 版本更新记录
- **[📖 文档导航](docs/DOC_INDEX.md)** - 完整文档索引

### 📋 项目跟踪
- **[📝 用户命令记录](docs/USER_COMMANDS.md)** - 项目发展历程和需求跟踪

### 🎯 按需阅读建议

| 你的角色 | 推荐阅读顺序 |
|---------|-------------|
| **新接手开发者** | README → [QUICK_START](docs/QUICK_START.md) → [DEV_GUIDE](docs/DEV_GUIDE.md) → [API_REFERENCE](docs/API_REFERENCE.md) |
| **功能了解者** | README → [FUNCTIONS](docs/FUNCTIONS.md) |
| **架构设计者** | README → [ARCHITECTURE](docs/ARCHITECTURE.md) → [DEV_GUIDE](docs/DEV_GUIDE.md) |
| **API使用者** | [API_REFERENCE](docs/API_REFERENCE.md) → [QUICK_START](docs/QUICK_START.md) |
| **运维人员** | README → [TROUBLESHOOTING](docs/TROUBLESHOOTING.md) |

## 🎯 技术特点

- **多线程架构**: 使用 QThread 实现硬件模拟和误差分析的并行处理
- **信号槽机制**: 基于 Qt 信号槽实现组件间的松耦合通信
- **实时数据流**: CSV文件监控和实时数据处理流水线
- **3D可视化**: 集成 matplotlib 实现理论点云和测量点的3D显示
- **模块化设计**: 清晰的功能模块划分，易于扩展和维护
- **坐标转换**: 支持柱坐标与笛卡尔坐标的精确转换
- **误差分析**: 实时计算统计指标（最大/最小/平均误差、标准差等）
- **响应式布局**: 支持窗口大小调整和界面自适应
- **现代化样式**: 使用 QSS 样式表实现美观的界面设计
- **完整中文支持**: 界面完全支持中文显示和注释

## 📄 许可证

本项目采用 MIT 许可证。

## 🤝 贡献

欢迎提交 Issues 和 Pull Requests！

---

> 💡 **提示**: 如需详细了解项目功能和开发指南，请查看 [docs/](docs/) 目录下的完整文档。