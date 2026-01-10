# 模具曲面精度分析系统 - Electron 版本

基于 Electron + Three.js 的 3D 可视化前端，通过 WebSocket 与 Python 后端通信。

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    Electron 应用 (前端)                          │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │  index.html │  │ renderer.js  │  │     Three.js 场景      │  │
│  │   (UI 布局)  │  │ (WebSocket)  │  │   (点云/模型渲染)      │  │
│  └─────────────┘  └──────────────┘  └────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │ WebSocket (ws://127.0.0.1:8765)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│               Python WebSocket 服务器 (后端)                     │
│  ┌──────────────────────┐  ┌─────────────────────────────────┐  │
│  │  electron_ws_server  │  │       hardware_driver.py        │  │
│  │   (消息路由/扫描)     │  │      (PLCDriver Modbus)        │  │
│  └──────────────────────┘  └─────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │ Modbus TCP (Port 502)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                 PLC / 仿真服务器                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  modbus_sim_server.py (开发仿真) / 真实 PLC (192.168.1.100)│ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## 环境要求

- **Node.js**: >= 18.x
- **Python**: >= 3.10 (推荐使用 conda 环境)
- **操作系统**: Windows 10/11

## 快速开始

### 1. 安装依赖

**Node.js 依赖**（在普通 PowerShell 中运行，**不要激活 conda 环境**）：
```bash
cd electron
npm install
```

**Python 依赖**（在 conda 环境中运行）：
```bash
conda activate inspector
pip install pymodbus>=3.5.0 websockets>=12.0
```

### 2. 启动应用

#### 方法一：双击启动脚本（推荐）⭐

**一键启动**：
1. 双击运行 `启动系统.bat`
2. 自动启动 Modbus 仿真服务器和 Electron 应用

**分别启动**：
1. 双击 `start_modbus_sim.bat` - 启动仿真服务器
2. 双击 `start_electron.bat` - 启动 Electron 应用

#### 方法二：命令行启动

**终端 1 - 启动 Modbus 仿真服务器**：
```powershell
conda activate inspector
cd D:\work\code\mold-surface-inspector
python modbus_sim_server.py
```

**终端 2 - 启动 Electron 应用**（在新的 PowerShell 窗口，**不要激活 conda**）：
```powershell
# 方式 A：刷新环境变量后启动（推荐）
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
cd D:\work\code\mold-surface-inspector\electron
npm start

# 方式 B：或者直接使用完整路径
& "C:\Program Files\nodejs\npm.cmd" start
```

#### 连接配置（仿真模式）

在应用界面中：
1. PLC IP: `127.0.0.1`
2. 端口: `502`
3. 点击"连接 PLC"按钮

#### 连接真实 PLC

在应用界面中：
1. PLC IP: `192.168.1.100`（或实际 PLC IP）
2. 端口: `502`
3. 点击"连接 PLC"按钮

### 3. 使用说明

1. **启动后会看到连接配置界面**
   - 填写 PLC 的 IP 地址和端口号
   - 仿真模式使用 `127.0.0.1:502`
   - 真实 PLC 使用实际 IP，如 `192.168.1.100:502`

2. **点击"连接 PLC"**
   - 系统会自动启动 Python WebSocket 服务器
   - 连接成功后进入主界面

3. **开始测量**
   - 设置扫描参数（X 轴范围、步进、旋转范围）
   - 点击"开始扫描"
   - 实时查看 3D 点云和误差数据

4. **断开连接**
   - 点击"断开连接"按钮
   - 自动停止所有服务并返回配置界面

## 通信协议

### WebSocket 消息格式

#### 客户端 → 服务器 (命令)

```json
// 开始扫描
{
    "cmd": "start_scan",
    "xMin": 0,
    "xMax": 100,
    "xStep": 5,
    "rotMin": 0,
    "rotMax": 180
}

// 停止扫描
{ "cmd": "stop_scan" }

// 设备复位
{ "cmd": "reset" }

// 手动移动轴
{
    "cmd": "move_axis",
    "axis": 1,      // 1=X1, 2=X2, 3=旋转
    "target": 50.0, // 目标位置 (mm 或 度)
    "speed": 30     // 速度 (可选)
}
```

#### 服务器 → 客户端 (数据)

```json
// 位置更新 (10Hz)
{
    "type": "position",
    "x1": 50.0,
    "x2": 0.0,
    "rot": 45.0
}

// 测量点数据
{
    "type": "point",
    "seq": 1,
    "x": 50.0,
    "y": 35.36,
    "z": 35.36,
    "theoretical": 50.0,
    "error": 0.023
}

// 状态更新
{
    "type": "status",
    "scanning": true,
    "text": "扫描中..."
}
```

## 项目结构

```
electron/
├── package.json      # Node.js 项目配置
├── main.js           # Electron 主进程
├── preload.js        # 预加载脚本 (IPC 桥接)
├── index.html        # UI 界面
├── renderer.js       # 渲染进程 (Three.js + WebSocket)
└── README.md         # 本文档

../
├── electron_ws_server.py  # WebSocket 服务器
├── hardware_driver.py     # PLC Modbus 驱动
├── modbus_sim_server.py   # Modbus 仿真服务器
└── requirements.txt       # Python 依赖
```

## 系统特点

### 🎯 双探头检测系统
- **1#探头（绿色）**: 从左侧(-300mm)向中心(60mm)移动
- **2#探头（蓝色）**: 从右侧(300mm)向中心(-60mm)移动
- **重叠区域**: -60mm ~ 60mm，两探头同时测量
- **旋转轴**: 0° ~ 170°，带动探头同步旋转

### 🔧 技术架构
- **前端**: Electron + Three.js (双点云 3D 渲染)
- **后端**: Python + pymodbus + WebSocket (双探头协同控制)
- **通信**: WebSocket 实时双向通信 (低延迟 < 5ms)

### 📊 扫描流程

1. **APPROACH 阶段**: 两探头同时移动到起始位置
   - 1#探头 → -300mm（左起点）
   - 2#探头 → +300mm（右起点）

2. **SCAN 阶段**: 旋转扫描
   - 旋转轴从 0° → 170°，步进可配置
   - 每个角度，两探头同时采集数据

3. **STEP 阶段**: X轴进给
   - 1#探头向右移动一步
   - 2#探头向左移动一步

4. **循环** 2-3 步，直到到达重叠区域终点

### 📈 数据可视化
- **双色点云**: 绿色(1#探头) + 蓝色(2#探头)
- **颜色编码**: 绿色=合格(≤0.05mm), 黄色=注意(0.05-0.1mm), 红色=超差(>0.1mm)
- **理论模型**: 半透明半圆柱，跟随旋转角度转动
- **视角控制**: 前视/俯视/侧视/等轴测 快速切换

## 开发指南

### 修改 Python 环境路径

如果使用不同的 Python 环境，需要修改 `main.js` 中的路径：

```javascript
// main.js 第 12 行
const pythonPath = 'C:\\path\\to\\your\\python.exe';
```

### 调试

- **Electron 调试**: 按 `Ctrl+Shift+I` 打开开发者工具
- **Python 日志**: WebSocket 服务器会输出详细日志到控制台

## 常见问题

### ❌ npm: 无法将"npm"项识别为 cmdlet
**原因**: conda 激活后会修改 PATH 环境变量，覆盖了系统的 npm 路径  

**解决方法（3选1）**:
1. **使用启动脚本**（最简单）：双击 `start_electron.bat`
2. **刷新环境变量**：在 PowerShell 中运行
   ```powershell
   $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
   npm start
   ```
3. **新建 PowerShell 窗口**（不激活 conda）：
   - 关闭当前终端
   - 打开新的 PowerShell（不运行 `conda activate`）
   - `cd D:\work\code\mold-surface-inspector\electron`
   - `npm start`

### ❌ ModuleNotFoundError: No module named 'websockets'
**原因**: Python 依赖未安装  
**解决方法**:
```powershell
conda activate inspector
pip install websockets pymodbus
```

### ❌ WebSocket 连接失败 / 启动超时
**原因**: Modbus 仿真服务器未启动  
**解决方法**:
```powershell
# 在另一个终端启动
conda activate inspector
python modbus_sim_server.py
```

### ❌ PLC 连接失败
1. 确保网络连通: `ping 192.168.1.100`
2. 检查 Modbus TCP 端口 502 是否开放
3. 仿真模式下确认 `modbus_sim_server.py` 正在运行

### ❌ 点云不显示
1. 检查浏览器控制台（Ctrl+Shift+I）是否有 WebGL 错误
2. 确认 WebSocket 消息正常接收
3. 尝试刷新页面或重启应用

## 技术参数

### 机械参数
- **模具半径**: 200mm
- **1#探头行程**: -300mm → +60mm
- **2#探头行程**: +300mm → -60mm
- **旋转范围**: 0° → 170°
- **重叠区域**: -60mm ~ +60mm

### 通信协议
- **Modbus TCP**: 端口 502
- **WebSocket**: 端口 8765
- **位置精度**: 0.01mm
- **更新频率**: 10Hz
3. 尝试刷新页面或重启应用
