#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模具曲面精度分析系统 - 主窗口模块

使用 PySide6 创建的桌面应用程序，用于模具表面精度的分析和可视化
"""

import sys
import random
import math
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QGridLayout, QFormLayout, QLabel, 
                               QPushButton, QLineEdit, QTableWidget, QTableWidgetItem,
                               QMenuBar, QToolBar, QSplitter, QFrame, QHeaderView,
                               QSizePolicy, QFileDialog, QMessageBox)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QIcon, QFont, QPalette, QColor

from config import AppConfig
from styles import StyleManager


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
        self.load_model_btn = QPushButton("📁 加载模型")
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
        
        # 主布局 - 水平分割
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # 左侧面板 - 测量设置与控制
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # 中心区域 - 可视化与实时数据
        center_panel = self.create_center_panel()
        splitter.addWidget(center_panel)
        
        # 右侧面板 - 统计分析与图例
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        # 设置分割器比例
        splitter.setSizes([AppConfig.LEFT_PANEL_WIDTH, 800, AppConfig.RIGHT_PANEL_WIDTH])
        
    def create_left_panel(self):
        """创建左侧面板 - 测量设置与控制"""
        panel = QFrame()
        panel.setObjectName("leftPanel")
        panel.setFixedWidth(AppConfig.LEFT_PANEL_WIDTH)
        panel.setFrameStyle(QFrame.StyledPanel)
        
        layout = QVBoxLayout(panel)
        layout.setSpacing(20)
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
        
        # 加载模型按钮
        self.load_cad_btn = QPushButton("加载CAD模型...")
        self.load_cad_btn.setObjectName("primaryButton")
        layout.addWidget(self.load_cad_btn)
        
        layout.addSpacing(10)
        
        # 模型信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(8)
        
        # 模型名称
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("模型名称:"))
        self.model_name_label = QLabel("a_mold_rev2.step")
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
        """创建中心面板 - 可视化与实时数据"""
        panel = QFrame()
        panel.setObjectName("centerPanel")
        
        layout = QVBoxLayout(panel)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # 3D可视化窗口（占位符）
        visualization_widget = QWidget()
        visualization_widget.setObjectName("visualizationPlaceholder")
        visualization_widget.setMinimumHeight(400)
        visualization_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # 添加占位文字
        viz_layout = QVBoxLayout(visualization_widget)
        viz_label = QLabel("3D 可视化窗口")
        viz_label.setAlignment(Qt.AlignCenter)
        viz_label.setObjectName("placeholderText")
        viz_layout.addWidget(viz_label)
        
        layout.addWidget(visualization_widget)
        
        # 实时数据表格
        self.create_data_table(layout)
        
        return panel
        
    def create_data_table(self, parent_layout):
        """创建实时数据表格"""
        # 表格标题和状态
        table_header = QHBoxLayout()
        table_title = QLabel("实时数据表格")
        table_title.setObjectName("groupTitle")
        table_header.addWidget(table_title)
        
        self.table_status_label = QLabel(f"测量中... (已完成 {self.measurement_count} / 约 {self.total_measurement_count} 点)")
        self.table_status_label.setObjectName("tableStatus")
        table_header.addWidget(self.table_status_label)
        table_header.addStretch()
        
        parent_layout.addLayout(table_header)
        
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
        self.data_table.setMinimumHeight(300)
        
        # 设置表头
        header = self.data_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        
        # 添加示例数据
        self.populate_sample_data()
        
        parent_layout.addWidget(self.data_table)
        
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
        panel.setFixedWidth(AppConfig.RIGHT_PANEL_WIDTH)
        panel.setFrameStyle(QFrame.StyledPanel)
        
        layout = QVBoxLayout(panel)
        layout.setSpacing(20)
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
        
        # 图表占位符
        chart_placeholder = QWidget()
        chart_placeholder.setObjectName("chartPlaceholder")
        chart_placeholder.setFixedHeight(200)
        
        # 添加占位文字
        chart_layout = QVBoxLayout(chart_placeholder)
        chart_label = QLabel("误差分布图表")
        chart_label.setAlignment(Qt.AlignCenter)
        chart_label.setObjectName("placeholderText")
        chart_layout.addWidget(chart_label)
        
        layout.addWidget(chart_placeholder)
        
        return group_widget
        
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
        """加载CAD模型占位符函数"""
        print("=== 加载模型功能 ===")
        
        # 打开文件选择对话框
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择CAD模型文件",
            "",
            "CAD文件 (*.step *.stp *.iges *.igs *.stl);;所有文件 (*.*)"
        )
        
        if file_path:
            print(f"选择的文件路径: {file_path}")
            
            # 提取文件名
            import os
            file_name = os.path.basename(file_path)
            
            # 更新模型信息
            self.model_name_label.setText(file_name)
            
            # 模拟更新旋转轴范围
            simulated_ranges = [
                "5.0° - 175.0°",
                "0.0° - 180.0°", 
                "10.0° - 170.0°",
                "15.0° - 165.0°"
            ]
            import random
            new_range = random.choice(simulated_ranges)
            self.rotation_range_label.setText(new_range)
            
            # 显示成功消息
            QMessageBox.information(self, "模型加载", f"已成功加载模型: {file_name}")
        else:
            print("用户取消了文件选择")
            
    def reset_view(self):
        """重置视图占位符函数"""
        print("=== 重置视图功能 ===")
        QMessageBox.information(self, "重置视图", "视图已重置到默认状态")
        
    def start_measurement(self):
        """开始测量占位符函数"""
        print("=== 开始测量功能 ===")
        print("测量开始")
        
        # 读取测量参数
        self.read_measurement_parameters()
        
        # 更新按钮状态
        self.start_measure_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        
        # 更新状态
        self.is_measuring = True
        self.status_text.setText("测量中...")
        self.status_indicator.setStyleSheet("color: #10b981; font-size: 12px;")
        
        # 启动模拟定时器 (每1秒添加一行数据)
        self.simulation_timer.start(1000)
        
    def pause_measurement(self):
        """暂停测量占位符函数"""
        print("=== 暂停测量功能 ===")
        
        if self.is_measuring:
            # 暂停定时器
            self.simulation_timer.stop()
            
            # 更新状态
            self.is_measuring = False
            self.status_text.setText("已暂停")
            self.status_indicator.setStyleSheet("color: #f59e0b; font-size: 12px;")
            
            # 更新按钮状态
            self.start_measure_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
            
            print("测量已暂停")
        
    def stop_measurement(self):
        """停止测量占位符函数"""
        print("=== 停止测量功能 ===")
        
        # 停止定时器
        self.simulation_timer.stop()
        
        # 重置状态
        self.is_measuring = False
        self.status_text.setText("已停止")
        self.status_indicator.setStyleSheet("color: #ef4444; font-size: 12px;")
        
        # 重置按钮状态
        self.start_measure_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        
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
