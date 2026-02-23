# 模具曲面精度分析系统

基于 Electron + Three.js 开发的桌面应用程序，配合 Python WebSocket 后端，用于模具表面精度的实时测量和 3D 可视化分析。

## 🚀 快速开始

### 环境要求

- Python 3.8+
- Node.js 16+
- conda 环境管理器（推荐）

### 安装和运行

#### 方式一：一键启动（推荐）

双击运行 `启动系统.bat`，将自动启动：
1. Modbus 仿真服务器（模拟 PLC 设备）
2. Electron 应用程序（3D 界面）

#### 方式二：手动启动

1. **安装 Python 依赖**
   ```bash
   conda activate inspector
   pip install -r requirements.txt
   ```

2. **安装 Electron 依赖**
   ```bash
   cd electron
   npm install
   ```

3. **启动 Modbus 仿真服务器**
   ```bash
   python modbus_sim_server.py
   ```

4. **启动 Electron 应用**
   ```bash
   cd electron
   npm start
   ```

## 🎯 使用流程

1. 在 Electron 界面输入 **PLC IP: 127.0.0.1**（仿真模式）
2. 点击 **"连接 PLC"** 按钮
3. 点击 **"开始"** 按钮进行扫描测量
4. 实时查看 3D 点云和扫描进度

## ✨ 核心功能

- **3D 实时可视化**: 基于 Three.js 的点云实时渲染
- **双探头扫描**: 支持 1# 和 2# 双探头同时采集
- **Modbus 通信**: 通过 Modbus TCP 协议与 PLC 通信
- **WebSocket 桥接**: Python 后端与 Electron 前端实时数据传输
- **硬件仿真**: 内置 Modbus 仿真服务器用于测试

## 📁 项目结构

```
mold-surface-inspector/
├── 启动系统.bat              # 一键启动脚本
├── start_modbus_sim.bat      # Modbus 仿真器启动脚本
├── start_electron.bat        # Electron 应用启动脚本
├── electron_ws_server.py     # WebSocket 服务器（后端核心）
├── modbus_sim_server.py      # Modbus TCP 仿真服务器
├── hardware_driver.py        # PLC 硬件驱动层
├── data_manager.py           # 数据管理模块
├── generate_semicylinder.py  # 点云数据生成工具
├── requirements.txt          # Python 依赖
├── electron/                 # Electron 前端
│   ├── main.js              # Electron 主进程
│   ├── preload.js           # 预加载脚本
│   ├── renderer.js          # 渲染进程（Three.js 3D）
│   ├── index.html           # 主界面
│   └── package.json         # Node.js 依赖
├── data/                     # 理论点云数据
│   └── semicylinder_pointcloud.csv
├── measurement_data/         # 测量数据输出
└── docs/                     # 文档目录
```

## 🔧 系统架构

```
┌──────────────────────────────────────────────────────────────┐
│                      Electron App                            │
│                    (Three.js 3D 可视化)                      │
└──────────────────────────┬───────────────────────────────────┘
                           │ WebSocket
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                  electron_ws_server.py                       │
│                   (Python WebSocket 服务器)                   │
└──────────────────────────┬───────────────────────────────────┘
                           │ Modbus TCP
                           ▼
┌──────────────────────────────────────────────────────────────┐
│              modbus_sim_server.py / 实际 PLC                 │
│                    (端口 502)                                │
└──────────────────────────────────────────────────────────────┘
```

## 📡 通信协议

- **WebSocket**: `ws://127.0.0.1:8765` - 前后端通信
- **Modbus TCP**: `127.0.0.1:502` - PLC 通信

详细协议说明请参考 [docs/PLC_PROTOCOL.md](docs/PLC_PROTOCOL.md)

## 测量设备原理

这是一个基于**圆柱坐标系**的接触式三维扫描设备：

### 坐标系统
- **X (轴向位置)**: 直线导轨滑块位置
- **θ (方位角)**: 旋转轴角度
- **r (径向距离)**: 千分表读数

### 扫描逻辑
1. **APPROACH**: 双探头移动到起始位置
2. **SCAN**: 旋转扫描采集数据
3. **STEP**: X 轴步进移动
4. 循环重复直到扫描完成

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issues 和 Pull Requests！
