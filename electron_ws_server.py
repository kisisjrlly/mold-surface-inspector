"""
模具曲面精度分析系统 - WebSocket 服务器
双探头检测系统：1#探头(左->中) 和 2#探头(右->中)

基于 simulation-of-device.html 的扫描逻辑
支持：
1. 真实 PLC 连接模式 - 从 PLC 读取探头测量数据
2. 理论点云加载与误差计算
"""

import asyncio
import json
import logging
import math
import time
import sys
import os
from typing import Set, Dict, Any, Optional, List

import websockets
import numpy as np

from hardware_driver import PLCDriver

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
# 设置控制台输出编码为UTF-8
if sys.stdout.encoding != 'utf-8':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

logger = logging.getLogger('ws_server')


class DualProbeScanServer:
    """
    双探头检测 WebSocket 服务器
    
    扫描逻辑:
    1. APPROACH 阶段: 两个探头同时移动到起始位置
    2. SCAN 阶段: 旋转扫描，两个探头同时采集数据
    3. STEP 阶段: X轴进给
    4. 重复 SCAN -> STEP 直到完成
    """
    
    # 扫描参数 - 根据实际曲面尺寸调整
    # 实际曲面尺寸: X: 1409.632mm, Y: 796.111mm, Z: 599.526mm
    X1_START = -700.0   # mm，1#探头起始位置（左侧）
    X1_END = 100.0      # mm，1#探头结束位置（中心略右）
    X2_START = 700.0    # mm，2#探头起始位置（右侧）
    X2_END = -100.0     # mm，2#探头结束位置（中心略左）
    
    STEP_X = 20.0       # mm，X轴步进（增大以减少扫描时间）
    MAX_ANGLE = 170.0   # 度，最大旋转角度
    ANGLE_STEP = 5.0    # 度，旋转步进（增大以减少采样点数和卡顿）
    
    # 模具参数 - 根据实际曲面尺寸
    MOLD_RADIUS = 400.0  # mm，模具半径约为Y/2
    
    def __init__(self, plc_host: str = '127.0.0.1', plc_port: int = 502):
        self.plc_driver = PLCDriver(plc_host, plc_port)
        self.clients: Set = set()
        
        # 扫描状态
        self.scanning = False
        self.scan_task: Optional[asyncio.Task] = None
        self.phase = 'IDLE'  # IDLE, APPROACH, SCAN, STEP
        self.scan_dir = 1    # 1=正向(0->170), -1=反向(170->0)
        self.current_angle = 0.0
        self.point_count = 0
        
        # 理论点云数据（用于误差计算）
        self.theoretical_data: Optional[np.ndarray] = None
        self.theoretical_loaded = False
        
    def load_theoretical_data(self, file_path: str) -> bool:
        """
        加载理论点云数据
        
        支持两种格式：
        1. CSV 文件（包含 x, y, z 列）
        2. Python 文件（包含 faces 列表）
        
        Args:
            file_path: 理论点云文件路径
            
        Returns:
            bool: 是否加载成功
        """
        try:
            if file_path.endswith('.csv'):
                import pandas as pd
                df = pd.read_csv(file_path)
                # 支持多种列名格式
                if 'x_mm' in df.columns:
                    self.theoretical_data = df[['x_mm', 'y_mm', 'z_mm']].values
                elif 'x' in df.columns:
                    self.theoretical_data = df[['x', 'y', 'z']].values
                else:
                    logger.error(f"CSV 文件缺少必要的坐标列: {df.columns.tolist()}")
                    return False
                    
            elif file_path.endswith('.py'):
                # 解析 Python 文件中的 faces 数据
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                # 执行代码获取 faces 变量
                local_vars = {}
                exec(content, {}, local_vars)
                if 'faces' in local_vars:
                    faces = local_vars['faces']
                    # faces 是一个点列表 [[x,y,z], [x,y,z], ...]
                    # 直接转换为 numpy 数组并去重
                    all_points = np.array(faces)
                    # 去除重复点
                    self.theoretical_data = np.unique(all_points, axis=0)
                    logger.info(f"从 Python 文件加载了 {len(self.theoretical_data)} 个唯一点（原始 {len(faces)} 个点）")
                else:
                    logger.error("Python 文件中没有找到 'faces' 变量")
                    return False
            else:
                logger.error(f"不支持的文件格式: {file_path}")
                return False
            
            self.theoretical_loaded = True
            logger.info(f"成功加载理论点云: {len(self.theoretical_data)} 个点")
            return True
            
        except Exception as e:
            logger.error(f"加载理论点云失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def find_nearest_theoretical_point(self, x: float, angle_deg: float, probe: int) -> Optional[Dict]:
        """
        根据当前位置和角度，在理论点云中找到最近的点
        
        Args:
            x: X 轴位置 (mm)
            angle_deg: 旋转角度 (度)
            probe: 探头编号 (1 或 2)
            
        Returns:
            最近点的信息 {'x', 'y', 'z', 'radius', 'distance'}
        """
        if not self.theoretical_loaded or self.theoretical_data is None:
            return None
        
        # 将角度转换为弧度
        rad = math.radians(angle_deg)
        
        # 计算当前探头在模具表面的理论位置
        # 1#探头测量上半部分，2#探头测量下半部分
        sign = 1 if probe == 1 else -1
        
        # 在理论点云中搜索最近的点
        # 首先按 X 坐标筛选附近的点（±5mm 范围）
        x_mask = np.abs(self.theoretical_data[:, 0] - x) < 5.0
        nearby_points = self.theoretical_data[x_mask]
        
        if len(nearby_points) == 0:
            return None
        
        # 计算每个点的角度
        # 角度 = atan2(z, y)
        point_angles = np.arctan2(nearby_points[:, 2], nearby_points[:, 1])
        
        # 找到角度最接近的点
        target_angle = rad * sign
        angle_diff = np.abs(point_angles - target_angle)
        nearest_idx = np.argmin(angle_diff)
        
        nearest_point = nearby_points[nearest_idx]
        
        # 计算理论半径
        theoretical_radius = math.sqrt(nearest_point[1]**2 + nearest_point[2]**2)
        
        return {
            'x': nearest_point[0],
            'y': nearest_point[1],
            'z': nearest_point[2],
            'radius': theoretical_radius,
            'distance': angle_diff[nearest_idx]
        }
        
    async def start(self, host: str = '127.0.0.1', port: int = 8765):
        """启动 WebSocket 服务器"""
        logger.info(f"Starting WebSocket server on ws://{host}:{port}")
        
        # 连接 PLC
        if self.plc_driver.connect():
            logger.info("PLC connected")
        else:
            logger.warning("PLC connection failed, running in simulation mode")
        
        # 启动服务器
        async with websockets.serve(self.handler, host, port):
            logger.info("WebSocket server started")
            broadcast_task = asyncio.create_task(self.broadcast_positions())
            await asyncio.Future()
    
    async def handler(self, websocket):
        """处理客户端连接"""
        self.clients.add(websocket)
        client_id = id(websocket)
        logger.info(f"Client {client_id} connected, total: {len(self.clients)}")
        
        try:
            async for message in websocket:
                await self.process_message(websocket, message)
        except websockets.ConnectionClosed:
            pass
        finally:
            self.clients.discard(websocket)
            logger.info(f"Client {client_id} disconnected, total: {len(self.clients)}")
    
    async def process_message(self, websocket, message: str):
        """处理客户端消息"""
        try:
            data = json.loads(message)
            cmd = data.get('cmd')
            
            if cmd == 'start_scan':
                await self.start_scan(data)
            elif cmd == 'stop_scan':
                await self.stop_scan()
            elif cmd == 'reset':
                await self.reset_machine()
            elif cmd == 'move_axis':
                await self.move_axis(data)
            elif cmd == 'get_status':
                await self.send_status(websocket)
            elif cmd == 'load_theoretical':
                await self.handle_load_theoretical(websocket, data)
            elif cmd == 'write_coil':
                await self.handle_write_coil(data)
            elif cmd == 'write_register':
                await self.handle_write_register(data)
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    async def handle_write_coil(self, data: Dict[str, Any]):
        """处理写线圈命令（手动操作）"""
        address = data.get('address')
        value = data.get('value', False)
        
        if address is None:
            logger.error("写线圈命令缺少地址")
            return
        
        try:
            success = self.plc_driver.client.write_coil(address, value, device_id=1)
            
            # 增强日志：显示点动操作
            coil_name = {
                1000: "1#X轴点动前进", 1001: "1#X轴点动后退",
                1100: "2#X轴点动前进", 1101: "2#X轴点动后退",
                1200: "旋转轴点动正转", 1201: "旋转轴点动反转"
            }.get(address, f"线圈{address}")
            
            logger.info(f"写{coil_name} = {value}, 结果: {success}")
        except Exception as e:
            logger.error(f"写线圈失败: {e}")
    
    async def handle_write_register(self, data: Dict[str, Any]):
        """处理写寄存器命令（手动操作）"""
        address = data.get('address')
        value = data.get('value', 0)
        
        if address is None:
            logger.error("写寄存器命令缺少地址")
            return
        
        try:
            # DInt 类型需要写入2个寄存器（Little Endian）
            low = value & 0xFFFF
            high = (value >> 16) & 0xFFFF
            success = self.plc_driver.client.write_registers(address, [low, high], device_id=1)
            
            # 增强日志：显示速度设置
            reg_name = {
                41188: "1#X轴点动速度", 41190: "1#X轴动作速度",
                41288: "2#X轴点动速度", 41290: "2#X轴动作速度",
                41390: "旋转轴动作速度",
                41212: "1#X轴目标位置", 41312: "2#X轴目标位置", 41412: "旋转轴目标位置"
            }.get(address, f"寄存器{address}")
            
            logger.info(f"写{reg_name} = {value} (L={low}, H={high}), 结果: {success}")
        except Exception as e:
            logger.error(f"写寄存器失败: {e}")
    
    async def handle_load_theoretical(self, websocket, data: Dict[str, Any]):
        """处理加载理论点云请求"""
        file_path = data.get('filePath', '')
        
        if not file_path:
            await websocket.send(json.dumps({
                'type': 'theoretical_load_result',
                'success': False,
                'message': '未指定文件路径'
            }))
            return
        
        success = self.load_theoretical_data(file_path)
        
        if success:
            # 计算点云统计信息
            x_min, x_max = self.theoretical_data[:, 0].min(), self.theoretical_data[:, 0].max()
            y_min, y_max = self.theoretical_data[:, 1].min(), self.theoretical_data[:, 1].max()
            z_min, z_max = self.theoretical_data[:, 2].min(), self.theoretical_data[:, 2].max()
            
            await self.broadcast({
                'type': 'theoretical_load_result',
                'success': True,
                'message': f'成功加载 {len(self.theoretical_data)} 个理论点',
                'pointCount': len(self.theoretical_data),
                'bounds': {
                    'x': [float(x_min), float(x_max)],
                    'y': [float(y_min), float(y_max)],
                    'z': [float(z_min), float(z_max)]
                },
                # 发送理论点云数据用于 3D 显示
                'points': self.theoretical_data.tolist()
            })
        else:
            await websocket.send(json.dumps({
                'type': 'theoretical_load_result',
                'success': False,
                'message': '加载理论点云失败，请检查文件格式'
            }))
    
    async def broadcast(self, message: Dict[str, Any]):
        """向所有客户端广播消息"""
        if not self.clients:
            return
        msg_str = json.dumps(message)
        await asyncio.gather(
            *[client.send(msg_str) for client in self.clients],
            return_exceptions=True
        )
    
    async def broadcast_positions(self):
        """定期广播设备位置 (5Hz，减少频率以降低CPU负担)"""
        probe_log_counter = 0  # 计数器，每10次打印一次探头日志
        while True:
            try:
                if self.clients:
                    positions = self.plc_driver.get_all_positions()
                    probes = self.plc_driver.get_probe_measurements()
                    
                    # 每2秒打印一次探头数据（10次 * 200ms = 2秒）
                    probe_log_counter += 1
                    if probe_log_counter >= 10:
                        probe_log_counter = 0
                        raw1 = probes.get('raw1', 'N/A')
                        raw2 = probes.get('raw2', 'N/A')
                        logger.info(f"探头数据: 1#={probes.get('probe1', 0):.2f}mm (raw={raw1}), 2#={probes.get('probe2', 0):.2f}mm (raw={raw2})")
                    
                    await self.broadcast({
                        'type': 'position',
                        'x1': positions.get('x1', 0),
                        'x2': positions.get('x2', 0),
                        'rot': positions.get('rotation', 0),
                        'probe1': probes.get('probe1', 0),
                        'probe2': probes.get('probe2', 0),
                        'phase': self.phase,
                        'pointCount': self.point_count
                    })
            except Exception as e:
                logger.error(f"Error broadcasting positions: {e}")
            await asyncio.sleep(0.2)  # 200ms，5Hz
    
    async def send_status(self, websocket):
        """发送当前状态"""
        positions = self.plc_driver.get_all_positions()
        probes = self.plc_driver.get_probe_measurements()
        await websocket.send(json.dumps({
            'type': 'status',
            'scanning': self.scanning,
            'phase': self.phase,
            'x1': positions.get('x1', 0),
            'x2': positions.get('x2', 0),
            'rot': positions.get('rotation', 0),
            'probe1': probes.get('probe1', 0),
            'probe2': probes.get('probe2', 0),
            'pointCount': self.point_count
        }))
    
    async def start_scan(self, params: Dict[str, Any]):
        """开始双探头扫描"""
        if self.scanning:
            logger.warning("Scan already in progress")
            return
        
        # 可选参数覆盖
        self.STEP_X = params.get('stepX', 10.0)
        self.MAX_ANGLE = params.get('maxAngle', 170.0)
        self.ANGLE_STEP = params.get('angleStep', 2.5)
        
        self.scanning = True
        self.point_count = 0
        self.scan_task = asyncio.create_task(self.dual_probe_scan_loop())
        
        await self.broadcast({
            'type': 'status',
            'scanning': True,
            'phase': 'APPROACH',
            'text': '正在归位...'
        })
        
        logger.info(f"Dual-probe scan started: step={self.STEP_X}mm, maxAngle={self.MAX_ANGLE}°")
    
    async def stop_scan(self):
        """停止扫描"""
        self.scanning = False
        if self.scan_task:
            self.scan_task.cancel()
            try:
                await self.scan_task
            except asyncio.CancelledError:
                pass
            self.scan_task = None
        
        self.phase = 'IDLE'
        await self.broadcast({
            'type': 'status',
            'scanning': False,
            'phase': 'IDLE',
            'text': '已停止'
        })
        logger.info("Scan stopped")
    
    async def dual_probe_scan_loop(self):
        """
        双探头扫描主循环
        实现与 simulation-of-device.html 完全一致的扫描逻辑
        """
        try:
            # ========== APPROACH 阶段 ==========
            self.phase = 'APPROACH'
            await self.broadcast({'type': 'status', 'scanning': True, 'phase': 'APPROACH', 'text': 'X轴归位中...'})
            
            # 两个探头同时移动到起始位置
            logger.info(f"Moving probes to start: 1#->{self.X1_START}mm, 2#->{self.X2_START}mm")
            self.plc_driver.move_axis(1, self.X1_START, 50)  # 1#探头到左侧
            self.plc_driver.move_axis(2, self.X2_START, 50)  # 2#探头到右侧
            self.plc_driver.move_axis(3, 0, 30)              # 旋转轴归零
            
            await self._wait_all_axes_stop()
            
            # 初始化扫描状态
            current_x1 = self.X1_START
            current_x2 = self.X2_START
            self.current_angle = 0.0
            self.scan_dir = 1
            step_number = 0
            
            # 计算预计总步数
            total_steps = int(min(self.X1_END - self.X1_START, self.X2_START - self.X2_END) / self.STEP_X)
            logger.info(f"Starting scan: {total_steps} steps expected, ~{total_steps * 10}s estimated time")
            
            # ========== SCAN-STEP 循环 ==========
            while self.scanning:
                step_number += 1
                # === SCAN 阶段: 旋转扫描 ===
                self.phase = 'SCAN'
                logger.info(f"Step {step_number}/{total_steps}: SCAN phase, direction={'CW' if self.scan_dir == 1 else 'CCW'}")
                await self.broadcast({
                    'type': 'status', 
                    'scanning': True, 
                    'phase': 'SCAN', 
                    'text': f'扫描中... ({step_number}/{total_steps})'
                })
                
                # 确定旋转方向和目标
                if self.scan_dir == 1:
                    target_angle = self.MAX_ANGLE
                else:
                    target_angle = 0.0
                
                # 逐步旋转并采样
                while self.scanning:
                    # 移动旋转轴
                    self.plc_driver.move_axis(3, self.current_angle, 20)
                    await asyncio.sleep(0.2)  # 200ms 采样间隔，减少CPU负担
                    
                    # 获取实际位置
                    positions = self.plc_driver.get_all_positions()
                    actual_x1 = positions.get('x1', current_x1)
                    actual_x2 = positions.get('x2', current_x2)
                    actual_angle = positions.get('rotation', self.current_angle)
                    
                    # 生成测量点 (两个探头同时采样)
                    await self._generate_point(actual_x1, actual_angle, probe=1)  # 1#探头（绿色）
                    await self._generate_point(actual_x2, actual_angle, probe=2)  # 2#探头（蓝色）
                    
                    # 更新角度
                    self.current_angle += self.ANGLE_STEP * self.scan_dir
                    
                    # 检查是否到达角度极限
                    if self.scan_dir == 1 and self.current_angle >= self.MAX_ANGLE:
                        self.current_angle = self.MAX_ANGLE
                        break
                    elif self.scan_dir == -1 and self.current_angle <= 0:
                        self.current_angle = 0
                        break
                
                if not self.scanning:
                    break
                
                # === STEP 阶段: X轴进给 ===
                # 计算下一步目标位置
                next_x1 = current_x1 + self.STEP_X  # 1#探头向右移动
                next_x2 = current_x2 - self.STEP_X  # 2#探头向左移动
                
                # 检查是否完成扫描
                if next_x1 > self.X1_END or next_x2 < self.X2_END:
                    # 扫描完成
                    self.phase = 'COMPLETE'
                    logger.info(f"Scan completed! Total points: {self.point_count}")
                    logger.info(f"Final positions: X1={current_x1}mm, X2={current_x2}mm")
                    await self.broadcast({
                        'type': 'status',
                        'scanning': False,
                        'phase': 'COMPLETE',
                        'text': f'✅ 扫描完成！共采集 {self.point_count} 点',
                        'pointCount': self.point_count
                    })
                    self.scanning = False
                    break
                
                # 进给移动
                self.phase = 'STEP'
                await self.broadcast({'type': 'status', 'scanning': True, 'phase': 'STEP', 'text': 'X轴进给...'})
                
                logger.info(f"Step move: 1#->{next_x1}mm, 2#->{next_x2}mm")
                self.plc_driver.move_axis(1, next_x1, 30)
                self.plc_driver.move_axis(2, next_x2, 30)
                
                await self._wait_all_axes_stop()
                
                current_x1 = next_x1
                current_x2 = next_x2
                
                # 反转旋转方向
                self.scan_dir *= -1
            
        except asyncio.CancelledError:
            logger.info("Scan cancelled")
            raise
        except Exception as e:
            logger.error(f"Scan error: {e}")
            self.scanning = False
            await self.broadcast({
                'type': 'status',
                'scanning': False,
                'phase': 'ERROR',
                'text': f'扫描错误: {e}'
            })
    
    async def _generate_point(self, x: float, angle: float, probe: int):
        """
        生成测量点数据
        
        从 PLC 读取真实的探头测量数据（或仿真数据），
        与理论点云对比计算误差。
        
        Args:
            x: 当前 X 轴位置 (mm)
            angle: 当前旋转角度 (度)
            probe: 探头编号 (1=绿色探头, 2=蓝色探头)
        """
        rad = math.radians(angle)
        
        # 从 PLC 读取探头测量数据
        probe_data = self.plc_driver.get_probe_measurements()
        
        if probe == 1:
            measured_radius = probe_data.get('probe1', self.MOLD_RADIUS)
        else:
            measured_radius = probe_data.get('probe2', self.MOLD_RADIUS)
        
        # 计算测量点的 3D 坐标（柱坐标转笛卡尔坐标）
        # 半圆柱开口向上，角度从0°到170°
        # 0° 时探头在前方(Z正向)，90°时探头在正上方(Y正向)，170°时探头在后方
        # Y = radius * sin(angle)  (向上为正)
        # Z = radius * cos(angle)  (向前为正)
        measured_y = measured_radius * math.sin(rad)
        measured_z = measured_radius * math.cos(rad)
        
        # 计算理论值和误差
        theoretical_radius = self.MOLD_RADIUS  # 默认理论半径
        
        # 如果有理论点云数据，尝试找到最近的理论点
        if self.theoretical_loaded:
            nearest = self.find_nearest_theoretical_point(x, angle, probe)
            if nearest:
                theoretical_radius = nearest['radius']
        
        # 计算误差（测量值 - 理论值）
        error = measured_radius - theoretical_radius
        
        self.point_count += 1
        
        # 发送点数据
        await self.broadcast({
            'type': 'point',
            'seq': self.point_count,
            'probe': probe,  # 1=绿色探头, 2=蓝色探头
            'x': x,
            'y': measured_y,
            'z': measured_z,
            'angle': angle,
            'measuredRadius': measured_radius,
            'theoretical': theoretical_radius,
            'error': error
        })
    
    async def _wait_all_axes_stop(self, timeout: float = 30.0):
        """等待所有轴停止移动"""
        start_time = time.time()
        
        # 首先等待一小段时间，确保运动指令已发送并开始执行
        await asyncio.sleep(0.2)
        
        while time.time() - start_time < timeout:
            if not self.scanning:
                return False
            
            status = self.plc_driver.get_machine_status()
            
            x1_moving = status.get('x1_moving', False)
            x2_moving = status.get('x2_moving', False)
            rot_moving = status.get('rotation_moving', False)
            
            # 调试日志
            if x1_moving or x2_moving or rot_moving:
                logger.debug(f"Axes moving: X1={x1_moving}, X2={x2_moving}, Rot={rot_moving}")
            
            if not x1_moving and not x2_moving and not rot_moving:
                return True
            
            await asyncio.sleep(0.1)
        
        logger.warning("Axes movement timeout")
        return False
    
    async def move_axis(self, params: Dict[str, Any]):
        """手动移动轴"""
        axis = params.get('axis', 1)
        target = params.get('target', 0)
        speed = params.get('speed', 30)
        
        logger.info(f"Manual move: axis={axis}, target={target}, speed={speed}")
        self.plc_driver.move_axis(axis, target, speed)
        
        await self.broadcast({
            'type': 'status',
            'text': f'移动轴 {axis} 到 {target}'
        })
    
    async def reset_machine(self):
        """复位设备到原点"""
        logger.info("Resetting machine to home position")
        
        await self.stop_scan()
        
        # 移动到原点
        self.plc_driver.move_axis(1, -300, 50)  # 1#探头回左侧
        self.plc_driver.move_axis(2, 300, 50)   # 2#探头回右侧
        self.plc_driver.move_axis(3, 0, 30)     # 旋转轴归零
        
        self.point_count = 0
        self.current_angle = 0
        
        await self.broadcast({
            'type': 'status',
            'phase': 'RESET',
            'text': '复位中...',
            'pointCount': 0
        })


async def main():
    """主入口"""
    plc_host = '127.0.0.1'
    plc_port = 502
    
    if len(sys.argv) > 1:
        plc_host = sys.argv[1]
    if len(sys.argv) > 2:
        plc_port = int(sys.argv[2])
    
    server = DualProbeScanServer(plc_host, plc_port)
    await server.start()


if __name__ == '__main__':
    asyncio.run(main())
