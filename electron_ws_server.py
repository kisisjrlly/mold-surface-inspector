"""
模具曲面精度分析系统 - WebSocket 服务器
双探头检测系统：1#探头(左->中) 和 2#探头(右->中)

基于 simulation-of-device.html 的扫描逻辑
"""

import asyncio
import json
import logging
import math
import time
import sys
from typing import Set, Dict, Any, Optional

import websockets

from hardware_driver import PLCDriver

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ws_server')


class DualProbeScanServer:
    """
    双探头检测 WebSocket 服务器
    
    扫描逻辑 (参照 simulation-of-device.html):
    1. APPROACH 阶段: 两个探头同时移动到起始位置
       - 1#探头: 移动到 X1_START (-300mm)
       - 2#探头: 移动到 X2_START (300mm)
    2. SCAN 阶段: 旋转扫描
       - 旋转轴从 0° 转到 170°，两个探头同时采集数据
       - 到达角度极限后进入 STEP 阶段
    3. STEP 阶段: X轴进给
       - 1#探头: 向右移动一步 (+STEP_X)
       - 2#探头: 向左移动一步 (-STEP_X)
       - 移动完成后返回 SCAN 阶段，旋转方向反转
    4. 重复 SCAN -> STEP 直到:
       - 1#探头到达 X1_END (60mm)
       - 2#探头到达 X2_END (-60mm)
    """
    
    # 扫描参数 (与 simulation-of-device.html 一致)
    X1_START = -300.0   # mm，1#探头起始位置（左侧）
    X1_END = 60.0       # mm，1#探头结束位置（中心略右）
    X2_START = 300.0    # mm，2#探头起始位置（右侧）
    X2_END = -60.0      # mm，2#探头结束位置（中心略左）
    
    STEP_X = 10.0       # mm，X轴步进
    MAX_ANGLE = 170.0   # 度，最大旋转角度
    ANGLE_STEP = 2.5    # 度，旋转步进（采样间隔）
    
    # 模具参数
    MOLD_RADIUS = 200.0  # mm，模具半径（与 HTML 中一致）
    
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
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
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
        """定期广播设备位置 (10Hz)"""
        while True:
            try:
                if self.clients:
                    positions = self.plc_driver.get_all_positions()
                    await self.broadcast({
                        'type': 'position',
                        'x1': positions.get('x1', 0),
                        'x2': positions.get('x2', 0),
                        'rot': positions.get('rotation', 0),
                        'phase': self.phase,
                        'pointCount': self.point_count
                    })
            except Exception as e:
                logger.error(f"Error broadcasting positions: {e}")
            await asyncio.sleep(0.1)
    
    async def send_status(self, websocket):
        """发送当前状态"""
        positions = self.plc_driver.get_all_positions()
        await websocket.send(json.dumps({
            'type': 'status',
            'scanning': self.scanning,
            'phase': self.phase,
            'x1': positions.get('x1', 0),
            'x2': positions.get('x2', 0),
            'rot': positions.get('rotation', 0),
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
            
            # ========== SCAN-STEP 循环 ==========
            while self.scanning:
                # === SCAN 阶段: 旋转扫描 ===
                self.phase = 'SCAN'
                await self.broadcast({'type': 'status', 'scanning': True, 'phase': 'SCAN', 'text': '翻转扫描中...'})
                
                # 确定旋转方向和目标
                if self.scan_dir == 1:
                    target_angle = self.MAX_ANGLE
                else:
                    target_angle = 0.0
                
                # 逐步旋转并采样
                while self.scanning:
                    # 移动旋转轴
                    self.plc_driver.move_axis(3, self.current_angle, 20)
                    await asyncio.sleep(0.05)  # 50ms 采样间隔
                    
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
                    await self.broadcast({
                        'type': 'status',
                        'scanning': False,
                        'phase': 'COMPLETE',
                        'text': f'检测完成，共采集 {self.point_count} 点'
                    })
                    logger.info(f"Scan completed, total points: {self.point_count}")
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
        
        根据 simulation-of-device.html 中的几何计算:
        - 1#探头 (probe=1): 在上方，测量上半圆柱
        - 2#探头 (probe=2): 在下方，测量下半圆柱
        """
        import random
        
        rad = math.radians(angle)
        
        # 探头方向偏移
        # 1#探头测量上半部分 (sign=1), 2#探头测量下半部分 (sign=-1)
        sign = 1 if probe == 1 else -1
        
        # 理论位置 (半圆柱表面)
        theoretical_y = sign * self.MOLD_RADIUS * math.cos(rad)
        theoretical_z = sign * self.MOLD_RADIUS * math.sin(rad)
        
        # 模拟测量误差 (±0.05mm 高斯分布)
        error = random.gauss(0, 0.03)
        measured_r = self.MOLD_RADIUS + error
        
        measured_y = sign * measured_r * math.cos(rad)
        measured_z = sign * measured_r * math.sin(rad)
        
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
            'theoretical': self.MOLD_RADIUS,
            'error': error
        })
    
    async def _wait_all_axes_stop(self, timeout: float = 30.0):
        """等待所有轴停止移动"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if not self.scanning:
                return False
            
            status = self.plc_driver.get_machine_status()
            
            x1_moving = status.get('x1_moving', False)
            x2_moving = status.get('x2_moving', False)
            rot_moving = status.get('rotation_moving', False)
            
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
