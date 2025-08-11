#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模具曲面精度分析系统 - 主窗口模块

使用 PySide6 创建的桌面应用程序，用于模具表面精度的分析和可视化
"""

import sys
import os
import random
import math
import numpy as np
import pandas as pd
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QGridLayout, QFormLayout, QLabel, 
                               QPushButton, QLineEdit, QTableWidget, QTableWidgetItem,
                               QMenuBar, QToolBar, QSplitter, QFrame, QHeaderView,
                               QSizePolicy, QFileDialog, QMessageBox)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QIcon, QFont, QPalette, QColor

from config import AppConfig
from styles import StyleManager
from hardware_simulator import HardwareSimulator
from analysis_worker import AnalysisWorker
from hardware_simulator import HardwareSimulator
from analysis_worker import AnalysisWorker


class MainWindow(QMainWindow):
    """主窗口类 - 模具曲面精度分析系统"""
    
    def __init__(self):
        super().__init__()
        
        # 初始化状态变量
        self.is_measuring = False
        self.simulation_timer = QTimer()
        self.current_sequence = 104  # 从示例数据后继续
        self.measurement_count = 103
        self.total_measurement_count = 2500
        
        # 模拟数据存储
        self.current_x = 150.0
        self.current_angle = 48.0
        self.errors_list = [0.020, 0.025, 0.155]  # 从示例数据开始
        
        # 新增：理论点云数据和模拟线程
        self.theoretical_data = None
        self.hardware_simulator = None
        self.analysis_worker = None
        self.measurement_file_path = "data/live_measurement.csv"
        
        # 新增：模拟器和分析器线程
        self.hardware_simulator = None
        self.analysis_worker = None
        self.theoretical_data = None  # 存储加载的理论数据
        
        # 新增：3D可视化相关
        self.matplotlib_canvas = None
        self.matplotlib_figure = None
        self.matplotlib_ax = None
        self.theoretical_scatter = None  # 理论点云散点图
        self.measured_scatter = None     # 测量点云散点图
        self.measured_points = []        # 存储测量点数据
        
        self.init_ui()
        self.setup_style()
        self.setup_connections()  # 设置信号连接
        self.init_timer()
        
    def init_ui(self):
        """初始化用户界面"""
        # 设置主窗口属性
        self.setWindowTitle(f"{AppConfig.APP_NAME} V{AppConfig.APP_VERSION}")
        self.setGeometry(100, 100, AppConfig.WINDOW_WIDTH, AppConfig.WINDOW_HEIGHT)
        self.setMinimumSize(AppConfig.WINDOW_MIN_WIDTH, AppConfig.WINDOW_MIN_HEIGHT)
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 创建工具栏
        self.create_toolbar()
        
        # 创建中央窗口部件
        self.create_central_widget()
        
    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件(&F)')
        
        # 视图菜单
        view_menu = menubar.addMenu('视图(&V)')
        
        # 工具菜单
        tools_menu = menubar.addMenu('工具(&T)')
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助(&H)')
        
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = self.addToolBar('主工具栏')
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        
        # 加载模型按钮
        self.load_model_btn = QPushButton("📁 加载理论模型")
        self.load_model_btn.setObjectName("primaryButton")
        toolbar.addWidget(self.load_model_btn)
        
        toolbar.addSeparator()
        
        # 重置视图按钮
        self.reset_view_btn = QPushButton("🔄 重置视图")
        self.reset_view_btn.setObjectName("secondaryButton")
        toolbar.addWidget(self.reset_view_btn)
        
        toolbar.addSeparator()
        
        # 开始测量按钮
        self.start_measure_btn = QPushButton("▶ 开始测量")
        self.start_measure_btn.setObjectName("successButton")
        toolbar.addWidget(self.start_measure_btn)
        
        # 暂停按钮
        self.pause_btn = QPushButton("⏸ 暂停")
        self.pause_btn.setObjectName("warningButton")
        self.pause_btn.setEnabled(False)  # 初始状态禁用
        toolbar.addWidget(self.pause_btn)
        
        # 停止按钮
        self.stop_btn = QPushButton("⏹ 停止")
        self.stop_btn.setObjectName("dangerButton")
        self.stop_btn.setEnabled(False)  # 初始状态禁用
        toolbar.addWidget(self.stop_btn)
        
    def create_central_widget(self):
        """创建中央窗口部件"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局 - 仅三栏水平布局（中间面板包含3D与表格）
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 三栏水平布局
        top_splitter = QSplitter(Qt.Horizontal)
        
        # 左侧面板 - 测量设置与控制
        left_panel = self.create_left_panel()
        top_splitter.addWidget(left_panel)
        
        # 中心区域 - 3D可视化 + 表格
        center_panel = self.create_center_panel()
        top_splitter.addWidget(center_panel)
        
        # 右侧面板 - 统计分析与图例
        right_panel = self.create_right_panel()
        top_splitter.addWidget(right_panel)
        
        # 设置三栏的宽度比例 [320, flexible, 320]
        top_splitter.setSizes([320, 800, 320])
        top_splitter.setStretchFactor(0, 0)  # 左侧固定宽度
        top_splitter.setStretchFactor(1, 1)  # 中心可伸缩
        top_splitter.setStretchFactor(2, 0)  # 右侧固定宽度
        
        # 添加三栏到主布局
        main_layout.addWidget(top_splitter)
        # 中心面板内部已包含实时数据表格
        
    def create_left_panel(self):
        """创建左侧面板 - 测量设置与控制"""
        panel = QFrame()
        panel.setObjectName("leftPanel")
        panel.setFixedWidth(320)  # 固定宽度320px，与UI.png一致
        panel.setFrameStyle(QFrame.StyledPanel)
        
        layout = QVBoxLayout(panel)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # 理论模型信息
        model_group = self.create_model_info_group()
        layout.addWidget(model_group)
        
        # 测量参数设置
        params_group = self.create_measurement_params_group()
        layout.addWidget(params_group)
        
        # 实时状态监控
        status_group = self.create_status_monitor_group()
        layout.addWidget(status_group)
        
        # 添加伸缩空间
        layout.addStretch()
        
        return panel
        
    def create_model_info_group(self):
        """创建理论模型信息组"""
        group_widget = QWidget()
        layout = QVBoxLayout(group_widget)
        
        # 标题
        title = QLabel("理论模型信息")
        title.setObjectName("groupTitle")
        layout.addWidget(title)
        
        # 加载理论模型按钮
        self.load_cad_btn = QPushButton("加载理论点云...")
        self.load_cad_btn.setObjectName("primaryButton")
        layout.addWidget(self.load_cad_btn)
        
        layout.addSpacing(10)
        
        # 模型信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(8)
        
        # 模型名称
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("点云文件:"))
        self.model_name_label = QLabel("未加载")
        self.model_name_label.setObjectName("infoValue")
        name_layout.addWidget(self.model_name_label)
        name_layout.addStretch()
        info_layout.addLayout(name_layout)
        
        # 旋转轴范围
        range_layout = QHBoxLayout()
        range_layout.addWidget(QLabel("旋转轴范围:"))
        self.rotation_range_label = QLabel("10.0° - 170.0°")
        self.rotation_range_label.setObjectName("infoValue")
        range_layout.addWidget(self.rotation_range_label)
        range_layout.addStretch()
        info_layout.addLayout(range_layout)
        
        layout.addLayout(info_layout)
        
        return group_widget
        
    def create_measurement_params_group(self):
        """创建测量参数设置组"""
        group_widget = QWidget()
        layout = QVBoxLayout(group_widget)
        
        # 标题
        title = QLabel("测量参数设置")
        title.setObjectName("groupTitle")
        layout.addWidget(title)
        
        # 参数设置表单
        form_layout = QGridLayout()
        form_layout.setSpacing(12)
        
        # X轴测量范围
        form_layout.addWidget(QLabel("X轴测量范围"), 0, 0, 1, 4)
        range_layout = QHBoxLayout()
        self.x_min_input = QLineEdit(str(AppConfig.DEFAULT_X_MIN))
        self.x_min_input.setFixedWidth(60)
        self.x_max_input = QLineEdit(str(AppConfig.DEFAULT_X_MAX))
        self.x_max_input.setFixedWidth(60)
        range_layout.addWidget(self.x_min_input)
        range_layout.addWidget(QLabel("至"))
        range_layout.addWidget(self.x_max_input)
        range_layout.addWidget(QLabel("mm"))
        range_layout.addStretch()
        
        range_widget = QWidget()
        range_widget.setLayout(range_layout)
        form_layout.addWidget(range_widget, 1, 0, 1, 4)
        
        # X轴步长
        form_layout.addWidget(QLabel("X轴步长"), 2, 0)
        step_layout = QHBoxLayout()
        self.x_step_input = QLineEdit(str(AppConfig.DEFAULT_X_STEP))
        self.x_step_input.setFixedWidth(60)
        step_layout.addWidget(self.x_step_input)
        step_layout.addWidget(QLabel("mm"))
        step_layout.addStretch()
        
        step_widget = QWidget()
        step_widget.setLayout(step_layout)
        form_layout.addWidget(step_widget, 3, 0, 1, 4)
        
        # 旋转轴步长
        form_layout.addWidget(QLabel("旋转轴步长"), 4, 0)
        rot_step_layout = QHBoxLayout()
        self.rot_step_input = QLineEdit(str(AppConfig.DEFAULT_ROT_STEP))
        self.rot_step_input.setFixedWidth(60)
        rot_step_layout.addWidget(self.rot_step_input)
        rot_step_layout.addWidget(QLabel("°"))
        rot_step_layout.addStretch()
        
        rot_step_widget = QWidget()
        rot_step_widget.setLayout(rot_step_layout)
        form_layout.addWidget(rot_step_widget, 5, 0, 1, 4)
        
        layout.addLayout(form_layout)
        
        return group_widget
        
    def create_status_monitor_group(self):
        """创建实时状态监控组"""
        group_widget = QWidget()
        layout = QVBoxLayout(group_widget)
        
        # 标题
        title = QLabel("实时状态监控")
        title.setObjectName("groupTitle")
        layout.addWidget(title)
        
        # 状态信息
        status_layout = QVBoxLayout()
        status_layout.setSpacing(8)
        
        # 当前X位置
        x_pos_layout = QHBoxLayout()
        x_pos_layout.addWidget(QLabel("当前X位置:"))
        self.current_x_label = QLabel("150.0 mm")
        self.current_x_label.setObjectName("infoValue")
        x_pos_layout.addWidget(self.current_x_label)
        x_pos_layout.addStretch()
        status_layout.addLayout(x_pos_layout)
        
        # 当前旋转角
        rot_angle_layout = QHBoxLayout()
        rot_angle_layout.addWidget(QLabel("当前旋转角:"))
        self.current_angle_label = QLabel("45.0°")
        self.current_angle_label.setObjectName("infoValue")
        rot_angle_layout.addWidget(self.current_angle_label)
        rot_angle_layout.addStretch()
        status_layout.addLayout(rot_angle_layout)
        
        # 有效角度
        valid_angle_layout = QHBoxLayout()
        valid_angle_layout.addWidget(QLabel("有效角度:"))
        self.valid_angle_label = QLabel("[15°-75°], [105°-165°]")
        self.valid_angle_label.setObjectName("infoValue")
        valid_angle_layout.addWidget(self.valid_angle_label)
        valid_angle_layout.addStretch()
        status_layout.addLayout(valid_angle_layout)
        
        # 系统状态
        system_status_layout = QHBoxLayout()
        system_status_layout.addWidget(QLabel("系统状态:"))
        status_widget = QWidget()
        status_inner_layout = QHBoxLayout(status_widget)
        status_inner_layout.setContentsMargins(0, 0, 0, 0)
        
        # 状态指示器
        self.status_indicator = QLabel("●")
        self.status_indicator.setObjectName("statusIndicator")
        self.status_indicator.setStyleSheet("color: #10b981; font-size: 8px;")
        status_inner_layout.addWidget(self.status_indicator)
        
        self.status_text = QLabel("测量中...")
        self.status_text.setObjectName("infoValue")
        status_inner_layout.addWidget(self.status_text)
        status_inner_layout.addStretch()
        
        system_status_layout.addWidget(status_widget)
        system_status_layout.addStretch()
        status_layout.addLayout(system_status_layout)
        
        layout.addLayout(status_layout)
        
        return group_widget
        
    def create_center_panel(self):
        """创建中心面板 - 3D可视化 + 实时数据表格"""
        panel = QFrame()
        panel.setObjectName("centerPanel")
        
        layout = QVBoxLayout(panel)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # 3D可视化窗口
        self.visualization_widget = QWidget()
        self.visualization_widget.setObjectName("visualizationPlaceholder")
        self.visualization_widget.setMinimumHeight(400)
        self.visualization_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # 保存layout引用以便后续更新
        self.viz_layout = QVBoxLayout(self.visualization_widget)
        self.viz_layout.setContentsMargins(0, 0, 0, 0)
        self.viz_layout.setSpacing(0)
        viz_label = QLabel("3D Visualization Window\nClick 'Load Theoretical Model' to load point cloud data")
        viz_label.setAlignment(Qt.AlignCenter)
        viz_label.setObjectName("placeholderText")
        self.viz_layout.addWidget(viz_label)
        
        layout.addWidget(self.visualization_widget)
        
        # 添加实时数据表格（位于中心面板下方）
        table_widget = self.create_data_table_widget()
        layout.addWidget(table_widget)
        
        # 设置中间布局伸缩比例：3D区域更大，表格较小
        layout.setStretch(0, 3)
        layout.setStretch(1, 1)
        
        return panel
    
    def create_data_table_widget(self):
        """创建实时数据表格独立组件"""
        table_widget = QWidget()
        table_widget.setObjectName("dataTableWidget")
        
        layout = QVBoxLayout(table_widget)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # 表格标题和状态
        table_header = QHBoxLayout()
        table_title = QLabel("实时数据表格")
        table_title.setObjectName("groupTitle")
        table_header.addWidget(table_title)
        
        self.table_status_label = QLabel(f"测量中... (已完成 {self.measurement_count} / 约 {self.total_measurement_count} 点)")
        self.table_status_label.setObjectName("tableStatus")
        table_header.addWidget(self.table_status_label)
        table_header.addStretch()
        
        layout.addLayout(table_header)
        
        # 创建表格
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(7)
        self.data_table.setHorizontalHeaderLabels([
            "序号", "X坐标(mm)", "角度(°)", "测量值(mm)", 
            "理论值(mm)", "误差(mm)", "状态"
        ])
        
        # 设置表格属性
        self.data_table.setAlternatingRowColors(True)
        self.data_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.data_table.setMinimumHeight(250)
        self.data_table.setMaximumHeight(300)
        
        # 设置表头
        header = self.data_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        
        # 添加示例数据
        self.populate_sample_data()
        
        layout.addWidget(self.data_table)
        
        return table_widget
        # 删除原有的create_data_table方法调用，因为现在已经移到独立组件中
        pass
        
    def populate_sample_data(self):
        """填充示例数据"""
        sample_data = [
            ["101", "150.0", "45.0", "50.120", "50.100", "+0.020", "合格"],
            ["102", "150.0", "46.5", "50.135", "50.110", "+0.025", "合格"],
            ["103", "150.0", "48.0", "50.280", "50.125", "+0.155", "超差!"]
        ]
        
        self.data_table.setRowCount(len(sample_data))
        
        for row, data in enumerate(sample_data):
            for col, value in enumerate(data):
                item = QTableWidgetItem(str(value))
                
                # 根据状态设置行颜色
                if col == 6 and value == "超差!":
                    item.setBackground(QColor("#fef3c7"))  # 黄色背景
                
                self.data_table.setItem(row, col, item)
        
    def create_right_panel(self):
        """创建右侧面板 - 统计分析与图例"""
        panel = QFrame()
        panel.setObjectName("rightPanel")
        panel.setFixedWidth(320)  # 固定宽度320px，与UI.png一致
        panel.setFrameStyle(QFrame.StyledPanel)
        
        layout = QVBoxLayout(panel)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # 颜色图例
        legend_group = self.create_color_legend_group()
        layout.addWidget(legend_group)
        
        # 总体误差统计
        stats_group = self.create_error_stats_group()
        layout.addWidget(stats_group)
        
        # 误差分布直方图（占位符）
        chart_group = self.create_error_chart_group()
        layout.addWidget(chart_group)
        
        # 添加伸缩空间
        layout.addStretch()
        
        return panel
        
    def create_color_legend_group(self):
        """创建颜色图例组"""
        group_widget = QWidget()
        layout = QVBoxLayout(group_widget)
        
        # 标题
        title = QLabel("颜色图例")
        title.setObjectName("groupTitle")
        layout.addWidget(title)
        
        # 图例项目
        legend_items = AppConfig.get_color_legend_items()
        
        for color, text in legend_items:
            item_layout = QHBoxLayout()
            
            # 颜色块
            color_block = QLabel()
            color_block.setFixedSize(16, 16)
            color_block.setStyleSheet(StyleManager.get_color_block_style(color))
            item_layout.addWidget(color_block)
            
            # 文字说明
            text_label = QLabel(text)
            text_label.setObjectName("legendText")
            item_layout.addWidget(text_label)
            item_layout.addStretch()
            
            layout.addLayout(item_layout)
        
        return group_widget
        
    def create_error_stats_group(self):
        """创建总体误差统计组"""
        group_widget = QWidget()
        layout = QVBoxLayout(group_widget)
        
        # 标题
        title = QLabel("总体误差统计")
        title.setObjectName("groupTitle")
        layout.addWidget(title)
        
        # 统计数据 - 创建可更新的标签引用
        stats_data = [
            ("最大误差:", "+0.152 mm", "max_error_label"),
            ("最小误差:", "-0.201 mm", "min_error_label"),
            ("平均误差:", "+0.034 mm", "avg_error_label"),
            ("标准差:", "0.088 mm", "std_error_label")
        ]
        
        for label_text, initial_value, attr_name in stats_data:
            stat_layout = QHBoxLayout()
            
            label_widget = QLabel(label_text)
            label_widget.setObjectName("statLabel")
            stat_layout.addWidget(label_widget)
            
            value_widget = QLabel(initial_value)
            value_widget.setObjectName("statValue")
            stat_layout.addWidget(value_widget)
            stat_layout.addStretch()
            
            # 保存标签引用以便后续更新
            setattr(self, attr_name, value_widget)
            
            layout.addLayout(stat_layout)
        
        return group_widget
        
    def create_error_chart_group(self):
        """创建误差分布直方图组"""
        group_widget = QWidget()
        layout = QVBoxLayout(group_widget)
        
        # 标题
        title = QLabel("误差分布直方图")
        title.setObjectName("groupTitle")
        layout.addWidget(title)
        
        # 创建matplotlib直方图画布
        try:
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
            from matplotlib.figure import Figure
            
            # 创建图形
            self.histogram_figure = Figure(figsize=(4, 3))
            self.histogram_canvas = FigureCanvas(self.histogram_figure)
            self.histogram_canvas.setFixedHeight(200)
            self.histogram_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            
            # 创建子图
            self.histogram_ax = self.histogram_figure.add_subplot(111)
            self.histogram_ax.set_xlabel('Error (mm)', fontsize=8)
            self.histogram_ax.set_ylabel('Frequency', fontsize=8)
            self.histogram_ax.tick_params(axis='both', labelsize=8)
            
            # 初始化空直方图
            self.update_error_histogram([])
            
            layout.addWidget(self.histogram_canvas)
            
        except ImportError:
            # 如果matplotlib不可用，显示占位符
            chart_placeholder = QWidget()
            chart_placeholder.setObjectName("chartPlaceholder")
            chart_placeholder.setFixedHeight(200)
            
            chart_layout = QVBoxLayout(chart_placeholder)
            chart_label = QLabel("Matplotlib required\nfor error distribution chart")
            chart_label.setAlignment(Qt.AlignCenter)
            chart_label.setObjectName("placeholderText")
            chart_layout.addWidget(chart_label)
            
            layout.addWidget(chart_placeholder)
        
        return group_widget
        
    def update_error_histogram(self, error_data):
        """更新误差分布直方图"""
        try:
            if not hasattr(self, 'histogram_ax'):
                return
                
            # 清除之前的图形
            self.histogram_ax.clear()
            
            if len(error_data) > 0:
                # 绘制直方图
                self.histogram_ax.hist(
                    error_data, bins=20, alpha=0.7, color='skyblue', edgecolor='black'
                )
                
                # 添加统计线
                mean_error = np.mean(error_data)
                self.histogram_ax.axvline(mean_error, color='red', linestyle='--', 
                                        linewidth=2, label=f'Mean: {mean_error:.3f}')
                
                # 添加合格范围线
                self.histogram_ax.axvline(0.1, color='green', linestyle=':', 
                                        alpha=0.7, label='Tolerance Range')
                self.histogram_ax.axvline(-0.1, color='green', linestyle=':', alpha=0.7)
                
                self.histogram_ax.legend(fontsize=8)
                
            else:
                # 显示空图表
                self.histogram_ax.text(0.5, 0.5, 'No Data Available', 
                                     transform=self.histogram_ax.transAxes,
                                     ha='center', va='center', fontsize=10)
            
            # 设置标签和格式
            self.histogram_ax.set_xlabel('Error (mm)', fontsize=8)
            self.histogram_ax.set_ylabel('Frequency', fontsize=8)
            self.histogram_ax.tick_params(axis='both', labelsize=8)
            
            # 调整布局
            self.histogram_figure.tight_layout()
            
            # 刷新画布
            self.histogram_canvas.draw()
            
        except Exception as e:
            print(f"更新误差直方图时出错: {e}")
        
    def setup_style(self):
        """设置界面样式"""
        # 应用自定义样式表
        self.setStyleSheet(StyleManager.get_main_stylesheet())
        
    def get_stylesheet(self):
        """获取样式表 - 已弃用，使用 StyleManager"""
        # 这个方法保留以防需要自定义样式
        return StyleManager.get_main_stylesheet()
        
    def init_timer(self):
        """初始化定时器"""
        # 模拟定时器已在 __init__ 中创建，这里不需要额外的定时器
        pass
        
    # 更新实时状态监控功能已整合到上述方法中
    
    def setup_connections(self):
        """设置信号连接"""
        # 工具栏按钮连接
        self.load_model_btn.clicked.connect(self.load_model)
        self.reset_view_btn.clicked.connect(self.reset_view)
        self.start_measure_btn.clicked.connect(self.start_measurement)
        self.pause_btn.clicked.connect(self.pause_measurement)
        self.stop_btn.clicked.connect(self.stop_measurement)
        
        # 左侧面板按钮连接
        self.load_cad_btn.clicked.connect(self.load_model)
        
        # 定时器连接
        self.simulation_timer.timeout.connect(self.simulation_step)
        
    # ==========================================
    # 占位符函数实现
    # ==========================================
    
    def load_model(self):
        """加载理论点云数据文件"""
        print("=== 加载理论点云数据 ===")
        
        # 打开文件选择对话框
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择理论点云数据文件",
            "",
            "点云文件 (*.csv *.txt);;CSV文件 (*.csv);;文本文件 (*.txt);;所有文件 (*.*)"
        )
        
        if file_path:
            print(f"选择的点云文件路径: {file_path}")
            
            try:
                # 使用HardwareSimulator的静态方法加载点云数据
                point_cloud_data = HardwareSimulator.load_theoretical_data(file_path)
                
                if point_cloud_data is not None:
                    # 保存理论数据
                    self.theoretical_data = point_cloud_data
                    
                    # 更新UI显示
                    import os
                    file_name = os.path.basename(file_path)
                    self.model_name_label.setText(file_name)
                    
                    # 更新点云数据计数
                    point_count = len(point_cloud_data)
                    self.rotation_range_label.setText(f"数据点: {point_count} 个")
                    
                    # 在3D可视化区域显示点云
                    self.display_point_cloud_in_3d(point_cloud_data.values)
                    
                    print(f"成功加载理论点云数据: {point_count} 个数据点")
                    
                    # 显示成功消息
                    QMessageBox.information(
                        self, 
                        "加载成功", 
                        f"成功加载理论点云数据!\n\n文件: {file_name}\n数据点: {point_count} 个"
                    )
                else:
                    # 显示错误消息
                    QMessageBox.warning(
                        self,
                        "加载失败",
                        f"无法加载点云文件: {file_path}\n\n请检查文件格式是否正确。"
                    )
            
            except Exception as e:
                print(f"加载点云文件时出错: {e}")
                QMessageBox.critical(
                    self,
                    "加载错误", 
                    f"加载点云文件时发生错误:\n\n{str(e)}"
                )
        else:
            print("用户取消了文件选择")
            
    def load_point_cloud_file(self, file_path):
        """加载点云数据文件"""
        try:
            if file_path.endswith('.csv'):
                # 尝试加载CSV文件
                df = pd.read_csv(file_path)
                
                # 检查是否有必要的列
                required_cols = ['x_mm', 'y_mm', 'z_mm']
                if all(col in df.columns for col in required_cols):
                    points = df[required_cols].values
                    self.theoretical_data = df  # 保存完整的DataFrame
                    return points
                else:
                    # 尝试其他可能的列名格式
                    alt_cols = ['x', 'y', 'z']
                    if all(col in df.columns for col in alt_cols):
                        df_renamed = df.rename(columns={'x': 'x_mm', 'y': 'y_mm', 'z': 'z_mm'})
                        points = df_renamed[required_cols].values
                        self.theoretical_data = df_renamed  # 保存完整的DataFrame
                        return points
                    else:
                        print(f"CSV文件缺少必要的列。找到的列: {list(df.columns)}")
                        print(f"需要的列: {required_cols} 或 {alt_cols}")
                        return None
                    
            elif file_path.endswith('.txt'):
                # 尝试加载文本文件
                with open(file_path, 'r') as f:
                    lines = f.readlines()
                
                points = []
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split()
                        if len(parts) >= 3:  # x, y, z
                            try:
                                x, y, z = float(parts[0]), float(parts[1]), float(parts[2])
                                points.append([x, y, z])
                            except ValueError:
                                continue
                
                if points:
                    points_array = np.array(points)
                    # 创建DataFrame
                    self.theoretical_data = pd.DataFrame(points_array, columns=['x_mm', 'y_mm', 'z_mm'])
                    return points_array
                else:
                    return None
            
            else:
                print(f"不支持的文件格式: {file_path}")
                return None
                
        except Exception as e:
            print(f"读取点云文件时出错: {e}")
            return None
    
    def display_point_cloud_in_3d(self, point_cloud_data):
        """在3D可视化区域显示点云数据"""
        try:
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
            from matplotlib.figure import Figure
            
            # 创建matplotlib图形
            self.matplotlib_figure = Figure(figsize=(10, 8))
            self.matplotlib_canvas = FigureCanvas(self.matplotlib_figure)
            self.matplotlib_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.matplotlib_canvas.setMinimumSize(1, 1)
            
            # 创建3D子图
            self.matplotlib_ax = self.matplotlib_figure.add_subplot(111, projection='3d')
            
            # 从点云数据中提取坐标
            if len(point_cloud_data) > 5000:
                # 如果点太多，进行采样以提高性能
                indices = np.random.choice(len(point_cloud_data), 5000, replace=False)
                sampled_data = point_cloud_data[indices]
            else:
                sampled_data = point_cloud_data
            
            x_coords = sampled_data[:, 0]
            y_coords = sampled_data[:, 1] 
            z_coords = sampled_data[:, 2]
            
            # 绘制理论点云（蓝色，半透明）
            self.theoretical_scatter = self.matplotlib_ax.scatter(
                x_coords, y_coords, zs=z_coords,
                c='lightblue', s=1, alpha=0.3, label='Theoretical Points'
            )
            
            # 设置标签和标题
            self.matplotlib_ax.set_xlabel('X (mm)')
            self.matplotlib_ax.set_ylabel('Y (mm)')
            # 对于3D轴，使用try-catch来设置Z标签
            try:
                self.matplotlib_ax.set_zlabel('Z (mm)')
            except AttributeError:
                pass
            self.matplotlib_ax.set_title('Theoretical vs Measured Point Cloud', pad=10)
            
            # 添加图例
            self.matplotlib_ax.legend()
            
            # 调整布局
            self.matplotlib_figure.tight_layout()
            
            # 更新3D可视化区域
            self.update_visualization_widget(self.matplotlib_canvas)
            
            print(f"3D点云可视化已更新，显示 {len(sampled_data)} 个理论点")
            
        except ImportError as e:
            print(f"缺少matplotlib库: {e}")
            QMessageBox.warning(
                self, "可视化错误", 
                "需要安装matplotlib库才能显示3D可视化\n\n请运行: pip install matplotlib"
            )
        except Exception as e:
            print(f"3D可视化时出错: {e}")
            QMessageBox.warning(self, "可视化错误", f"显示3D点云时出错:\n\n{str(e)}")
            
    def add_measured_point_to_3d(self, measured_point, error_analysis):
        """向3D可视化添加测量点"""
        try:
            if self.matplotlib_ax is None:
                return
                
            # 提取测量点坐标
            x = measured_point['x']
            y = measured_point['y']
            z = measured_point['z']
            
            # 根据误差确定颜色
            error_value = error_analysis['radius_error']
            if error_analysis['status'] == "合格":
                color = 'green'
            elif error_analysis['status'] == "注意":
                color = 'orange'
            else:
                color = 'red'
            
            # 添加测量点到3D图中
            self.matplotlib_ax.scatter(
                [x], [y], [z], 
                c=[color], s=20, alpha=0.8
            )
            
            # 存储测量点数据用于后续更新
            self.measured_points.append({
                'x': x, 'y': y, 'z': z,
                'error': error_value,
                'color': color
            })
            
            # 限制测量点数量以提高性能
            if len(self.measured_points) > 1000:
                self.measured_points = self.measured_points[-1000:]
                
            # 每100个点更新一次显示
            if len(self.measured_points) % 100 == 0:
                self.refresh_3d_view()
                
        except Exception as e:
            print(f"添加测量点到3D视图时出错: {e}")
            
    def refresh_3d_view(self):
        """刷新3D视图"""
        try:
            if self.matplotlib_canvas:
                self.matplotlib_canvas.draw()
        except Exception as e:
            print(f"刷新3D视图时出错: {e}")
    
    def update_visualization_widget(self, canvas):
        """更新3D可视化窗口部件"""
        try:
            # 清除现有内容
            for i in reversed(range(self.viz_layout.count())):
                child = self.viz_layout.itemAt(i).widget()
                if child:
                    child.setParent(None)
            
            # 添加新的matplotlib画布
            self.viz_layout.addWidget(canvas)
            canvas.updateGeometry()
            
            print("3D可视化区域已更新为matplotlib画布")
            
        except Exception as e:
            print(f"更新3D可视化区域时出错: {e}")
            # 如果更新失败，显示错误信息
            error_label = QLabel(f"3D Visualization Error:\n{str(e)}")
            error_label.setAlignment(Qt.AlignCenter)
            error_label.setObjectName("errorText")
            self.viz_layout.addWidget(error_label)
            
    def reset_view(self):
        """重置视图占位符函数"""
        print("=== 重置视图功能 ===")
        QMessageBox.information(self, "重置视图", "视图已重置到默认状态")
        
    def start_measurement(self):
        """开始测量 - 使用新的模拟器系统"""
        print("=== 开始测量功能 ===")
        
        # 检查是否已加载理论数据
        if self.theoretical_data is None:
            QMessageBox.warning(
                self, "无法开始测量", 
                "请先加载理论点云数据文件才能开始测量。"
            )
            return
        
        print(f"开始测量，理论数据点数: {len(self.theoretical_data)}")
        
        # 读取测量参数
        measurement_params = self.get_measurement_parameters()
        if measurement_params is None:
            return
        
        # 停止之前的定时器
        self.simulation_timer.stop()
        
        # 清理之前的线程
        self.cleanup_threads()
        
        # 重置表格和统计数据
        self.reset_measurement_data()
        
        # 创建输出文件路径
        output_dir = os.path.join(os.getcwd(), "measurement_data")
        os.makedirs(output_dir, exist_ok=True)
        measurement_file = os.path.join(output_dir, "live_measurement.csv")
        
        # 创建硬件模拟器
        self.hardware_simulator = HardwareSimulator(
            theoretical_data=self.theoretical_data,
            measurement_params=measurement_params,
            output_file_path=measurement_file
        )
        
        # 创建误差分析工作线程
        self.analysis_worker = AnalysisWorker(
            theoretical_data=self.theoretical_data,
            measurement_file_path=measurement_file
        )
        
        # 连接硬件模拟器信号
        self.hardware_simulator.measurement_point.connect(self.on_measurement_point)
        self.hardware_simulator.measurement_finished.connect(self.on_measurement_finished)
        self.hardware_simulator.measurement_error.connect(self.on_measurement_error)
        self.hardware_simulator.progress_updated.connect(self.on_progress_updated)
        
        # 连接误差分析工作线程信号
        self.analysis_worker.analysis_result.connect(self.on_analysis_result)
        self.analysis_worker.statistics_updated.connect(self.on_statistics_updated)
        self.analysis_worker.error_data_updated.connect(self.on_error_data_updated)
        self.analysis_worker.analysis_finished.connect(self.on_analysis_finished)
        self.analysis_worker.analysis_error.connect(self.on_analysis_error)
        
        # 启动线程
        self.hardware_simulator.start()
        self.analysis_worker.start()
        
        # 更新UI状态
        self.update_ui_measurement_started()
        
        print("测量和分析线程已启动")
        
    def get_measurement_parameters(self):
        """获取测量参数"""
        try:
            x_min = float(self.x_min_input.text())
            x_max = float(self.x_max_input.text())
            x_step = float(self.x_step_input.text())
            rot_step = float(self.rot_step_input.text())
            
            # 验证参数合理性
            if x_min >= x_max:
                raise ValueError("X轴最小值必须小于最大值")
            if x_step <= 0 or rot_step <= 0:
                raise ValueError("步长值必须大于0")
                
            params = {
                'x_min': x_min,
                'x_max': x_max,
                'x_step': x_step,
                'rot_step': rot_step,
                'measurement_delay': 0.05  # 50ms延时
            }
            
            print(f"测量参数: {params}")
            return params
            
        except ValueError as e:
            QMessageBox.warning(self, "参数错误", f"请检查输入的测量参数:\n\n{str(e)}")
            return None
            
    def cleanup_threads(self):
        """清理之前的线程"""
        if self.hardware_simulator is not None:
            self.hardware_simulator.stop()
            self.hardware_simulator.wait(1000)  # 等待最多1秒
            self.hardware_simulator = None
            
        if self.analysis_worker is not None:
            self.analysis_worker.stop()
            self.analysis_worker.wait(1000)  # 等待最多1秒
            self.analysis_worker = None
            
    def reset_measurement_data(self):
        """重置测量数据"""
        # 清空表格（保留示例数据的最后3行）
        self.data_table.setRowCount(3)
        
        # 重置统计数据
        self.errors_list = [0.020, 0.025, 0.155]
        self.measurement_count = 3
        self.current_sequence = 104
        
        # 清空测量点数据
        self.measured_points = []
        
        # 清空直方图
        if hasattr(self, 'update_error_histogram'):
            self.update_error_histogram([])
        
        # 更新统计显示
        self.update_statistics()
        
    def update_ui_measurement_started(self):
        """更新UI状态为测量开始"""
        # 更新按钮状态
        self.start_measure_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        
        # 更新状态
        self.is_measuring = True
        self.status_text.setText("测量中...")
        self.status_indicator.setStyleSheet("color: #10b981; font-size: 12px;")
        
        # 禁用参数输入
        self.x_min_input.setEnabled(False)
        self.x_max_input.setEnabled(False)
        self.x_step_input.setEnabled(False)
        self.rot_step_input.setEnabled(False)
        
    # 新增：信号槽函数
    def on_measurement_point(self, sequence, x_pos, angle_deg, measured_radius):
        """处理硬件模拟器的测量点信号"""
        print(f"收到测量点: 序号={sequence}, X={x_pos}, 角度={angle_deg}, 半径={measured_radius}")
        
        # 更新实时状态
        self.current_x = x_pos
        self.current_angle = angle_deg
        self.current_x_label.setText(f"{x_pos:.1f} mm")
        self.current_angle_label.setText(f"{angle_deg:.1f}°")
        
    def on_analysis_result(self, result):
        """处理误差分析结果信号"""
        try:
            # 提取数据
            sequence = result['sequence']
            x_pos = result['x_pos']
            angle_deg = result['angle_deg']
            measured_radius = result['measured_radius']
            theoretical_radius = result['theoretical_radius']
            error_analysis = result['error_analysis']
            measured_point = result['measured_point']
            
            # 添加到表格
            self.add_analysis_result_to_table(
                sequence, x_pos, angle_deg, measured_radius,
                theoretical_radius, error_analysis
            )
            
            # 添加测量点到3D可视化
            self.add_measured_point_to_3d(measured_point, error_analysis)
            
            print(f"分析结果已添加到表格和3D视图: 序号={sequence}, 误差={error_analysis['radius_error']:.6f}")
            
        except Exception as e:
            print(f"处理分析结果时出错: {e}")
            
    def add_analysis_result_to_table(self, sequence, x_pos, angle_deg, measured_radius, theoretical_radius, error_analysis):
        """将分析结果添加到表格"""
        row = self.data_table.rowCount()
        self.data_table.insertRow(row)
        
        # 准备数据
        items = [
            str(sequence),
            f"{x_pos:.1f}",
            f"{angle_deg:.1f}",
            f"{measured_radius:.3f}",
            f"{theoretical_radius:.3f}",
            f"{error_analysis['radius_error']:+.3f}",
            error_analysis['status']
        ]
        
        # 添加数据到表格
        for col, value in enumerate(items):
            item = QTableWidgetItem(value)
            
            # 根据状态设置颜色
            if error_analysis['status'] == "超差!":
                item.setBackground(QColor("#fef3c7"))
            elif error_analysis['status'] == "注意":
                item.setBackground(QColor("#fef0e6"))
                
            self.data_table.setItem(row, col, item)
            
        # 自动滚动到最新行
        self.data_table.scrollToBottom()
        
    def on_statistics_updated(self, statistics):
        """处理统计数据更新信号"""
        # 更新统计标签
        self.max_error_label.setText(f"{statistics['max_error']:+.3f} mm")
        self.min_error_label.setText(f"{statistics['min_error']:+.3f} mm")
        self.avg_error_label.setText(f"{statistics['avg_error']:+.3f} mm")
        self.std_error_label.setText(f"{statistics['std_error']:.3f} mm")
        
        # 更新表格状态
        total_points = statistics['total_points']
        within_tolerance = statistics['within_tolerance_count']
        self.table_status_label.setText(
            f"测量中... (已完成 {total_points} 点，合格率: {within_tolerance/max(1,total_points)*100:.1f}%)"
        )
        
        # 更新误差分布直方图
        if hasattr(self, 'errors_list'):
            self.update_error_histogram(self.errors_list)
            
    def on_error_data_updated(self, error_data):
        """处理误差数据更新信号 - 用于直方图"""
        try:
            # 更新误差分布直方图
            self.update_error_histogram(error_data)
        except Exception as e:
            print(f"更新误差直方图时出错: {e}")
        
    def on_progress_updated(self, current_point, total_points):
        """处理进度更新信号"""
        progress_percent = (current_point / max(1, total_points)) * 100
        print(f"测量进度: {current_point}/{total_points} ({progress_percent:.1f}%)")
        
    def on_measurement_finished(self):
        """处理测量完成信号"""
        print("硬件模拟器测量完成")
        
    def on_analysis_finished(self):
        """处理分析完成信号"""
        print("误差分析完成")
        
        # 更新UI状态
        self.update_ui_measurement_finished()
        
    def on_measurement_error(self, error_msg):
        """处理测量错误信号"""
        print(f"测量错误: {error_msg}")
        QMessageBox.warning(self, "测量错误", error_msg)
        
    def on_analysis_error(self, error_msg):
        """处理分析错误信号"""
        print(f"分析错误: {error_msg}")
        QMessageBox.warning(self, "分析错误", error_msg)
        
    def update_ui_measurement_finished(self):
        """更新UI状态为测量完成"""
        # 更新按钮状态
        self.start_measure_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        
        # 更新状态
        self.is_measuring = False
        self.status_text.setText("测量完成")
        self.status_indicator.setStyleSheet("color: #10b981; font-size: 12px;")
        
        # 重新启用参数输入
        self.x_min_input.setEnabled(True)
        self.x_max_input.setEnabled(True)
        self.x_step_input.setEnabled(True)
        self.rot_step_input.setEnabled(True)
        
    def pause_measurement(self):
        """暂停测量 - 使用新的模拟器系统"""
        print("=== 暂停测量功能 ===")
        
        if self.is_measuring and self.hardware_simulator and self.analysis_worker:
            # 暂停两个线程
            self.hardware_simulator.pause()
            self.analysis_worker.pause()
            
            # 更新状态
            self.is_measuring = False
            self.status_text.setText("已暂停")
            self.status_indicator.setStyleSheet("color: #f59e0b; font-size: 12px;")
            
            # 更新按钮状态
            self.start_measure_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
            
            print("测量已暂停")
        
    def stop_measurement(self):
        """停止测量 - 使用新的模拟器系统"""
        print("=== 停止测量功能 ===")
        
        # 停止并清理线程
        self.cleanup_threads()
        
        # 重置状态
        self.is_measuring = False
        self.status_text.setText("已停止")
        self.status_indicator.setStyleSheet("color: #ef4444; font-size: 12px;")
        
        # 重置按钮状态
        self.update_ui_measurement_finished()
        
        print("测量已停止")
        
    def simulation_step(self):
        """模拟测量步骤占位符函数"""
        print(f"=== 模拟测量步骤 - 序号 {self.current_sequence} ===")
        
        # 生成随机模拟数据
        measured_value = 50.0 + random.uniform(-0.5, 0.5)
        theoretical_value = 50.0 + 0.1 * math.sin(math.radians(self.current_angle))
        error = measured_value - theoretical_value
        
        # 确定状态
        if abs(error) <= 0.1:
            status = "合格"
        elif abs(error) <= 0.3:
            status = "注意"
        else:
            status = "超差!"
            
        # 添加到表格
        self.add_table_row(
            self.current_sequence,
            self.current_x,
            self.current_angle,
            measured_value,
            theoretical_value,
            error,
            status
        )
        
        # 更新统计数据
        self.errors_list.append(error)
        self.update_statistics()
        
        # 更新实时状态
        self.update_real_time_status()
        
        # 更新计数
        self.current_sequence += 1
        self.measurement_count += 1
        
        # 更新角度和位置 (简单的递增模拟)
        self.current_angle += 1.5
        if self.current_angle > 175:
            self.current_angle = 10.0
            self.current_x += 10.0
            
        # 如果达到总数，自动停止
        if self.measurement_count >= self.total_measurement_count:
            self.stop_measurement()
            
    def read_measurement_parameters(self):
        """读取测量参数占位符函数"""
        print("=== 读取测量参数 ===")
        
        try:
            x_min = float(self.x_min_input.text())
            x_max = float(self.x_max_input.text())
            x_step = float(self.x_step_input.text())
            rot_step = float(self.rot_step_input.text())
            
            print(f"X轴范围: {x_min} - {x_max} mm")
            print(f"X轴步长: {x_step} mm")
            print(f"旋转轴步长: {rot_step} °")
            
            # 根据参数估算测量点数
            x_points = int((x_max - x_min) / x_step) + 1
            angle_points = int((170 - 10) / rot_step) + 1
            self.total_measurement_count = x_points * angle_points
            
            print(f"预计测量点数: {self.total_measurement_count}")
            
        except ValueError as e:
            print(f"参数读取错误: {e}")
            QMessageBox.warning(self, "参数错误", "请检查输入的测量参数是否为有效数字")
            
    def add_table_row(self, sequence, x_coord, angle, measured, theoretical, error, status):
        """向表格添加一行数据"""
        row = self.data_table.rowCount()
        self.data_table.insertRow(row)
        
        # 添加数据
        items = [
            str(sequence),
            f"{x_coord:.1f}",
            f"{angle:.1f}",
            f"{measured:.3f}",
            f"{theoretical:.3f}",
            f"{error:+.3f}",
            status
        ]
        
        for col, value in enumerate(items):
            item = QTableWidgetItem(value)
            
            # 根据状态设置行颜色
            if status == "超差!":
                item.setBackground(QColor("#fef3c7"))
            elif status == "注意":
                item.setBackground(QColor("#fef0e6"))
                
            self.data_table.setItem(row, col, item)
            
        # 自动滚动到最新行
        self.data_table.scrollToBottom()
        
    def update_statistics(self):
        """更新统计信息"""
        if not self.errors_list:
            return
            
        max_error = max(self.errors_list)
        min_error = min(self.errors_list)
        avg_error = sum(self.errors_list) / len(self.errors_list)
        
        # 计算标准差
        variance = sum((x - avg_error) ** 2 for x in self.errors_list) / len(self.errors_list)
        std_error = math.sqrt(variance)
        
        # 更新标签
        self.max_error_label.setText(f"{max_error:+.3f} mm")
        self.min_error_label.setText(f"{min_error:+.3f} mm") 
        self.avg_error_label.setText(f"{avg_error:+.3f} mm")
        self.std_error_label.setText(f"{std_error:.3f} mm")
        
    def update_real_time_status(self):
        """更新实时状态监控"""
        self.current_x_label.setText(f"{self.current_x:.1f} mm")
        self.current_angle_label.setText(f"{self.current_angle:.1f}°")
        
        # 更新表格状态
        self.table_status_label.setText(
            f"测量中... (已完成 {self.measurement_count} / 约 {self.total_measurement_count} 点)"
        )
def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序属性
    app.setApplicationName(AppConfig.APP_NAME)
    app.setApplicationVersion(AppConfig.APP_VERSION)
    app.setOrganizationName(AppConfig.APP_ORGANIZATION)
    
    # 创建主窗口
    window = MainWindow()
    window.show()
    
    # 启动事件循环
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
