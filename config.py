#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模具曲面精度分析系统 - 配置管理模块

管理应用程序的各种配置参数和常量
"""

class AppConfig:
    """应用程序配置类"""
    
    # 应用程序基本信息
    APP_NAME = "模具曲面精度分析系统"
    APP_VERSION = "2.1"
    APP_ORGANIZATION = "工业精度检测"
    
    # 窗口尺寸和位置
    WINDOW_WIDTH = 1440
    WINDOW_HEIGHT = 900
    WINDOW_MIN_WIDTH = 1200
    WINDOW_MIN_HEIGHT = 700
    
    # 面板宽度
    LEFT_PANEL_WIDTH = 320
    RIGHT_PANEL_WIDTH = 320
    
    # 默认测量参数
    DEFAULT_X_MIN = -5.0
    DEFAULT_X_MAX = 500.0
    DEFAULT_X_STEP = 10.0
    DEFAULT_ROT_STEP = 1.5
    
    # 默认误差阈值参数（mm）
    DEFAULT_TOLERANCE_QUALIFIED = 0.1    # 合格阈值：±0.1mm
    DEFAULT_TOLERANCE_ATTENTION = 0.2    # 注意阈值：±0.2mm
    DEFAULT_TOLERANCE_OVER_LIMIT = 0.3   # 超差阈值：±0.3mm
    
    # 更新频率（毫秒）
    DATA_UPDATE_INTERVAL = 2000
    
    # 颜色配置
    COLORS = {
        'error_positive_high': '#ef4444',   # 红色 - 正向超差
        'error_positive_low': '#f97316',    # 橙色 - 正向误差
        'error_normal': '#10b981',          # 绿色 - 合格范围
        'error_negative_low': '#3b82f6',    # 蓝色 - 负向误差
        'error_negative_high': '#1e40af',   # 深蓝 - 负向超差
        'status_active': '#10b981',         # 绿色 - 活动状态
        'status_warning': '#f59e0b',        # 黄色 - 警告状态
        'status_error': '#ef4444',          # 红色 - 错误状态
    }
    
    # 误差阈值
    ERROR_THRESHOLDS = {
        'high_positive': 0.5,
        'low_positive': 0.25,
        'normal': 0.0,
        'low_negative': -0.25,
        'high_negative': -0.5,
    }
    
    # 文件路径配置
    SUPPORTED_MODEL_FORMATS = ['.step', '.stp', '.iges', '.igs', '.stl']
    
    @classmethod
    def get_color_legend_items(cls):
        """获取颜色图例项目列表"""
        return [
            (cls.COLORS['error_positive_high'], "+0.5mm (正向超差)"),
            (cls.COLORS['error_positive_low'], "+0.25mm"),
            (cls.COLORS['error_normal'], "0.0mm (合格范围)"),
            (cls.COLORS['error_negative_low'], "-0.25mm"),
            (cls.COLORS['error_negative_high'], "-0.5mm (负向超差)")
        ]
    
    @classmethod
    def get_error_color(cls, error_value):
        """根据误差值获取对应的颜色"""
        if error_value >= cls.ERROR_THRESHOLDS['high_positive']:
            return cls.COLORS['error_positive_high']
        elif error_value >= cls.ERROR_THRESHOLDS['low_positive']:
            return cls.COLORS['error_positive_low']
        elif error_value <= cls.ERROR_THRESHOLDS['high_negative']:
            return cls.COLORS['error_negative_high']
        elif error_value <= cls.ERROR_THRESHOLDS['low_negative']:
            return cls.COLORS['error_negative_low']
        else:
            return cls.COLORS['error_normal']
