#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
硬件模拟器模块 - 模拟测量设备

模拟硬件测量设备的数据采集过程，根据理论点云数据生成带有微小误差的测量数据
"""

import os
import time
import math
import random
import numpy as np
import pandas as pd
from PySide6.QtCore import QThread, Signal


class HardwareSimulator(QThread):
    """硬件模拟器线程 - 模拟测量设备的工作过程"""
    
    # 自定义信号
    measurement_point = Signal(int, float, float, float)  # 序号, X, 角度, 测量半径
    measurement_finished = Signal()  # 测量完成信号
    measurement_error = Signal(str)  # 错误信号
    progress_updated = Signal(int, int)  # 进度更新 (当前点, 总点数)
    
    def __init__(self, theoretical_data, measurement_params, output_file_path="live_measurement.csv"):
        """
        初始化硬件模拟器
        
        Args:
            theoretical_data: Pandas DataFrame，包含理论点云数据 (x_mm, y_mm, z_mm)
            measurement_params: dict，测量参数 
                {
                    'x_min': float, 'x_max': float, 'x_step': float,
                    'rot_step': float, 'measurement_delay': float
                }
            output_file_path: str，输出文件路径
        """
        super().__init__()
        
        self.theoretical_data = theoretical_data
        self.measurement_params = measurement_params
        self.output_file_path = output_file_path
        self.is_running = False
        self.is_paused = False
        
        # 误差参数
        self.error_amplitude = 0.1  # 基础误差幅度 (±0.1mm)
        self.systematic_error = 0.02  # 系统性误差 (固定偏移)
        self.random_noise_level = 0.05  # 随机噪声级别
        
        print(f"HardwareSimulator初始化完成，理论数据点数: {len(theoretical_data)}")
        
    def run(self):
        """主运行函数 - 在独立线程中执行"""
        try:
            self.is_running = True
            self.simulate_measurement_process()
        except Exception as e:
            print(f"硬件模拟器运行出错: {e}")
            self.measurement_error.emit(f"硬件模拟器错误: {str(e)}")
        finally:
            self.is_running = False
            
    def simulate_measurement_process(self):
        """模拟整个测量过程"""
        print("开始硬件模拟测量过程...")
        
        # 清空或创建输出文件
        self.initialize_output_file()
        
        # 根据测量参数筛选需要测量的点
        measurement_points = self.filter_measurement_points()
        total_points = len(measurement_points)
        
        print(f"根据测量参数，需要测量 {total_points} 个点")
        
        # 逐个测量点进行模拟
        for i, (index, row) in enumerate(measurement_points.iterrows()):
            if not self.is_running:
                break
                
            # 检查暂停状态
            while self.is_paused and self.is_running:
                time.sleep(0.1)
                
            if not self.is_running:
                break
                
            # 执行单点测量模拟
            sequence = i + 1
            x_ideal, y_ideal, z_ideal = row['x_mm'], row['y_mm'], row['z_mm']
            
            # 逆向计算：笛卡尔坐标 → 硬件原始读数
            # 硬件坐标系统：
            # - X位置：直接对应 x_ideal
            # - 测量半径：从原点到(y, z)的距离
            # - 角度：相对于Y轴的角度
            x_pos = x_ideal
            ideal_radius = math.sqrt(y_ideal**2 + z_ideal**2)
            
            # 角度计算：使用atan2(z, y)来获得相对于Y轴的角度
            # 这样cos(angle) = y/radius, sin(angle) = z/radius
            angle_rad = math.atan2(z_ideal, y_ideal)
            angle_deg = math.degrees(angle_rad)
            
            # 模拟测量误差
            measured_radius = self.simulate_measurement_error(ideal_radius, sequence)
            
            # 写入数据到文件
            self.write_measurement_data(sequence, x_pos, angle_deg, measured_radius)
            
            # 发射信号
            self.measurement_point.emit(sequence, x_pos, angle_deg, measured_radius)
            self.progress_updated.emit(sequence, total_points)
            
            # 模拟测量延时
            measurement_delay = self.measurement_params.get('measurement_delay', 0.05)
            time.sleep(measurement_delay)
            
        print("硬件模拟测量过程完成")
        self.measurement_finished.emit()
        
    def filter_measurement_points(self):
        """根据测量参数筛选需要测量的点 - 改进的循环旋转模式"""
        x_min = self.measurement_params.get('x_min', -5.0)
        x_max = self.measurement_params.get('x_max', 500.0)
        x_step = self.measurement_params.get('x_step', 10.0)
        rot_step = self.measurement_params.get('rot_step', 1.5)
        
        # 筛选X轴范围内的点
        filtered_data = self.theoretical_data[
            (self.theoretical_data['x_mm'] >= x_min) & 
            (self.theoretical_data['x_mm'] <= x_max)
        ].copy()
        
        # 按X坐标分组
        x_values = sorted(filtered_data['x_mm'].unique())
        selected_x_values = []
        
        # 选择符合X步长的坐标
        current_x = x_min
        while current_x <= x_max:
            closest_x = min(x_values, key=lambda x: abs(x - current_x))
            if abs(closest_x - current_x) <= x_step / 2:
                selected_x_values.append(closest_x)
            current_x += x_step
        
        print(f"选择的X坐标: {len(selected_x_values)} 个")
        
        # 改进的循环旋转测量模式
        measurement_points = []
        reverse_direction = False  # 控制旋转方向
        
        for i, x_val in enumerate(selected_x_values):
            x_data = filtered_data[filtered_data['x_mm'] == x_val]
            
            if len(x_data) == 0:
                continue
                
            # 计算每个点的角度
            angles = []
            for _, row in x_data.iterrows():
                y, z = row['y_mm'], row['z_mm']
                angle_deg = math.degrees(math.atan2(y, z))
                angles.append((angle_deg, row))
                
            # 按角度排序
            angles.sort(key=lambda x: x[0])
            
            if not angles:
                continue
                
            min_angle = angles[0][0]
            max_angle = angles[-1][0]
            
            # 根据X轴位置决定旋转方向
            # 奇数位置：从最小角度到最大角度
            # 偶数位置：从最大角度到最小角度（循环往复）
            if i % 2 == 0:
                # 正向旋转：从min到max
                current_angle = min_angle
                while current_angle <= max_angle:
                    closest_angle_data = min(angles, key=lambda x: abs(x[0] - current_angle))
                    if abs(closest_angle_data[0] - current_angle) <= rot_step / 2:
                        measurement_points.append(closest_angle_data[1])
                    current_angle += rot_step
            else:
                # 反向旋转：从max到min
                current_angle = max_angle
                while current_angle >= min_angle:
                    closest_angle_data = min(angles, key=lambda x: abs(x[0] - current_angle))
                    if abs(closest_angle_data[0] - current_angle) <= rot_step / 2:
                        measurement_points.append(closest_angle_data[1])
                    current_angle -= rot_step
                    
        print(f"生成的测量点: {len(measurement_points)} 个")
        
        # 转换为DataFrame并按测量顺序排序
        if measurement_points:
            result_df = pd.DataFrame(measurement_points)
            result_df.reset_index(drop=True, inplace=True)
            return result_df
        else:
            return pd.DataFrame(columns=['x_mm', 'y_mm', 'z_mm'])
            
    def simulate_measurement_error(self, ideal_radius, sequence):
        """
        模拟测量误差
        
        Args:
            ideal_radius: float，理论半径值
            sequence: int，测量序号
            
        Returns:
            float，带误差的测量半径值
        """
        # 1. 系统性误差（固定偏移）
        systematic_error = self.systematic_error
        
        # 2. 随机噪声
        random_noise = (random.random() - 0.5) * 2 * self.random_noise_level
        
        # 3. 周期性误差（模拟机械振动等）
        periodic_error = 0.02 * math.sin(2 * math.pi * sequence / 50)
        
        # 4. 位置相关误差（随位置变化）
        position_error = 0.01 * math.sin(ideal_radius / 100)
        
        # 总误差
        total_error = systematic_error + random_noise + periodic_error + position_error
        
        # 限制误差范围
        total_error = max(-self.error_amplitude, min(self.error_amplitude, total_error))
        
        measured_radius = ideal_radius + total_error
        
        return measured_radius
        
    def initialize_output_file(self):
        """初始化输出文件"""
        try:
            # 创建目录（如果不存在）
            os.makedirs(os.path.dirname(self.output_file_path), exist_ok=True)
            
            # 创建文件并写入头部
            with open(self.output_file_path, 'w', encoding='utf-8') as f:
                f.write("sequence,x_pos_mm,angle_deg,measured_radius_mm\n")
                
            print(f"输出文件已初始化: {self.output_file_path}")
            
        except Exception as e:
            print(f"初始化输出文件失败: {e}")
            raise
            
    def write_measurement_data(self, sequence, x_pos, angle_deg, measured_radius):
        """写入测量数据到文件"""
        try:
            with open(self.output_file_path, 'a', encoding='utf-8') as f:
                f.write(f"{sequence},{x_pos:.3f},{angle_deg:.3f},{measured_radius:.6f}\n")
                
        except Exception as e:
            print(f"写入测量数据失败: {e}")
            
    def pause(self):
        """暂停测量"""
        self.is_paused = True
        print("硬件模拟器已暂停")
        
    def resume(self):
        """恢复测量"""
        self.is_paused = False
        print("硬件模拟器已恢复")
        
    def stop(self):
        """停止测量"""
        self.is_running = False
        self.is_paused = False
        print("硬件模拟器已停止")
        
    @staticmethod
    def load_theoretical_data(file_path):
        """
        静态方法：加载理论点云数据
        
        Args:
            file_path: str，理论点云文件路径
            
        Returns:
            pandas.DataFrame 或 None
        """
        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
                
                # 检查必要的列
                required_cols = ['x_mm', 'y_mm', 'z_mm']
                if all(col in df.columns for col in required_cols):
                    print(f"成功加载理论数据: {len(df)} 个点")
                    return df
                else:
                    # 尝试其他列名格式
                    alt_cols = ['x', 'y', 'z']
                    if all(col in df.columns for col in alt_cols):
                        df.rename(columns={'x': 'x_mm', 'y': 'y_mm', 'z': 'z_mm'}, inplace=True)
                        print(f"成功加载理论数据(重命名列): {len(df)} 个点")
                        return df
                    else:
                        print(f"CSV文件缺少必要的列。找到: {list(df.columns)}")
                        return None
                        
            else:
                print(f"不支持的文件格式: {file_path}")
                return None
                
        except Exception as e:
            print(f"加载理论数据失败: {e}")
            return None
