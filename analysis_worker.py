#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
误差分析工作线程模块 - 实时误差计算与分析

处理测量数据与理论数据的比较，计算误差并进行统计分析
"""

import os
import time
import math
import threading
import numpy as np
import pandas as pd
from collections import deque
from PySide6.QtCore import QThread, Signal


class AnalysisWorker(QThread):
    """误差分析工作线程 - 实时处理测量数据并计算误差"""
    
    # 自定义信号
    analysis_result = Signal(dict)  # 分析结果信号
    statistics_updated = Signal(dict)  # 统计数据更新信号
    error_data_updated = Signal(list)  # 误差数据更新信号（用于直方图）
    analysis_finished = Signal()  # 分析完成信号
    analysis_error = Signal(str)  # 错误信号
    
    def __init__(self, theoretical_data, measurement_file_path="live_measurement.csv"):
        """
        初始化误差分析工作线程
        
        Args:
            theoretical_data: Pandas DataFrame，理论点云数据
            measurement_file_path: str，测量数据文件路径
        """
        super().__init__()
        
        self.theoretical_data = theoretical_data
        self.measurement_file_path = measurement_file_path
        self.is_running = False
        self.is_paused = False
        
        # 数据缓存
        self.processed_lines = 0  # 已处理的行数
        self.error_history = deque(maxlen=10000)  # 误差历史记录
        self.measurement_cache = {}  # 测量数据缓存
        
        # 统计数据
        self.statistics = {
            'total_points': 0,
            'max_error': 0.0,
            'min_error': 0.0,
            'avg_error': 0.0,
            'std_error': 0.0,
            'within_tolerance_count': 0,
            'tolerance_threshold': 0.1  # 合格阈值 ±0.1mm
        }
        
        # 创建理论数据的快速查找索引
        self.create_theoretical_lookup()
        
        print(f"AnalysisWorker初始化完成，理论数据点数: {len(theoretical_data)}")
        
    def create_theoretical_lookup(self):
        """创建理论数据的快速查找索引"""
        print("创建理论数据查找索引...")
        
        # 创建基于(x, angle)的查找字典
        self.theoretical_lookup = {}
        
        for index, row in self.theoretical_data.iterrows():
            x_mm, y_mm, z_mm = row['x_mm'], row['y_mm'], row['z_mm']
            
            # 计算角度 - 必须与硬件模拟器一致：使用atan2(z, y)
            angle_rad = math.atan2(z_mm, y_mm)
            angle_deg = math.degrees(angle_rad)
            
            # 计算理论半径
            theoretical_radius = math.sqrt(y_mm**2 + z_mm**2)
            
            # 创建键值对 (四舍五入到合理精度)
            x_key = round(x_mm, 1)  # X坐标精度到0.1mm
            angle_key = round(angle_deg, 1)  # 角度精度到0.1度
            
            key = (x_key, angle_key)
            self.theoretical_lookup[key] = {
                'x_theoretical': x_mm,
                'y_theoretical': y_mm, 
                'z_theoretical': z_mm,
                'radius_theoretical': theoretical_radius,
                'angle_theoretical': angle_deg
            }
            
        print(f"理论数据索引创建完成，索引项数: {len(self.theoretical_lookup)}")
        
    def run(self):
        """主运行函数 - 在独立线程中执行"""
        try:
            self.is_running = True
            self.monitor_measurement_file()
        except Exception as e:
            print(f"误差分析工作线程运行出错: {e}")
            self.analysis_error.emit(f"误差分析错误: {str(e)}")
        finally:
            self.is_running = False
            
    def monitor_measurement_file(self):
        """监控测量文件变化并处理新数据"""
        print("开始监控测量文件...")
        
        # 等待文件创建
        while self.is_running and not os.path.exists(self.measurement_file_path):
            time.sleep(0.1)
            
        if not self.is_running:
            return
            
        print(f"找到测量文件: {self.measurement_file_path}")
        
        # 初始化已处理行数
        self.processed_lines = 0
        
        # 持续监控文件
        while self.is_running:
            # 检查暂停状态
            while self.is_paused and self.is_running:
                time.sleep(0.1)
                
            if not self.is_running:
                break
                
            try:
                # 读取文件新增的行
                new_data = self.read_new_measurement_data()
                
                if new_data is not None and len(new_data) > 0:
                    # 处理新的测量数据
                    for _, row in new_data.iterrows():
                        if not self.is_running:
                            break
                        self.process_measurement_point(row)
                        
                # 短暂休眠避免过度占用CPU
                time.sleep(0.05)
                
            except Exception as e:
                print(f"监控文件时出错: {e}")
                time.sleep(0.5)  # 出错后稍长时间休眠
                
        print("误差分析监控结束")
        self.analysis_finished.emit()
        
    def read_new_measurement_data(self):
        """读取测量文件中的新数据"""
        try:
            # 读取整个文件
            df = pd.read_csv(self.measurement_file_path)
            
            # 检查是否有新行
            total_lines = len(df)
            if total_lines > self.processed_lines:
                # 获取新行
                new_data = df.iloc[self.processed_lines:].copy()
                self.processed_lines = total_lines
                return new_data
            else:
                return None
                
        except Exception as e:
            # 文件可能正在写入，忽略读取错误
            return None
            
    def process_measurement_point(self, measurement_row):
        """
        处理单个测量点数据
        
        Args:
            measurement_row: pandas Series，包含测量数据
        """
        try:
            # 提取测量数据
            sequence = int(measurement_row['sequence'])
            x_pos = float(measurement_row['x_pos_mm'])
            angle_deg = float(measurement_row['angle_deg'])
            measured_radius = float(measurement_row['measured_radius_mm'])
            
            # 查找对应的理论数据
            theoretical_data = self.find_theoretical_point(x_pos, angle_deg)
            
            if theoretical_data is None:
                print(f"警告: 找不到序号 {sequence} 对应的理论数据 (X={x_pos}, Angle={angle_deg})")
                return
                
            # 执行正向计算：硬件读数 → 笛卡尔坐标
            measured_point = self.convert_to_cartesian(x_pos, angle_deg, measured_radius)
            
            # 计算误差
            error_analysis = self.calculate_error(theoretical_data, measured_point, measured_radius)
            
            # 构建完整的分析结果
            analysis_result = {
                'sequence': sequence,
                'x_pos': x_pos,
                'angle_deg': angle_deg,
                'measured_radius': measured_radius,
                'theoretical_radius': theoretical_data['radius_theoretical'],
                'measured_point': measured_point,
                'theoretical_point': {
                    'x': theoretical_data['x_theoretical'],
                    'y': theoretical_data['y_theoretical'],
                    'z': theoretical_data['z_theoretical']
                },
                'error_analysis': error_analysis
            }
            
            # 更新统计数据
            self.update_statistics(error_analysis)
            
            # 发射信号
            self.analysis_result.emit(analysis_result)
            
        except Exception as e:
            print(f"处理测量点数据时出错: {e}")
            
    def find_theoretical_point(self, x_pos, angle_deg):
        """查找对应的理论点数据"""
        # 使用查找表进行快速查找
        x_key = round(x_pos, 1)
        angle_key = round(angle_deg, 1)
        key = (x_key, angle_key)
        
        # 直接查找
        if key in self.theoretical_lookup:
            return self.theoretical_lookup[key]
            
        # 如果直接查找失败，尝试邻近搜索
        tolerance_x = 0.5  # X方向容差
        tolerance_angle = 1.0  # 角度容差
        
        best_match = None
        min_distance = float('inf')
        
        for (lookup_x, lookup_angle), data in self.theoretical_lookup.items():
            if (abs(lookup_x - x_pos) <= tolerance_x and 
                abs(lookup_angle - angle_deg) <= tolerance_angle):
                
                # 计算距离
                distance = math.sqrt((lookup_x - x_pos)**2 + (lookup_angle - angle_deg)**2)
                
                if distance < min_distance:
                    min_distance = distance
                    best_match = data
                    
        return best_match
        
    def convert_to_cartesian(self, x_pos, angle_deg, measured_radius):
        """
        将硬件测量数据转换为笛卡尔坐标
        
        硬件坐标系统：
        - x_pos: X轴位置（沿工件长度方向）
        - angle_deg: 旋转角度（千分表相对于Y轴的角度）
        - measured_radius: 千分表测得的半径距离
        
        转换到笛卡尔坐标系：
        - X = x_pos (直接对应)
        - Y = measured_radius * cos(angle) (径向在Y方向的分量)  
        - Z = measured_radius * sin(angle) (径向在Z方向的分量)
        
        Args:
            x_pos: float，X位置
            angle_deg: float，角度(度) 
            measured_radius: float，测量半径
            
        Returns:
            dict，笛卡尔坐标 {'x', 'y', 'z'}
        """
        # 角度转换为弧度
        angle_rad = math.radians(angle_deg)
        
        # 坐标转换
        x_measured = x_pos  # X坐标直接对应
        y_measured = measured_radius * math.cos(angle_rad)  # Y分量
        z_measured = measured_radius * math.sin(angle_rad)  # Z分量
        
        return {
            'x': x_measured,
            'y': y_measured,
            'z': z_measured
        }
        
    def calculate_error(self, theoretical_data, measured_point, measured_radius):
        """
        计算各种误差指标
        
        Args:
            theoretical_data: dict，理论数据
            measured_point: dict，测量点笛卡尔坐标
            measured_radius: float，测量半径
            
        Returns:
            dict，误差分析结果
        """
        # 1. 半径误差
        radius_error = measured_radius - theoretical_data['radius_theoretical']
        
        # 2. 笛卡尔坐标误差
        x_error = measured_point['x'] - theoretical_data['x_theoretical']
        y_error = measured_point['y'] - theoretical_data['y_theoretical'] 
        z_error = measured_point['z'] - theoretical_data['z_theoretical']
        
        # 3. 欧氏距离误差（总体误差）
        euclidean_error = math.sqrt(x_error**2 + y_error**2 + z_error**2)
        
        # 4. 径向误差（在半径方向的投影）
        radial_error = radius_error  # 在半径测量中，径向误差等于半径误差
        
        # 5. 切向误差（垂直于半径方向）
        # 这里简化处理，使用总误差减去径向误差的估算
        tangential_error = math.sqrt(max(0, euclidean_error**2 - radial_error**2))
        
        # 6. 误差状态判定
        tolerance = self.statistics['tolerance_threshold']
        if abs(radius_error) <= tolerance:
            status = "合格"
            status_color = "green"
        elif abs(radius_error) <= tolerance * 2:
            status = "注意"
            status_color = "orange"
        else:
            status = "超差!"
            status_color = "red"
            
        return {
            'radius_error': radius_error,
            'x_error': x_error,
            'y_error': y_error,
            'z_error': z_error,
            'euclidean_error': euclidean_error,
            'radial_error': radial_error,
            'tangential_error': tangential_error,
            'status': status,
            'status_color': status_color
        }
        
    def update_statistics(self, error_analysis):
        """更新统计数据"""
        error_value = error_analysis['radius_error']
        self.error_history.append(error_value)
        
        # 更新计数
        self.statistics['total_points'] += 1
        
        # 检查容差范围
        if abs(error_value) <= self.statistics['tolerance_threshold']:
            self.statistics['within_tolerance_count'] += 1
            
        # 更新极值
        if self.statistics['total_points'] == 1:
            self.statistics['max_error'] = error_value
            self.statistics['min_error'] = error_value
        else:
            self.statistics['max_error'] = max(self.statistics['max_error'], error_value)
            self.statistics['min_error'] = min(self.statistics['min_error'], error_value)
            
        # 更新平均值和标准差
        errors_array = np.array(list(self.error_history))
        self.statistics['avg_error'] = np.mean(errors_array)
        self.statistics['std_error'] = np.std(errors_array)
        
        # 发射统计更新信号
        self.statistics_updated.emit(self.statistics.copy())
        
        # 发射误差数据更新信号（用于直方图）
        self.error_data_updated.emit(list(self.error_history))
        
    def pause(self):
        """暂停分析"""
        self.is_paused = True
        print("误差分析工作线程已暂停")
        
    def resume(self):
        """恢复分析"""
        self.is_paused = False
        print("误差分析工作线程已恢复")
        
    def stop(self):
        """停止分析"""
        self.is_running = False
        self.is_paused = False
        print("误差分析工作线程已停止")
        
    def get_current_statistics(self):
        """获取当前统计数据"""
        return self.statistics.copy()
        
    def reset_statistics(self):
        """重置统计数据"""
        self.statistics = {
            'total_points': 0,
            'max_error': 0.0,
            'min_error': 0.0,
            'avg_error': 0.0,
            'std_error': 0.0,
            'within_tolerance_count': 0,
            'tolerance_threshold': 0.1
        }
        self.error_history.clear()
        self.processed_lines = 0
        print("统计数据已重置")
