#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模具曲面精度分析系统 - 数据管理模块

管理测量数据、统计分析和数据更新
"""

import random
import math
from dataclasses import dataclass
from typing import List, Tuple, Dict
from PySide6.QtCore import QObject, Signal


@dataclass
class MeasurementPoint:
    """测量点数据类"""
    sequence: int           # 序号
    x_coord: float         # X坐标
    angle: float           # 角度
    measured_value: float  # 测量值
    theoretical_value: float # 理论值
    error: float           # 误差
    status: str            # 状态


class DataManager(QObject):
    """数据管理器"""
    
    # 信号定义
    data_updated = Signal()  # 数据更新信号
    statistics_updated = Signal(dict)  # 统计数据更新信号
    
    def __init__(self):
        super().__init__()
        self.measurement_data: List[MeasurementPoint] = []
        self.current_sequence = 1
        self.is_measuring = False
        self.statistics = {}
        
        # 初始化示例数据
        self.init_sample_data()
        
    def init_sample_data(self):
        """初始化示例数据"""
        sample_data = [
            (150.0, 45.0, 50.120, 50.100, "+0.020", "合格"),
            (150.0, 46.5, 50.135, 50.110, "+0.025", "合格"),
            (150.0, 48.0, 50.280, 50.125, "+0.155", "超差!")
        ]
        
        for i, (x, angle, measured, theoretical, error_str, status) in enumerate(sample_data):
            error_value = float(error_str.replace("+", ""))
            point = MeasurementPoint(
                sequence=i + 1,
                x_coord=x,
                angle=angle,
                measured_value=measured,
                theoretical_value=theoretical,
                error=error_value,
                status=status
            )
            self.measurement_data.append(point)
        
        self.current_sequence = len(self.measurement_data) + 1
        self.update_statistics()
        
    def add_measurement_point(self, x_coord: float, angle: float, 
                            measured_value: float, theoretical_value: float) -> MeasurementPoint:
        """添加测量点"""
        error = measured_value - theoretical_value
        status = self.determine_status(error)
        
        point = MeasurementPoint(
            sequence=self.current_sequence,
            x_coord=x_coord,
            angle=angle,
            measured_value=measured_value,
            theoretical_value=theoretical_value,
            error=error,
            status=status
        )
        
        self.measurement_data.append(point)
        self.current_sequence += 1
        
        # 更新统计数据
        self.update_statistics()
        
        # 发射信号
        self.data_updated.emit()
        
        return point
        
    def determine_status(self, error: float) -> str:
        """根据误差确定状态"""
        if abs(error) <= 0.1:
            return "合格"
        elif abs(error) <= 0.3:
            return "注意"
        else:
            return "超差!"
            
    def update_statistics(self):
        """更新统计数据"""
        if not self.measurement_data:
            return
            
        errors = [point.error for point in self.measurement_data]
        
        self.statistics = {
            'max_error': max(errors),
            'min_error': min(errors),
            'avg_error': sum(errors) / len(errors),
            'std_error': self.calculate_std(errors),
            'total_points': len(errors),
            'qualified_points': sum(1 for point in self.measurement_data if point.status == "合格"),
            'error_distribution': self.calculate_error_distribution(errors)
        }
        
        self.statistics_updated.emit(self.statistics)
        
    def calculate_std(self, values: List[float]) -> float:
        """计算标准差"""
        if len(values) < 2:
            return 0.0
            
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return math.sqrt(variance)
        
    def calculate_error_distribution(self, errors: List[float]) -> Dict[str, int]:
        """计算误差分布"""
        distribution = {
            '-0.2': 0,
            '-0.1': 0,
            '0.0': 0,
            '+0.1': 0,
            '+0.2': 0
        }
        
        for error in errors:
            if error <= -0.15:
                distribution['-0.2'] += 1
            elif error <= -0.05:
                distribution['-0.1'] += 1
            elif error <= 0.05:
                distribution['0.0'] += 1
            elif error <= 0.15:
                distribution['+0.1'] += 1
            else:
                distribution['+0.2'] += 1
                
        return distribution
        
    def simulate_measurement_point(self, x_coord: float, angle: float) -> MeasurementPoint:
        """模拟生成测量点（用于演示）"""
        # 生成理论值（基于简单的数学函数）
        theoretical_value = 50.0 + 0.1 * math.sin(math.radians(angle)) + 0.001 * x_coord
        
        # 生成带噪声的测量值
        noise = random.gauss(0, 0.05)  # 标准差为0.05的高斯噪声
        measured_value = theoretical_value + noise
        
        return self.add_measurement_point(x_coord, angle, measured_value, theoretical_value)
        
    def start_measurement(self):
        """开始测量"""
        self.is_measuring = True
        
    def stop_measurement(self):
        """停止测量"""
        self.is_measuring = False
        
    def pause_measurement(self):
        """暂停测量"""
        self.is_measuring = False
        
    def clear_data(self):
        """清除所有数据"""
        self.measurement_data.clear()
        self.current_sequence = 1
        self.statistics.clear()
        self.data_updated.emit()
        
    def get_latest_points(self, count: int = 10) -> List[MeasurementPoint]:
        """获取最新的测量点"""
        return self.measurement_data[-count:] if len(self.measurement_data) >= count else self.measurement_data
        
    def get_all_data(self) -> List[MeasurementPoint]:
        """获取所有测量数据"""
        return self.measurement_data
        
    def export_data(self, filename: str):
        """导出数据到文件"""
        # TODO: 实现数据导出功能
        pass
        
    def import_data(self, filename: str):
        """从文件导入数据"""
        # TODO: 实现数据导入功能
        pass
