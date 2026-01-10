import time
import math
import random
import csv
import logging
from PySide6.QtCore import QThread, Signal, QObject
from hardware_driver import PLCDriver

# 配置日志
logger = logging.getLogger("DataCollector")

class DataCollector(QThread):
    """
    数据采集与运动控制线程
    1. 通过 PLCDriver 控制 PLC 运动
    2. 实时读取 PLC 坐标 (X, Angle)
    3. 模拟传感器数据 (Z) - 因为协议中没有传感器读数
    4. 将数据写入 CSV 供分析线程使用
    """
    progress_update = Signal(int)
    status_update = Signal(str)
    position_update = Signal(float, float) # X, Angle
    finished = Signal()
    error_occurred = Signal(str)

    def __init__(self, plc_ip='127.0.0.1', data_file='measurement_data/live_measurement.csv'):
        super().__init__()
        self.plc = PLCDriver(ip=plc_ip)
        self.data_file = data_file
        self.is_running = False
        self.is_paused = False
        
        # 扫描参数
        self.x_start = 0.0
        self.x_end = 100.0
        self.x_step = 10.0
        self.scan_speed = 1000 # deg/min (approx)
        
        # 理论模型参数 (用于模拟传感器数据)
        self.radius = 50.0 # 模具半径

    def connect_device(self):
        return self.plc.connect()

    def disconnect_device(self):
        self.plc.disconnect()

    def start_scan(self, x_start, x_end, step):
        self.x_start = x_start
        self.x_end = x_end
        self.x_step = step
        self.is_running = True
        self.start()

    def stop_scan(self):
        self.is_running = False
        self.plc.stop_all()

    def stop(self):
        self.stop_scan()

    def run(self):
        if not self.plc.connected:
            if not self.plc.connect():
                self.error_occurred.emit("无法连接到 PLC")
                return

        self.status_update.emit("设备初始化中...")
        self.plc.initialize_machine()
        time.sleep(1)

        # 生成扫描路径
        x_points = []
        curr = self.x_start
        while curr <= self.x_end:
            x_points.append(curr)
            curr += self.x_step

        total_points = len(x_points)
        
        try:
            with open(self.data_file, 'w') as f:
                f.write("x,y,z\n") # Header

            for i, target_x in enumerate(x_points):
                if not self.is_running: break
                
                # 1. 移动到 X 位置
                self.status_update.emit(f"移动到 X={target_x:.1f}mm...")
                self.plc.move_axis(1, target_x) # Top Axis
                self.plc.move_axis(2, target_x) # Bottom Axis (同步移动)
                
                # 等待到位
                while self.is_running:
                    x1, x2, r = self.plc.get_all_positions()
                    if abs(x1 - target_x) < 0.5: # 0.5mm 容差
                        break
                    time.sleep(0.1)
                
                # 2. 执行旋转扫描
                self.status_update.emit(f"正在扫描 X={target_x:.1f}mm...")
                
                # 往复扫描: 偶数层 0->180, 奇数层 180->0
                start_angle = 0.0
                end_angle = 180.0
                if i % 2 != 0:
                    start_angle, end_angle = end_angle, start_angle
                
                self.plc.move_axis(3, end_angle, speed=self.scan_speed)
                
                # 采集循环
                while self.is_running:
                    x1, x2, r = self.plc.get_all_positions()
                    self.position_update.emit(x1, r)
                    
                    # 模拟传感器数据 (Z = 理论半径 + 噪声)
                    # 简单的半圆柱模型: y = r*cos(theta), z = r*sin(theta)
                    # 这里我们输出原始坐标 (x, y, z)
                    # 假设传感器测量的是表面点
                    
                    rad = math.radians(r)
                    # 模拟误差
                    noise = random.uniform(-0.05, 0.05)
                    periodic = 0.02 * math.sin(r * 0.1)
                    
                    simulated_r = self.radius + noise + periodic
                    
                    # 转换为笛卡尔坐标 (用于 3D 显示)
                    # 注意: 这里的 y, z 定义可能需要根据 UI 的坐标系调整
                    # 通常: x=长轴, y=水平横向, z=垂直高度
                    y_val = simulated_r * math.cos(rad)
                    z_val = simulated_r * math.sin(rad)
                    
                    # 写入数据
                    with open(self.data_file, 'a') as f:
                        f.write(f"{x1:.3f},{y_val:.3f},{z_val:.3f}\n")
                    
                    # 检查是否到达终点角度
                    if abs(r - end_angle) < 1.0:
                        break
                    
                    time.sleep(0.05) # 20Hz 采样率

                # 更新进度
                progress = int((i + 1) / total_points * 100)
                self.progress_update.emit(progress)

            self.status_update.emit("扫描完成")
            self.finished.emit()

        except Exception as e:
            logger.error(f"Scan Error: {e}")
            self.error_occurred.emit(str(e))
        finally:
            self.plc.stop_all()
